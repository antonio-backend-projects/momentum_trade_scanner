# Momentum Breakout Scanner — Full Stack (Alpaca + Telegram + DB + Options)

Scanner orario (1H) per segnali Momentum Breakout, con:
- Dati Alpaca (feed=IEX) — free tier
- Alert Telegram opzionali
- Esecuzione paper/live su Alpaca (equity bracket/OCO, parziale a 2R, stop→BE)
- Modulo opzioni (buy call) basato su delta/DTE target (paper)
- SQLite DB per segnali, ordini, fill, posizioni
- Docker/Docker Compose

**Default**: trading disabilitato (`enableTrading: false`).

## Setup
```
cp .env.example .env
docker compose build --no-cache
docker compose run --rm scanner
# oppure
WATCH=1 docker compose up scanner
```

Parametri in `config.yaml`. Watchlist in `tickers.csv`.
Licenza: MIT
