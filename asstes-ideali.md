Perfetto: ti preparo **(A)** l’**indicatore Pine v6** che replica i segnali della strategia (niente ordini, solo etichette/alert), e **(B)** una lista pratica di **asset/ETF** su cui la strategia tende a rendere meglio, più i **filtri screener** da usare in TradingView.

---

# (A) Indicatore “Momentum Breakout Signals — v0.6i” (Pine v6)

> Incolla in Pine Editor, **1H candele standard**, aggiungi al grafico.
> Mostra: bande Donchian (escl. barra corrente), EMA20D, SMA200D, etichette LONG/SHORT quando tutte le condizioni sono vere, tabellina debug opzionale, e **alertcondition** pronte.

```pine
//@version=6
indicator("Momentum Breakout Signals — v0.6i", overlay=true, max_labels_count=500)

// ===== INPUTS =====
useLong         = input.bool(true,  "Segnali Long")
useShort        = input.bool(false, "Segnali Short")
baseLenDays     = input.int(12,     "Base minima (giorni)", minval=7)
donchLenHours   = input.int(24*12,  "Finestra breakout (ore)")
rvMin           = input.float(2.5,  "Relative Volume minimo (consigliato 2.5–3.0)")
benchmark       = input.symbol("SPY", "Benchmark RS (Daily)") // Cambia per settore: XLE, XLK, XLF, ecc.
use1030ET       = input.bool(false, "Valida solo alle 10:30 ET (mercati USA)")
showDebug       = input.bool(true,  "Mostra tabella diagnostica")

// ===== FINESTRA 10:30 ET =====
is1030ETclose = (hour(time, "America/New_York") == 10 and minute(time, "America/New_York") == 30 and barstate.isconfirmed)
allowEntryBar = (use1030ET ? is1030ETclose : true) and barstate.isconfirmed

// ===== SERIE DAILY (no lookahead) =====
closeD  = request.security(syminfo.tickerid, "D", close,  barmerge.gaps_off, barmerge.lookahead_off)
ema20D  = request.security(syminfo.tickerid, "D", ta.ema(close, 20), barmerge.gaps_off, barmerge.lookahead_off)
sma200D = request.security(syminfo.tickerid, "D", ta.sma(close,200), barmerge.gaps_off, barmerge.lookahead_off)

benchD  = request.security(benchmark,        "D", close,  barmerge.gaps_off, barmerge.lookahead_off)
rsLine  = closeD / benchD
rsMA50  = request.security(syminfo.tickerid, "D", ta.sma(rsLine, 50), barmerge.gaps_off, barmerge.lookahead_off)

// BIAS 3 giorni (prezzo sopra/sotto EMA20D da 3 giorni)
emaBiasLong  = closeD > ema20D and closeD[1] > ema20D[1] and closeD[2] > ema20D[2]
emaBiasShort = closeD < ema20D and closeD[1] < ema20D[1] and closeD[2] < ema20D[2]

// RS slope (precompute)
lrNow  = ta.linreg(rsLine, 10, 0)
lrPrev = ta.linreg(rsLine, 10, 1)
rsUp   = (rsLine > rsMA50) and (lrNow > lrPrev)
rsDown = (rsLine < rsMA50) and (lrNow < lrPrev)

// Filtro trend principale per Long/Short
trendOKLong  = closeD > sma200D
trendOKShort = closeD < sma200D

// ===== DONCHIAN: esclude la barra corrente =====
donchLen = math.max(donchLenHours, baseLenDays*24)
hh = ta.highest(high[1], donchLen)
ll = ta.lowest(low[1],  donchLen)
breakUp   = ta.crossover(close,  hh)
breakDown = ta.crossunder(close, ll)

// ===== RELATIVE VOLUME 1H =====
rv   = volume / ta.sma(volume, 50)
rvOK = rv >= rvMin

// ===== SETUP CORE =====
longCore  = useLong  and emaBiasLong  and rsUp   and trendOKLong  and breakUp   and rvOK and allowEntryBar
shortCore = useShort and emaBiasShort and rsDown and trendOKShort and breakDown and rvOK and allowEntryBar

// ===== PLOT =====
plot(ema20D,  "EMA20 D",  color=color.new(color.teal,  0))
plot(sma200D, "SMA200 D", color=color.new(color.blue, 20))
plot(hh, "Base High (excl.)", color=color.new(color.green, 60))
plot(ll, "Base Low  (excl.)", color=color.new(color.red,   60))

// Etichette segnali
if longCore
    label.new(bar_index, low, "LONG",
        style=label.style_label_up, color=color.new(color.green, 0), textcolor=color.white, size=size.small)
if shortCore
    label.new(bar_index, high, "SHORT",
        style=label.style_label_down, color=color.new(color.red, 0), textcolor=color.white, size=size.small)

// ===== ALERTS (messaggi costanti) =====
alertcondition(longCore,  title="LONG setup",  message="A+ LONG breakout: RS ok, SMA200 ok, RV ok")
alertcondition(shortCore, title="SHORT setup", message="A+ SHORT breakdown: RS ok, SMA200 ok, RV ok")

// ===== DEBUG TABLE =====
var table t = table.new(position.top_right, 2, 8, border_width=1)
if barstate.islast and showDebug
    table.cell(t, 0, 0, "Condizione", text_color=color.white, bgcolor=color.new(color.gray, 0))
    table.cell(t, 1, 0, "OK?",        text_color=color.white, bgcolor=color.new(color.gray, 0))
    table.cell(t, 0, 1, "10:30 ET window")
    table.cell(t, 1, 1, str.tostring(allowEntryBar))
    table.cell(t, 0, 2, "EMA bias L/S")
    table.cell(t, 1, 2, str.tostring(emaBiasLong) + " / " + str.tostring(emaBiasShort))
    table.cell(t, 0, 3, "RS Up/Down (vs bench)")
    table.cell(t, 1, 3, str.tostring(rsUp) + " / " + str.tostring(rsDown))
    table.cell(t, 0, 4, "Trend SMA200 (L/S)")
    table.cell(t, 1, 4, str.tostring(trendOKLong) + " / " + str.tostring(trendOKShort))
    table.cell(t, 0, 5, "BreakUp/Down")
    table.cell(t, 1, 5, str.tostring(breakUp) + " / " + str.tostring(breakDown))
    table.cell(t, 0, 6, "RV ok (≥"+str.tostring(rvMin)+")")
    table.cell(t, 1, 6, str.tostring(rvOK) + "  rv=" + str.tostring(rv, format.mintick))
    table.cell(t, 0, 7, "Benchmark")
    table.cell(t, 1, 7, str.tostring(benchmark))
```

