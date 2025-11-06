# Guida Docker — Pivot Confluence Breakout

## 0) Requisiti
- Docker + Docker Compose
- (Opzionale) account Alpaca (paper) per export ETF/stocks

## 1) Build
```bash
docker compose build
```

## 2) Dati 1-min in CSV
### Alpaca (ETF/Stocks USA)
1. Compila `.env` con le chiavi paper.
2. Esegui:
```bash
docker compose run --rm strategy python scripts/fetch_alpaca_csv.py --symbols SPY QQQ IWM --start 2025-10-01 --end 2025-10-31 --out ./data
```

### Binance (Crypto)
```bash
docker compose run --rm strategy python scripts/fetch_binance_csv.py --symbols BTCUSDT ETHUSDT SOLUSDT --start 2025-10-01 --end 2025-10-31 --out ./data
```

## 3) Backtest
```bash
docker compose run --rm strategy
# date custom:
START=2025-10-01 END=2025-10-31 docker compose run --rm strategy
```

## 4) Paper trading (safe)
```bash
MODE=paper docker compose run --rm strategy
```
Mostrerà log di polling; gli ordini non vengono ancora piazzati.

## 5) Struttura volumi
- `./data` montata in `/app/data`
- `config.yaml` bind montato: lo modifichi senza rebuild
