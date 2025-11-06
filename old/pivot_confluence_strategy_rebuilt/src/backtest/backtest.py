import os
import pandas as pd
from typing import Dict, List

class Backtester:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        bt = cfg.get("backtest", {})
        self.start = pd.to_datetime(bt.get("start_date")).tz_localize(None)
        self.end = pd.to_datetime(bt.get("end_date")).tz_localize(None)

    def _load_csv_folder(self, folder: str, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        out = {}
        CASH_UTC_START = pd.to_datetime("13:30").time()
        CASH_UTC_END   = pd.to_datetime("20:00").time()

        bt_cfg = self.cfg.get("backtest", {})
        ex_open = int(bt_cfg.get("exclude_open_first_min", 0))
        ex_close = int(bt_cfg.get("exclude_close_last_min", 0))

        for s in symbols:
            path = os.path.join(folder, f"{s}.csv")
            if not os.path.exists(path):
                raise FileNotFoundError(f"Missing CSV: {path}")
            df = pd.read_csv(path)
            if "timestamp" not in df.columns:
                raise ValueError(f"{path} missing 'timestamp'.")
            ts = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)
            df = df.assign(timestamp=ts).set_index("timestamp").sort_index()
            df = df.loc[:, ["open","high","low","close","volume"]]

            # date range + session cash
            dfx = df.loc[self.start:self.end]
            dfx = dfx[(dfx.index.time >= CASH_UTC_START) & (dfx.index.time <= CASH_UTC_END)]

            # exclude first/last minutes
            if ex_open > 0 or ex_close > 0:
                dfx = (
                    dfx.assign(_date=dfx.index.date)
                       .groupby("_date", group_keys=False)
                       .apply(lambda g: g.iloc[ex_open: (len(g) - ex_close) if ex_close > 0 else None])
                       .drop(columns="_date")
                )
            out[s] = dfx
        return out

    def run(self, strategy):
        symbols = self.cfg["universe"]["main"]
        folder = self.cfg["data"]["folder"]
        data_map = self._load_csv_folder(folder, symbols)
        strategy.on_backtest_init(data_map)

        trades = []
        timeline = sorted(set().union(*[d.index for d in data_map.values()]))
        for ts in timeline:
            bar_map = {s: data_map[s].loc[ts] for s in symbols if ts in data_map[s].index}
            if not bar_map:
                continue
            fills = strategy.on_bar_backtest(ts, bar_map)
            trades.extend(fills)

        import pandas as pd
        if len(trades) == 0:
            df = pd.DataFrame(columns=["ts","symbol","side","px_entry","px_exit","qty","pnl","R"])
        else:
            df = pd.DataFrame(trades, columns=["ts","symbol","side","px_entry","px_exit","qty","pnl","R"])

        by_day = df.groupby(df["ts"].dt.date)["pnl"].sum().to_frame(name="pnl") if not df.empty else pd.DataFrame(columns=["pnl"])
        metrics = {}
        metrics["Trades"] = len(df)
        metrics["Win rate"] = float((df["pnl"] > 0).mean() * 100) if not df.empty else 0.0
        metrics["Expectancy (media PnL trade)"] = float(df["pnl"].mean()) if not df.empty else 0.0
        metrics["Media R"] = float(df["R"].mean()) if not df.empty else 0.0
        if not df.empty:
            eq = df["pnl"].cumsum()
            peak = eq.cummax()
            drawdown = eq - peak
            metrics["Max Drawdown"] = float(drawdown.min())
        else:
            metrics["Max Drawdown"] = 0.0

        return {"trades": df, "by_day": by_day, "metrics": metrics}
