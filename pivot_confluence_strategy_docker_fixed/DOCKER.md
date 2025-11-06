# Guida Docker — Pivot Confluence Breakout

Questa guida ti porta **da zero a backtest** e (se vuoi) a **paper trading** usando Docker.

## 0) Requisiti
- Docker e Docker Compose installati
- (Opzionale per stocks/ETF) Account **Alpaca** (anche paper) con chiavi API

## 1) Build immagine
Nella cartella del progetto (dove c'è `Dockerfile`):
```bash
docker compose build
```

## 2) Dati 1-min in CSV (senza yfinance)

### 2a) ETF/Stocks USA da Alpaca
1. Crea `.env` copiando `.env.example` e inserisci le chiavi Alpaca.
2. Esporta i CSV in `./data` (esempio ottobre 2025 per SPY/QQQ/IWM):
```bash
docker compose run --rm strategy   python scripts/fetch_alpaca_csv.py --symbols SPY QQQ IWM   --start 2025-10-01 --end 2025-10-31 --out ./data
```

### 2b) Crypto da Binance (nessuna chiave richiesta)
```bash
docker compose run --rm strategy   python scripts/fetch_binance_csv.py --symbols BTCUSDT ETHUSDT SOLUSDT   --start 2025-10-01 --end 2025-10-31 --out ./data
```

> I file hanno schema: `timestamp,open,high,low,close,volume` — pronti per il backtest.

## 3) Configurazione universi/parametri
Apri `config.yaml` e scegli l'universo:
```yaml
universe:
  main: [SPY, QQQ]
  confirms:
    SPY: [QQQ, IWM]
    QQQ: [SPY, IWM]
```
Oppure per crypto:
```yaml
universe:
  main: [BTCUSDT]
  confirms:
    BTCUSDT: [ETHUSDT, SOLUSDT]
```

## 4) Backtest
Esegui:
```bash
docker compose run --rm strategy
```
Per date personalizzate:
```bash
START=2025-10-01 END=2025-10-31 docker compose run --rm strategy
```
Vedrai:
- `=== BACKTEST SUMMARY ===` (lista dei trade)
- `By day:` (PnL giornaliero)

## 5) Paper trading (solo se vuoi connetterti ad Alpaca)
> **Sicurezza**: la modalità live/paper è in *demo safe*: non invia ordini fino all'abilitazione dello stato incrementale in `on_poll`. Usa prima il backtest.

1. Assicurati `.env` con chiavi Alpaca.
2. Avvia il container in **paper**:
```bash
MODE=paper docker compose run --rm strategy
```
Uscita attesa: `Poll tick - demo mode...`

## 6) Struttura volumi
- `./data` è montata in `/app/data` dentro il container.
- `config.yaml` è montato come bind — puoi modificarlo senza rebuild.

## 7) Troubleshooting
- **CSV mancanti**: controlla i nomi file (es. `SPY.csv`).
- **Alpaca 429/rate limit**: riduci intervallo/export o simboli per chiamata.
- **Timezone**: i livelli OR/VWAP si basano sugli orari cash USA (09:30–16:00) per gli indici. Per crypto non è necessario.
