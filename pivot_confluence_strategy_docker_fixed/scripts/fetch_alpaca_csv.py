import os, argparse, csv
from datetime import datetime, timedelta, timezone
from dateutil import parser as dparser
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST

def iso_floor(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--out", default="./data")
    args = parser.parse_args()

    load_dotenv()
    api = REST(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), base_url=os.getenv("APCA_API_BASE_URL"))

    os.makedirs(args.out, exist_ok=True)
    start = dparser.parse(args.start)
    end = dparser.parse(args.end) + timedelta(days=1)  # inclusive end

    for sym in args.symbols:
        print(f"Downloading {sym} 1Min bars from Alpaca...")
        bars = api.get_bars(sym, "1Min", start=iso_floor(start), end=iso_floor(end), adjustment="raw")
        path = os.path.join(args.out, f"{sym}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["timestamp","open","high","low","close","volume"])
            for b in bars:
                ts = b.timestamp if hasattr(b, "timestamp") else b.t
                vol = getattr(b, "v", getattr(b, "volume", 0))
                w.writerow([ts.isoformat(), b.o, b.h, b.l, b.c, vol])
        print(f"Saved {path}")

if __name__ == "__main__":
    main()
