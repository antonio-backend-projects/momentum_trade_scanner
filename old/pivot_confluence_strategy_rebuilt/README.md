# Pivot Confluence Strategy (Docker)

Strategia intraday/scalping basata su **confluenza di livelli** (Floor Pivots, OR, VWAP, PDH/PDL/PDC) e filtro **trend** (EMA20/EMA50 + VWAP), con **ATR buffer**, **cooldown**, **bracket TP/SL** e **slippage/commissioni**. Nessuna dipendenza da `yfinance`.

## Setup
```bash
docker compose build

# Scarica CSV 1m da Alpaca
export ALPACA_API_KEY=...
export ALPACA_API_SECRET=...
docker compose run --rm --entrypoint "" strategy   python scripts/fetch_alpaca_csv.py --symbols SPY QQQ IWM   --start 2025-10-01 --end 2025-10-31 --out ./data

# Backtest
docker compose run --rm strategy
```
Risultati in console + `backtest_trades.csv`.
