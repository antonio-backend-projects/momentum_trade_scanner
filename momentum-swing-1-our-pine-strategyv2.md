//@version=6
strategy("Momentum Breakout — v0.6 (XLE RS, SMA200, cooldown, time-stop)",
 overlay=true, initial_capital=100000,
 commission_type=strategy.commission.percent, commission_value=0.01,
 pyramiding=0, process_orders_on_close=true)

// ===== INPUTS =====
useLong        = input.bool(true,  "Attiva Long")
useShort       = input.bool(false, "Attiva Short")
riskPct        = input.float(1.0,  "Rischio per trade (%)", step=0.1, minval=0.1, maxval=2.0)

baseLenDays    = input.int(12,     "Base minima (giorni)", minval=7)
donchLenHours  = input.int(24*12,  "Finestra breakout (ore)")
rvMin          = input.float(2.5,  "Relative Volume minimo (consigliato 2.5–3.0)")
tpRR           = input.float(2.0,  "RR Target (>=2.0)")

benchmark      = input.symbol("XLE", "Benchmark RS (Daily)") // settore Energy
use1030ET      = input.bool(false, "Entra solo alle 10:30 ET (USA)")
usePartialTP   = input.bool(true,  "TP parziale 50% a 2R")
trailOnEMA20D  = input.bool(false, "Trail su EMA20 Daily (restante)")

cooldownDays   = input.int(10,     "Cooldown dopo un trade (giorni)", minval=0, maxval=60)
maxHoldDays    = input.int(10,     "Time-stop: uscita dopo N giorni", minval=5, maxval=30)

showDebug      = input.bool(true,  "Mostra DEBUG table")
useDynamicAlerts = input.bool(false, "Usa alert() dinamici (crea 'Any alert() function call')")

// ===== TIME WINDOW =====
is1030ETclose = (hour(time, "America/New_York") == 10 and minute(time, "America/New_York") == 30 and barstate.isconfirmed)
allowEntryBar = (use1030ET ? is1030ETclose : true) and barstate.isconfirmed

// ===== DAILY SERIES (no lookahead) =====
closeD  = request.security(syminfo.tickerid, "D", close,  barmerge.gaps_off, barmerge.lookahead_off)
ema20D  = request.security(syminfo.tickerid, "D", ta.ema(close, 20), barmerge.gaps_off, barmerge.lookahead_off)
sma200D = request.security(syminfo.tickerid, "D", ta.sma(close,200), barmerge.gaps_off, barmerge.lookahead_off)

benchD  = request.security(benchmark,        "D", close,  barmerge.gaps_off, barmerge.lookahead_off)
rsLine  = closeD / benchD
rsMA50  = request.security(syminfo.tickerid, "D", ta.sma(rsLine, 50), barmerge.gaps_off, barmerge.lookahead_off)

// BIAS 3 giorni (senza ta.sum)
emaBiasLong  = closeD > ema20D and closeD[1] > ema20D[1] and closeD[2] > ema20D[2]
emaBiasShort = closeD < ema20D and closeD[1] < ema20D[1] and closeD[2] < ema20D[2]

// RS slope (precompute)
lrNow  = ta.linreg(rsLine, 10, 0)
lrPrev = ta.linreg(rsLine, 10, 1)
rsUp   = (rsLine > rsMA50) and (lrNow > lrPrev)
rsDown = (rsLine < rsMA50) and (lrNow < lrPrev)

// Filtro trend principale per Long: sopra SMA200D (per Short: sotto)
trendOKLong  = closeD > sma200D
trendOKShort = closeD < sma200D

// ===== ATR 4H =====
atr4h = request.security(syminfo.tickerid, "240", ta.atr(14), barmerge.gaps_off, barmerge.lookahead_off)

// ===== DONCHIAN: esclude la barra corrente =====
donchLen = math.max(donchLenHours, baseLenDays*24)
hh = ta.highest(high[1], donchLen)
ll = ta.lowest(low[1],  donchLen)
breakUp   = ta.crossover(close,  hh)
breakDown = ta.crossunder(close, ll)

// ===== RELATIVE VOLUME 1H =====
rv   = volume / ta.sma(volume, 50)
rvOK = rv >= rvMin

// ===== COOLDOWN CONTROL =====
var int lastEntryTime = 0
cooldownOK = (time - lastEntryTime) > cooldownDays * 86400000

// ===== SETUP =====
longCore  = emaBiasLong  and rsUp   and trendOKLong  and breakUp   and rvOK
shortCore = emaBiasShort and rsDown and trendOKShort and breakDown and rvOK

longSetup  = useLong  and longCore  and allowEntryBar and cooldownOK
shortSetup = useShort and shortCore and allowEntryBar and cooldownOK

