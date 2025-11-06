# Pivot Confluence Breakout (Docker)

Strategia intraday/scalping basata su **Pivot/VWAP/Opening Range/PDH-PDL** + **confluenza cross-asset**.
- Backtest da **CSV 1m** (Alpaca per ETF/stocks, Binance per crypto).
- Paper/live Alpaca (loop in modalità **safe** finché non abilitiamo lo stato incrementale).

## Avvio rapido (Docker)
```bash
docker compose build
# Export CSV (ETF/Stocks USA via Alpaca; richiede .env con chiavi):
docker compose run --rm strategy python scripts/fetch_alpaca_csv.py --symbols SPY QQQ IWM --start 2025-10-01 --end 2025-10-31 --out ./data
# Oppure Crypto (Binance, pubblico):
docker compose run --rm strategy python scripts/fetch_binance_csv.py --symbols BTCUSDT ETHUSDT SOLUSDT --start 2025-10-01 --end 2025-10-31 --out ./data
# Backtest:
docker compose run --rm strategy
```

## Config universi
ETF:
```yaml
universe:
  main: [SPY, QQQ]
  confirms:
    SPY: [QQQ, IWM]
    QQQ: [SPY, IWM]
```
Crypto:
```yaml
universe:
  main: [BTCUSDT]
  confirms:
    BTCUSDT: [ETHUSDT, SOLUSDT]
```

## Note
- Il loader CSV filtra la **cash session USA**: 13:30–20:00 UTC (09:30–16:00 ET).
- Nessun uso di yfinance.
- Trade export in `backtest_trades.csv` + metriche (win-rate, expectancy, max DD).
