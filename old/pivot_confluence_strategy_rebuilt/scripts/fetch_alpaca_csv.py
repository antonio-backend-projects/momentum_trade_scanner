import argparse, os, sys
import pandas as pd
from alpaca_trade_api.rest import REST, TimeFrame

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--out", default="./data")
    args = ap.parse_args()

    key = os.getenv("ALPACA_API_KEY")
    sec = os.getenv("ALPACA_API_SECRET")
    url = os.getenv("ALPACA_API_BASE_URL", "https://data.alpaca.markets")
    if not key or not sec:
        print("ERROR: set ALPACA_API_KEY and ALPACA_API_SECRET", file=sys.stderr)
        sys.exit(1)

    rest = REST(key, sec, base_url=url)
    os.makedirs(args.out, exist_ok=True)
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC") + pd.Timedelta(days=1)

    for sym in args.symbols:
        print(f"Downloading {sym} 1Min bars from Alpaca...")
        bars = rest.get_bars(sym, TimeFrame.Minute, start.isoformat(), end.isoformat(), adjustment='raw').df
        if bars.empty:
            print(f"WARNING: no bars for {sym}")
            continue
        if "symbol" in bars.columns:
            try:
                bars = bars.droplevel(0)
            except Exception:
                pass

        bars = bars.rename(columns=str.lower)
        bars = bars.reset_index()
        bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)
        cols = ["timestamp","open","high","low","close","volume"]
        bars = bars[cols].sort_values("timestamp")
        out = os.path.join(args.out, f"{sym}.csv")
        bars.to_csv(out, index=False)
        print(f"Saved {out}")

if __name__ == "__main__":
    main()
