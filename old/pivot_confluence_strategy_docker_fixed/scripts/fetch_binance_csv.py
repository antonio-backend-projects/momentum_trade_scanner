import os, argparse, csv, time, requests
from datetime import datetime, timedelta, timezone
from dateutil import parser as dparser

BASE = "https://api.binance.com/api/v3/klines"

def to_ms(dt):
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--out", default="./data")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    start = dparser.parse(args.start)
    end = dparser.parse(args.end) + timedelta(days=1)

    for sym in args.symbols:
        print(f"Downloading {sym} 1m klines from Binance...")
        path = os.path.join(args.out, f"{sym}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["timestamp","open","high","low","close","volume"])
            cur = start
            while cur < end:
                params = {
                    "symbol": sym,
                    "interval": "1m",
                    "startTime": to_ms(cur),
                    "endTime": to_ms(min(cur + timedelta(days=3), end)),
                    "limit": 1000
                }
                r = requests.get(BASE, params=params, timeout=30)
                r.raise_for_status()
                data = r.json()
                if not data:
                    break
                for k in data:
                    ts = datetime.fromtimestamp(k[0]/1000, tz=timezone.utc).isoformat()
                    w.writerow([ts, k[1], k[2], k[3], k[4], k[5]])
                # advance window
                cur = datetime.fromtimestamp(data[-1][0]/1000, tz=timezone.utc) + timedelta(minutes=1)
                time.sleep(0.2)
        print(f"Saved {path}")

if __name__ == "__main__":
    main()
