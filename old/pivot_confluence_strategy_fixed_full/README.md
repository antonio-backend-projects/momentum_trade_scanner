# Pivot Confluence Strategy (fixed)

Niente yfinance. Dati 1m da Alpaca in UTC, filtro sessione in America/New_York.

## Quick start
```bash
docker compose build

cp .env.example .env
nano .env  # inserisci le chiavi Alpaca

docker compose run --rm --entrypoint "" strategy   python scripts/fetch_alpaca_csv.py --symbols SPY QQQ IWM   --start 2025-10-01 --end 2025-10-31 --out ./data

docker compose run --rm strategy
```
Debug:
```bash
docker compose run --rm -e STRAT_DEBUG=1 strategy
```
