# Pivot Confluence Strategy — Corrected Backtester

## Setup
```bash
cp .env.example .env  # set keys
docker compose build
```

## Fetch data (example)
```bash
docker compose run --rm --entrypoint "" strategy   python scripts/fetch_alpaca_csv.py --symbols SPY QQQ IWM   --start 2025-10-01 --end 2025-10-31 --out ./data
```

## Run backtest
```bash
docker compose run --rm strategy
```

### Why results are now realistic
- Entry simulated from the **bar after** the signal (no look-ahead).
- Entry requires price to **touch** the stop price.
- Exit uses **OCO bracket** (TP/SL), adverse-first if both hit in the same bar.
- Commission and slippage applied on entry and exit.
- PnL is computed **only** by the backtester (strategy emits signals).
