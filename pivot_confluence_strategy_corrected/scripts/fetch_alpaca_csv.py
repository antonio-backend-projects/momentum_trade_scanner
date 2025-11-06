#!/usr/bin/env python3
"""
Scarica minute bars da Alpaca e salva CSV per backtest.

Usage (dentro Docker):
  docker compose run --rm --entrypoint "" strategy \
    python scripts/fetch_alpaca_csv.py --symbols SPY QQQ IWM \
    --start 2025-10-01 --end 2025-10-31 --out ./data --timeframe 1m
"""

import os
import sys
import time
import argparse
from datetime import datetime, timezone

import pandas as pd

try:
    from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit, APIError
except Exception as e:
    print("Alpaca SDK non installato o non importabile:", e, file=sys.stderr)
    sys.exit(1)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", required=True, help="Lista simboli es. SPY QQQ IWM")
    ap.add_argument("--start", required=True, help="Data start (YYYY-MM-DD)")
    ap.add_argument("--end", required=True, help="Data end inclusa (YYYY-MM-DD)")
    ap.add_argument("--out", default="./data", help="Cartella output CSV")
    ap.add_argument("--timeframe", default="1m", help="1m, 5m, 15m ... (solo minuti)")
    ap.add_argument("--feed", default=None, help="feed Alpaca (es. iex, sip). Di solito lasciare vuoto.")
    ap.add_argument("--adjustment", default="raw", choices=["raw", "split", "all"], help="Aggiustamento prezzi")
    return ap.parse_args()


def get_tf(tf_str: str) -> TimeFrame:
    # accetta “1m, 5m, 15m, 30m, 60m”
    if not tf_str.endswith("m"):
        raise ValueError("timeframe deve terminare con 'm' (minuti), es. 1m")
    mins = int(tf_str[:-1])
    return TimeFrame(mins, TimeFrameUnit.Minute)


def get_rest_client() -> REST:
    key = os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID")
    secret = os.getenv("ALPACA_API_SECRET") or os.getenv("APCA_API_SECRET_KEY")
    base_url = os.getenv("ALPACA_BASE_URL") or os.getenv("APCA_API_BASE_URL")  # opzionale
    if not key or not secret:
        print("ERROR: set ALPACA_API_KEY and ALPACA_API_SECRET", file=sys.stderr)
        sys.exit(2)
    return REST(key_id=key, secret_key=secret, base_url=base_url)


def round_trip(client: REST, *args, **kwargs):
    """Chiamata con retry/backoff semplice per evitare rate-limit."""
    backoff = 1.0
    for attempt in range(7):
        try:
            return client.get_bars(*args, **kwargs)
        except APIError as e:
            msg = str(e).lower()
            if "rate limit" in msg or "too many" in msg or e.status_code == 429:
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
                continue
            raise
        except Exception:
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
    raise RuntimeError("Impossibile ottenere i dati dopo vari tentativi.")


def fetch_symbol(client: REST, symbol: str, start: str, end: str, tf: TimeFrame, feed: str | None, adjustment: str) -> pd.DataFrame:
    # Alpaca vuole start/end in ISO con timezone; usiamo UTC inclusivo
    start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    # end alle 23:59:59 UTC del giorno indicato
    end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc) \
             .replace(hour=23, minute=59, second=59)

    # get_bars restituisce un BarSet-like (iterator). Convertiamo in DataFrame
    bars = round_trip(
        client,
        symbol,
        tf,
        start=start_dt,
        end=end_dt,
        adjustment=adjustment,
        feed=feed
    )

    if hasattr(bars, "df"):  # SDK vecchi
        df = bars.df
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol)
    else:
        # SDK nuovi: bars è list/iterator di Bar
        rows = []
        for b in bars:
            rows.append({
                "timestamp": pd.Timestamp(b.t).tz_convert("UTC"),
                "open": float(b.o),
                "high": float(b.h),
                "low": float(b.l),
                "close": float(b.c),
                "volume": int(b.v),
            })
        df = pd.DataFrame(rows).set_index("timestamp")

    if df.empty:
        return df

    # Normalizza colonne e indice
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()

    # Rimuovi duplicati eventuali
    df = df[~df.index.duplicated(keep="last")]

    return df


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    client = get_rest_client()
    tf = get_tf(args.timeframe)

    for sym in args.symbols:
        print(f"Downloading {sym} {args.timeframe} bars from Alpaca...")
        df = fetch_symbol(client, sym, args.start, args.end, tf, args.feed, args.adjustment)
        if df.empty:
            print(f"WARNING: nessun dato per {sym} nel periodo richiesto.")
            continue

        # CSV con timestamp ISO +00:00 e header richiesti dal backtest
        out_path = os.path.join(args.out, f"{sym}.csv")
        df_reset = df.reset_index()
        # timestamp in ISO con offset esplicito
        df_reset["timestamp"] = df_reset["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S%z")
        # Inserisci i due punti nel +0000 -> +00:00 per compatibilità
        df_reset["timestamp"] = df_reset["timestamp"].str.replace(r"(\+|\-)(\d{2})(\d{2})$", r"\1\2:\3", regex=True)

        df_reset.rename(columns={"timestamp": "timestamp"}, inplace=True)
        df_reset.to_csv(out_path, index=False, columns=["timestamp", "open", "high", "low", "close", "volume"])
        print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
