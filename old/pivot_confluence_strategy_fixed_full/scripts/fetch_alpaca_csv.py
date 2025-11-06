import os
import argparse
import pandas as pd
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame

def fetch(symbols, start, end, outdir):
    load_dotenv()
    api_key = os.getenv("ALPACA_API_KEY")
    api_sec = os.getenv("ALPACA_API_SECRET")
    base_url = os.getenv("ALPACA_API_BASE_URL", "https://data.alpaca.markets")

    if not api_key or not api_sec:
        raise SystemExit("ERROR: set ALPACA_API_KEY and ALPACA_API_SECRET")

    rest = REST(api_key, api_sec, base_url=base_url)
    os.makedirs(outdir, exist_ok=True)

    for sym in symbols:
        print(f"Downloading {sym} 1Min bars from Alpaca...")
        bars = rest.get_bars(sym, TimeFrame.Minute, start, end, adjustment='raw', limit=10000)
        if not bars:
            print(f"WARNING: no bars for {sym}")
            continue
        df = bars.df
        df = df.rename(columns={'t':'timestamp','o':'open','h':'high','l':'low','c':'close','v':'volume'})
        if df.index.tz is None:
            df.index = pd.to_datetime(df.index, utc=True)
        else:
            df.index = df.index.tz_convert("UTC")
        df = df[['open','high','low','close','volume']].copy()
        df.index.name = 'timestamp'
        outpath = os.path.join(outdir, f"{sym}.csv")
        df.to_csv(outpath)
        print(f"Saved {outpath}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default="./data")
    args = ap.parse_args()
    fetch(args.symbols, args.start, args.end, args.out)
