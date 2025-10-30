# Momentum Breakout Scanner (Alpaca + Telegram)

Scanner orario che replica i **segnali dell’indicatore Momentum Breakout** su timeframe **1H** e invia **alert su Telegram**.
- **Conservativo per default**: segnali a **chiusura barra** (no intrabar).
- **Dati**: Alpaca Market Data API (IEX realtime / SIP ritardato 15m).
- **Uso tipico**: cron ogni ora, oppure modalità `WATCH=1` per loop continuo.

## 1) Cosa serve
- Un account **Alpaca Market Data** con **API Key/Secret** (anche senza trading).  
- Un **Telegram Bot** e un **chat ID** (puoi usare un gruppo o chat privata).

## 2) Configurazione
1. Copia `.env.example` in `.env` e completa:
   - `ALPACA_API_KEY`, `ALPACA_API_SECRET`
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
2. (Opzionale) Modifica `config.yaml`:
   - `timeframe: 1H` (lascia 1H)
   - `baseLenDays: 12`, `donchLenHours: 288`
   - `rvMin: 2.5`
   - `confirmOnClose: true`, `useHighIntrabar: false`, `showPreSignal: false`
   - `use1030ET: false` (metti `true` per filtrare alle 10:30 ET)
3. Modifica/integra i simboli in `tickers.csv` (c’è già una lista iniziale per settore).  
   Puoi anche impostare il **Benchmark** per singolo ticker (es. SMH, XLE, QQQ, SPY).

## 3) Esecuzione (senza Docker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # poi edit .env
python scanner.py         # esegue una scansione singola
WATCH=1 python scanner.py # loop continuo (scan ogni N minuti)
```

## 4) Esecuzione con Docker
```bash
# build
docker build -t momentum-scanner:latest .

# una scansione singola (cron-friendly)
docker run --rm --env-file .env -v $PWD/state:/app/state -v $PWD/tickers.csv:/app/tickers.csv momentum-scanner:latest

# loop continuo (ogni 60 minuti di default)
docker run --rm --env-file .env -e WATCH=1 -v $PWD/state:/app/state -v $PWD/tickers.csv:/app/tickers.csv momentum-scanner:latest
```

### docker compose (comodo)
```bash
docker compose run --rm scanner             # singola scansione
WATCH=1 docker compose up scanner           # loop continuo
```

## 5) Cron (Linux / Raspberry Pi / server)
Esempio: esegui ogni ora al minuto 35 (per catturare la chiusura della barra 1H su molti broker):
```
35 * * * * cd /path/to/momentum_breakout_scanner && docker compose run --rm scanner >> scan.log 2>&1
```

## 6) Come funziona (in breve)
Per ogni ticker:
- Serie **Daily**: calcola **EMA20**, **SMA200**, **RS vs Benchmark** (media 50 e pendenza 10), **bias 3 giorni**.
- Serie **1H**: calcola **Donchian** (massimo/minimo ultimi N ore **escludendo la barra corrente**), **RV** = volume / media volume 50 (esclusa barra corrente).
- Segnale **LONG** se: bias long da 3 giorni, RS up, sopra SMA200, breakout up, RV ≥ soglia, (eventuale 10:30 ET).
- Segnale **SHORT** speculare.
- Invio alert su Telegram e salvataggio stato in `state/state.json` per non duplicare.
- **Default prudente**: segnali a **chiusura barra**. Per intrabar/near-signal vedi `config.yaml`.

## 7) Limiti e note
- Free tier e limiti API variano per provider; con Alpaca puoi fare richieste multi-simbolo ed è adatto a scansioni orarie. 
- Per grandi universi di titoli, suddividi in **lotti** (batch) per non superare limiti o URL troppo lunghi.
- Non è consulenza finanziaria. Usa sempre conto demo e fai backtest.

## 8) Provider alternativi (se non vuoi Alpaca)
- **Twelve Data**: free **~800 calls/giorno** (tier Basic); utile per scansioni giornaliere/ogni poche ore.
- **Polygon**: free **~5 richieste/minuto** (buono per test). 
- **Finnhub**: free con limiti/min inclusi; adatto a piccoli universi di tickers.

## 9) Fonti utili
- Alpaca Market Data (overview): https://alpaca.markets/data
- Alpaca docs bars (multi-simbolo): https://docs.alpaca.markets/reference/stockbars
- Alpaca WebSocket (realtime): https://docs.alpaca.markets/docs/real-time-stock-pricing-data
- Twelve Data pricing (free 800/day Basic): https://twelvedata.com/pricing
- Polygon free tier (5 req/min): https://polygon.io/knowledge-base/article/what-is-the-request-limit-for-polygons-restful-apis