**Come usarlo**

* Grafico **1H**.
* Se il titolo è di un settore specifico, imposta `benchmark` coerente (es. **XLE** per Energy, **XLK** per Tech, **XLF** per Financials, **XLI** Industrials, **XLB** Materials, **XLV** Healthcare, **IWM** Small caps, **SMH** Semis).
* Per crypto/24x7 metti `use1030ET = OFF`.
* Puoi creare alert con “**Quando condizione dell’alert è vera**” usando le due `alertcondition`.

---

# (B) Watchlist: asset/ETF ideali + filtri screener

## Filtri TradingView (per Long)

* **Capitalizzazione**: > 2–10 miliardi (meglio >10B per qualità).
* **Volumi medi**: > 2M azioni/giorno.
* **Volatilità giornaliera (ADR)**: > 2%.
* **Beta**: > 1 (più movimento del mercato).
* **Prezzo sopra SMA200**.
* **Settore/benchmark coerente** (per la nostra RS).

## ETF “bussola” per segnali top-down

* **Indice/Tech**: SPY, QQQ, **XLK**, **SMH**
* **Energia**: **XLE**
* **Finanziari**: **XLF**
* **Industriali**: **XLI**
* **Materiali**: **XLB**
* **Healthcare**: **XLV**
* **Small Caps**: **IWM**

## Titoli USA liquidi e “momentum-friendly” (esempi)

**Tech / Growth**

* NVDA, AMD, AVGO, AAPL, MSFT, META, GOOGL, AMZN, TSLA
* ORCL, CRM, NOW, PANW, CRWD, NET, SNOW
* MU, LRCX, TSM, ARM, SMCI, ASML* (listing EU, ma ADR utili su alcuni broker)

**Semiconduttori (usa benchmark SMH/XLK)**

* NVDA, AMD, AVGO, MU, LRCX, KLAC, ASML*, TSM, AMAT

**Energy (usa benchmark XLE)**

* XOM, CVX, **OXY**, SLB, HAL, EOG, DVN

**Industrials (XLI)**

* CAT, DE, GE, BA, LMT, NOC

**Materials (XLB)**

* FCX (rame), AA (alluminio), NUE (acciaio), LIN

**Financials (XLF)**

* JPM, GS, MS, BAC, CME

**Healthcare (XLV)**

* LLY, UNH, MRK, REGN, MRNA (più volatile)

**Consumer/Internet**

* UBER, ABNB, COST, LULU, NFLX

> Suggerimento operativo: parti dagli **ETF**. Se, ad esempio, **XLE** è forte vs SPY, allora scorri i componenti Energy e applica l’indicatore; stessa cosa per **SMH** → semiconduttori.

---

## Vuoi che ti generi:

* una **lista salvabile** (CSV) con questi ticker già organizzati per settore,
* oppure una **variante dell’indicatore** che mostra a schermo **perché** un segnale è stato scartato (es. “RV basso”, “non sopra SMA200”, ecc.)?

Dimmi la preferenza e te la preparo subito.
