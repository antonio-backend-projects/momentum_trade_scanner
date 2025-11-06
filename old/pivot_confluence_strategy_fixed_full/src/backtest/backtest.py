import os
import pandas as pd
from tabulate import tabulate

LOCAL_TZ = "America/New_York"

def _apply_session(df: pd.DataFrame, cfg) -> pd.DataFrame:
    if df.empty:
        return df
    if df.index.tz is None:
        df = df.tz_localize("UTC")
    else:
        df = df.tz_convert("UTC")
    dlocal = df.tz_convert(LOCAL_TZ)
    start_s = cfg["data"]["session"]["start"]
    end_s   = cfg["data"]["session"]["end"]
    dlocal = dlocal.between_time(start_s, end_s, inclusive="both")
    ex_open  = int(cfg["backtest"].get("exclude_open_first_min", 0))
    ex_close = int(cfg["backtest"].get("exclude_close_last_min", 0))
    if ex_open or ex_close:
        dlocal = (
            dlocal.assign(_date=dlocal.index.tz_convert(LOCAL_TZ).date)
            .groupby("_date", group_keys=False)
            .apply(lambda g: g.iloc[ex_open: (len(g) - ex_close) if ex_close > 0 else None])
            .drop(columns=["_date"], errors="ignore")
        )
    return dlocal.tz_convert("UTC")

class Backtester:
    def __init__(self, cfg):
        self.cfg = cfg
        self.start = pd.to_datetime(cfg["backtest"]["start_date"]).tz_localize("UTC")
        self.end   = pd.to_datetime(cfg["backtest"]["end_date"]).tz_localize("UTC")

    def _load_csv_folder(self, folder, symbols):
        out = {}
        for s in symbols:
            path = os.path.join(folder, f"{s}.csv")
            if not os.path.exists(path):
                continue
            df = pd.read_csv(path)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df = df.set_index("timestamp")[["open","high","low","close","volume"]].sort_index()
            df = _apply_session(df, self.cfg)
            df = df.loc[self.start:self.end]
            out[s] = df
        return out

    def run(self, strategy):
        main_syms = self.cfg["universe"]["main"]
        confirms = list({x for lst in self.cfg["universe"].get("confirms",{}).values() for x in lst})
        symbols = list(dict.fromkeys(main_syms + confirms))
        data_map = self._load_csv_folder(self.cfg["data"]["folder"], symbols)
        strategy.on_backtest_init(data_map)

        all_idx = sorted(set().union(*[dm.index for dm in data_map.values() if dm is not None and not dm.empty]))
        fills = []
        for ts in all_idx:
            bar_map = {s: (data_map[s].loc[ts] if s in data_map and ts in data_map[s].index else None) for s in main_syms}
            if all(v is None for v in bar_map.values()):
                continue
            new_fills = strategy.on_bar_backtest(ts, bar_map)
            if new_fills:
                fills.extend(new_fills)

        cols = ["ts","symbol","side","px_entry","px_exit","qty","pnl","R"]
        trades = pd.DataFrame(fills, columns=cols) if fills else pd.DataFrame(columns=cols)
        print("\n=== BACKTEST SUMMARY ===")
        if not trades.empty:
            print(tabulate(trades, headers='keys', tablefmt='plain', showindex=False))
        else:
            print(trades)

        print("\n=== METRICHE ===")
        if trades.empty:
            print("Trades: 0\nWin rate: 0.0\nExpectancy (media PnL trade): 0.0\nMedia R: 0.0\nMax Drawdown: 0.0")
        else:
            wins = (trades["pnl"] > 0).sum()
            wr = 100.0 * wins / len(trades)
            exp = trades["pnl"].mean()
            rmean = trades["R"].mean() if "R" in trades else float('nan')
            eq = trades["pnl"].cumsum()
            dd = (eq.cummax() - eq).max() if not eq.empty else 0.0
            print(f"Trades: {len(trades)}\nWin rate: {wr:.2f}%\nExpectancy (media PnL trade): {exp:.4f}\nMedia R: {rmean:.2f}\nMax Drawdown: {dd:.4f}")

        if not trades.empty:
            trades["date"] = pd.to_datetime(trades["ts"]).dt.date
            byday = trades.groupby("date")["pnl"].sum().to_frame()
        else:
            byday = pd.DataFrame(columns=["pnl"])
        print("\nBy day:")
        print(byday)

        out_csv = "backtest_trades.csv"
        trades.to_csv(out_csv, index=False)
        print(f"\nTrade esportati in: {out_csv}")
        return trades
