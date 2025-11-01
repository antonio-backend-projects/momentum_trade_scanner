# Alpaca Mini Broker (test platform)

Piccolo frontend broker-like per testare ordini Alpaca:
- Lista **assets** disponibili
- **Apertura/chiusura posizioni**
- **Bracket orders** (Stop-Loss & Take-Profit)
- **Log** completo di ogni transazione in **SQLite**
- **Docker** + `docker-compose` (porta `8000`)

> **ATTENZIONE**: Solo per **uso didattico** su **Paper Trading**. Non è un consiglio finanziario.

## Avvio rapido

1. Copia `.env.example` in `.env` e imposta le tue **API key Alpaca (paper)**.
2. Avvia:
   ```bash
   docker compose up --build
   ```
3. Apri: http://localhost:8000

## Funzioni

- **Assets**: elenco cercabile di simboli disponibili (status=active, us_equity).
- **Ordini**: Market/Limit, `order_class=bracket` per SL/TP (prezzi assoluti).
- **Posizioni**: elenco posizioni aperte, pulsante **Chiudi** per simbolo.
- **Log**: ogni chiamata che genera una transazione viene salvata su SQLite (`data/broker.db`, tabella `trade_logs`).

## Endpoints principali (API)

- `GET /api/assets?query=NVDA`
- `GET /api/positions`
- `GET /api/orders`
- `POST /api/order` → body JSON con {symbol, side, qty, type, limit_price?, sl_price?, tp_price?}
- `POST /api/close_position` → {symbol}
- `GET /api/logs`

## Ambiente

- **TZ** di default: `Europe/Rome` (override in `.env`).

## Sicurezza

- Questo progetto non espone protezioni avanzate. Non lasciare le chiavi su repository pubblici.