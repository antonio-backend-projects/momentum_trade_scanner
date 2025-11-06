import pandas as pd, os
from typing import Dict, List

from strategies.pivot_confluence import PivotConfluenceStrategy

class Backtester:
    def __init__(self, cfg: Dict, start_date: str, end_date: str):
        self.cfg = cfg
        self.start = pd.Timestamp(start_date)
        self.end = pd.Timestamp(end_date)
        self.results = []

    def _load_csv_folder(self, folder: str, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        out = {}
        # Cash session NY in UTC (09:30–16:00 ET -> 13:30–20:00 UTC)
        CASH_UTC_START = pd.to_datetime("13:30").time()
        CASH_UTC_END   = pd.to_datetime("20:00").time()

        for s in symbols:
            path = os.path.join(folder, f"{s}.csv")
            if not os.path.exists(path):
                raise FileNotFoundError(f"Missing CSV: {path}")
            df = pd.read_csv(path)
            if "timestamp" not in df.columns:
                raise ValueError(f"{path} non contiene la colonna 'timestamp'.")
            ts = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)
            df = df.assign(timestamp=ts).set_index("timestamp").sort_index()
            df = df.loc[:, ["open","high","low","close","volume"]]
            dfx = df.loc[self.start:self.end]
            dfx = dfx[(dfx.index.time >= CASH_UTC_START) & (dfx.index.time <= CASH_UTC_END)]
            out[s] = dfx
        return out

    def _load_yfinance(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        try:
            import yfinance as yf  # not used here
        except ImportError:
            raise RuntimeError("yfinance non installato: usa data.source=csv nel config.yaml.")
        out = {}
        for s in symbols:
            df = yf.download(s, interval="1m", period="60d")
            df = df.rename(columns=str.lower).rename_axis("timestamp").loc[:, ["open","high","low","close","volume"]]
            out[s] = df.loc[self.start:self.end]
        return out

    def run(self, strategy: PivotConfluenceStrategy) -> pd.DataFrame:
        main_syms = self.cfg['universe']['main']
        confirm_syms = sorted({x for lst in self.cfg['universe'].get('confirms',{}).values() for x in lst})
        symbols = sorted(set(main_syms + confirm_syms))

        if self.cfg['data']['source'] == "csv":
            data_map = self._load_csv_folder(self.cfg['data']['folder'], symbols)
        else:
            data_map = self._load_yfinance(symbols)

        common_index = None
        for _, df in data_map.items():
            common_index = df.index if common_index is None else common_index.intersection(df.index)
        data_map = {s: df.loc[common_index] for s, df in data_map.items()}

        strategy.on_backtest_init(data_map)

        for ts in common_index:
            bar_map = {s: data_map[s].loc[ts] for s in symbols}
            fills = strategy.on_bar_backtest(ts, bar_map)
            if fills:
                self.results.extend(fills)

        res = pd.DataFrame(self.results, columns=["ts","symbol","side","px_entry","px_exit","qty","pnl","R"])
        self._results_df = res
        return res

    def daily_pnl(self) -> pd.DataFrame:
        if not hasattr(self, "_results_df") or self._results_df is None or self._results_df.empty:
            return pd.DataFrame()
        df = self._results_df.copy()
        df['date'] = pd.to_datetime(df['ts']).dt.date
        return df.groupby('date')['pnl'].sum().to_frame("pnl")
