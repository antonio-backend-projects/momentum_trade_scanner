# Pivot Confluence Breakout (Alpaca + Backtest)

Strategia intraday/scalping che combina **pivot/vwap/opening-range/PDH-PDL** con **confluenze cross-asset**.
Supporta:
- **Backtest** su dati 1m (CSV o yfinance)
- **Paper/Live** su Alpaca (ordini bracket TP+SL)

## Setup rapido

```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env  # compila le chiavi Alpaca se vuoi eseguire paper/live
```

## Esecuzione

### Backtest (CSV locali)
1. Metti i CSV 1m in `./data/` con schema: `timestamp,open,high,low,close,volume` (UTC o locale coerente).
2. Configura `data:` in `config.yaml` (folder e simboli).
3. Esegui:
```bash
python src/main.py --mode backtest --config config.yaml
```

### Backtest (yfinance) — *opzionale, se non bloccato*
Imposta `data.source: yfinance` e i simboli in `universe.main` + `universe.confirms`.
```bash
python src/main.py --mode backtest --config config.yaml --start 2025-09-01 --end 2025-10-31
```

### Paper trading (Alpaca)
- .env con `APCA_API_BASE_URL` (es: https://paper-api.alpaca.markets), `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`
- modalità:
```bash
python src/main.py --mode paper --config config.yaml
```

## Come ottenere i CSV 1m (senza yfinance)

### Opzione 1 — **Alpaca Market Data** (stocks/ETF USA)
Requisiti: account Alpaca (anche paper), chiavi in `.env`.

Scarica CSV 1-min per simboli e intervallo:
```bash
python scripts/fetch_alpaca_csv.py --symbols SPY QQQ IWM --start 2025-10-01 --end 2025-10-31 --out ./data
```

### Opzione 2 — **Binance** (crypto 24/7)
Nessuna API key necessaria per klines pubblici.
```bash
python scripts/fetch_binance_csv.py --symbols BTCUSDT ETHUSDT SOLUSDT --start 2025-10-01 --end 2025-10-31 --out ./data
```

> I file generati hanno schema `timestamp,open,high,low,close,volume` conforme al backtester.

Poi in `config.yaml`:
```yaml
data:
  source: csv
  folder: ./data
```
e lancia:
```bash
python src/main.py --mode backtest --config config.yaml
```

## File principali
- `src/strategies/pivot_confluence.py` — logica della strategia
- `src/utils/levels.py` — PP/R1/S1, VWAP, Opening Range, PDH/PDL
- `src/utils/indicators.py` — ATR(1m), vol mediana
- `src/utils/confluence.py` — score cross-asset
- `src/execution/alpaca_broker.py` — invio ordini bracket su Alpaca
- `src/backtest/backtest.py` — motore backtest minuto per minuto
- `scripts/fetch_alpaca_csv.py` — exporter CSV 1m da Alpaca
- `scripts/fetch_binance_csv.py` — exporter CSV 1m da Binance
- `config.yaml` — parametri

## Note importanti
- Regole deterministiche: distanza dal livello ≤ `proximity_atr_1m` × ATR(1m), volume sul break ≥ `volume_mult_break` × mediana.
- Confluenza: # asset di conferma **near-level** nello stesso minuto.
- Risk: stop = `stop_atr` × ATR(1m); TP = `take_profit_atr` × ATR(1m); blocco giornaliero a `daily_max_loss_R`.
- Validare sempre su **paper** prima del live.


---

## Avvio veloce con Docker

```bash
docker compose build
# ETF USA da Alpaca (CSV):
docker compose run --rm strategy python scripts/fetch_alpaca_csv.py --symbols SPY QQQ IWM --start 2025-10-01 --end 2025-10-31 --out ./data
# Oppure crypto da Binance (CSV):
docker compose run --rm strategy python scripts/fetch_binance_csv.py --symbols BTCUSDT ETHUSDT SOLUSDT --start 2025-10-01 --end 2025-10-31 --out ./data
# Backtest:
docker compose run --rm strategy
```
Per dettagli vedi `DOCKER.md`.