// ===== SIZING / SL / TP =====
riskValue = strategy.equity * (riskPct/100.0)
longSL = close - atr4h
shortSL = close + atr4h
longRiskPerShare  = math.max(close - longSL, 0.0000001)
shortRiskPerShare = math.max(shortSL - close, 0.0000001)
longQty  = strategy.position_size == 0 ? math.floor(riskValue / longRiskPerShare)  : 0
shortQty = strategy.position_size == 0 ? math.floor(riskValue / shortRiskPerShare) : 0
longTP  = close + (tpRR * longRiskPerShare)
shortTP = close - (tpRR * shortRiskPerShare)

// ===== ORDERS =====
if (longSetup and longQty > 0)
    strategy.entry("LONG", strategy.long, qty=longQty)
    strategy.exit("L-EXIT", "LONG", stop=longSL, limit=longTP)
    lastEntryTime := time

if (shortSetup and shortQty > 0)
    strategy.entry("SHORT", strategy.short, qty=shortQty)
    strategy.exit("S-EXIT", "SHORT", stop=shortSL, limit=shortTP)
    lastEntryTime := time

// ===== PARTIAL TP / TRAIL =====
if usePartialTP
    if strategy.position_size > 0
        avg = strategy.position_avg_price
        r   = avg - longSL
        pt  = avg + (tpRR * r)
        strategy.exit("L-50%", from_entry="LONG", qty_percent=50, limit=pt)
    if strategy.position_size < 0
        avg = strategy.position_avg_price
        r   = shortSL - avg
        pt  = avg - (tpRR * r)
        strategy.exit("S-50%", from_entry="SHORT", qty_percent=50, limit=pt)

if trailOnEMA20D
    if strategy.position_size > 0
        strategy.exit("L-TR", from_entry="LONG", stop=ema20D)
    if strategy.position_size < 0
        strategy.exit("S-TR", from_entry="SHORT", stop=ema20D)

// ===== TIME-STOP (chiudi se supera maxHoldDays) =====
var int entryTime = 0
if strategy.position_size == 0
    entryTime := 0
else if entryTime == 0
    entryTime := time

if entryTime != 0 and (time - entryTime) >= maxHoldDays * 86400000
    if strategy.position_size > 0
        strategy.close("LONG", comment="TimeStop")
    if strategy.position_size < 0
        strategy.close("SHORT", comment="TimeStop")

// ===== PLOT =====
plot(ema20D,  "EMA20 D",  color=color.new(color.teal,  0))
plot(sma200D, "SMA200 D", color=color.new(color.blue, 20))
plot(hh, "Base High (excl.)", color=color.new(color.green, 60))
plot(ll, "Base Low  (excl.)", color=color.new(color.red,   60))

// ===== DEBUG TABLE =====
var table t = table.new(position.top_right, 2, 9, border_width=1)
if barstate.islast and showDebug
    table.cell(t, 0, 0, "Condizione", text_color=color.white, bgcolor=color.new(color.gray, 0))
    table.cell(t, 1, 0, "OK?",        text_color=color.white, bgcolor=color.new(color.gray, 0))
    table.cell(t, 0, 1, "10:30 ET window")
    table.cell(t, 1, 1, str.tostring(allowEntryBar))
    table.cell(t, 0, 2, "EMA bias L/S")
    table.cell(t, 1, 2, str.tostring(emaBiasLong) + " / " + str.tostring(emaBiasShort))
    table.cell(t, 0, 3, "RS Up/Down (vs benchmark)")
    table.cell(t, 1, 3, str.tostring(rsUp) + " / " + str.tostring(rsDown))
    table.cell(t, 0, 4, "Trend SMA200 (L/S)")
    table.cell(t, 1, 4, str.tostring(trendOKLong) + " / " + str.tostring(trendOKShort))
    table.cell(t, 0, 5, "BreakUp/Down")
    table.cell(t, 1, 5, str.tostring(breakUp) + " / " + str.tostring(breakDown))
    table.cell(t, 0, 6, "RV ok (≥"+str.tostring(rvMin)+")")
    table.cell(t, 1, 6, str.tostring(rvOK) + " (rv=" + str.tostring(rv, format.mintick) + ")")
    table.cell(t, 0, 7, "Cooldown OK")
    table.cell(t, 1, 7, str.tostring(cooldownOK))
    table.cell(t, 0, 8, "MaxHold (giorni)")
    table.cell(t, 1, 8, str.tostring(maxHoldDays))

// ===== ALERTS (costanti) =====
alertcondition(longCore,  title="LONG setup",  message="A+ LONG breakout: RS ok, SMA200 ok, RV ok")
alertcondition(shortCore, title="SHORT setup", message="A+ SHORT breakdown: RS ok, SMA200 ok, RV ok")

// ===== (Opzionale) alert() dinamici =====
if useDynamicAlerts and barstate.isconfirmed and longCore
    alert("LONG: A+ breakout | bench=" + str.tostring(benchmark) + " | rv=" + str.tostring(rv, format.mintick), alert.freq_once_per_bar_close)
if useDynamicAlerts and barstate.isconfirmed and shortCore
    alert("SHORT: A+ breakdown | bench=" + str.tostring(benchmark) + " | rv=" + str.tostring(rv, format.mintick), alert.freq_once_per_bar_close)
