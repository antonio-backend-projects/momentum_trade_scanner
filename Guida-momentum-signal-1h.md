perfetto — ecco una guida chiara, passo-passo, per **usare e configurare** l’indicatore “Momentum Breakout Signals”, con linguaggio semplice e una **legenda** dei termini.

---

# 1) Cosa fa l’indicatore (in parole semplici)

Ti avvisa quando un titolo:

* è **in tendenza** (sopra/sotto alcune medie a 1 giorno),
* sta **uscendo da una “gabbia” di prezzo** (breakout dell’ultimo periodo),
* lo fa con **volumi sufficienti** (quindi non una fiammata casuale),
* ed eventualmente **nell’orario che preferisci** (per i mercati USA, 10:30 ET).

Quando tutte le condizioni sono vere, sul grafico appare un’etichetta **LONG** (verde) o **SHORT** (rossa) e puoi creare **alert**.

---

# 2) Requisiti e setup base

* **Piattaforma**: TradingView.
* **Grafico**: candele/barre **standard** (no Renko, Range, Heikin Ashi se vuoi il segnale “puro”).
* **Timeframe consigliato**: **1 ora (1H)**.
* **Intervallo**: nessun limite, ma più storico = segnali più affidabili.

## Come aggiungerlo

1. Apri il grafico del titolo (es. NVDA).
2. Vai in **Pine Editor**, incolla il codice dell’indicatore.
3. Clicca **Aggiungi al grafico**.
4. Apri l’ingranaggio dell’indicatore per le **Impostazioni**.

> Nota: se vuoi anche la **strategia** (backtest con ordini finti, P&L, ecc.), è un file diverso. L’indicatore **non** fa ordini, mostra solo segnali/alert.

---

# 3) Configurazione (tab “Input”): cosa significa ogni voce

Queste voci compaiono nelle impostazioni dell’indicatore. Te le spiego con i **valori di default** consigliati.

### Segnali base

* **Segnali Long** (ON): abilita i segnali di acquisto.
* **Segnali Short** (OFF): abilita i segnali di vendita allo scoperto (lascialo OFF se non fai short).

### Struttura del breakout

* **Base minima (giorni)**: quanti giorni considerare per la “gabbia” di prezzo. Default **12** giorni.
* **Finestra breakout (ore)**: stessa idea ma in ore. Default **12×24** (coerente con 12 giorni).
* **Relative Volume minimo**: forza dei volumi rispetto alla media recente. Default **2.5** (alza a 3.0 se vuoi più selezione, abbassa a 2.0 se vuoi più segnali).

### Forza relativa e tendenza

* **Benchmark RS (Daily)**: con cosa confronti il titolo per capire se “batte” il mercato/settore.

  * Generico USA: **SPY** (S&P500) o **QQQ** (Nasdaq 100).
  * Settore energia: **XLE**.
  * Tech/Semiconduttori: **XLK** o **SMH**.
* **Valida solo alle 10:30 ET (mercati USA)**: se ON, i segnali scattano solo alla chiusura della barra delle 10:30 ora di New York (utile per filtrare il caos dell’apertura). Di default **OFF** per essere più flessibili.

### Modalità di conferma del segnale (patch “tempi del segnale”)

* **Conferma a chiusura barra** (ON – consigliata): il segnale compare **a barra chiusa** (es. su 1H, alla fine dell’ora). È più “lento” ma più affidabile e **non repaint**.
* **Intrabar (HIGH/LOW)** (OFF): il segnale compare **appena** il massimo (o minimo) supera il livello, **anche prima della chiusura** della barra. Più veloce ma più falsi allarmi.
* **Pre-segnale di prossimità** (facoltativo): puoi avere un alert quando il prezzo arriva a **X%** dal livello di breakout (ti prepara all’eventuale rottura). Default **OFF**.

> Se il tuo file non mostra ancora queste tre voci, fammelo sapere e ti rigiro subito la versione con i toggle già inclusi.

### Debug (aiuta a capire “perché non scatta”)

* **Mostra tabella diagnostica** (ON): in alto a destra vedi quali condizioni sono vere/false (trend, volumi, breakout, orario, ecc.).

---

# 4) Come leggere i segnali

* **Etichetta “LONG”**: il prezzo ha rotto verso l’alto la “gabbia” (massimi recenti), il titolo è in tendenza (sopra medie giornaliere) e i volumi sono adeguati.
* **Etichetta “SHORT”**: l’opposto (rottura verso il basso, tendenza debole, volumi ok).
* Le **bande** che vedi (due linee tenue verde/rossa) sono i limiti della “gabbia” (Donchian) **escludendo** la barra corrente — questo evita falsi segnali calcolati “con i dati della candela stessa”.

---

# 5) Come creare gli alert (notifiche)

1. Clicca **Allarme** (campanella) su TradingView.
2. Scegli l’indicatore → **Condizione**:

   * **LONG setup** per i long.
   * **SHORT setup** per gli short.
3. **Quando**:

   * Se vuoi segnali **confermati** (barra chiusa): **Once per bar close**.
   * Se usi la modalità **Intrabar**: **Once per bar** (arriva prima ma può sparire se il prezzo rientra).
4. Messaggio/azioni: imposta testo a piacere, app/Telegram/email come preferisci.
5. Crea l’alert.

> Se usi anche il **pre-segnale**, crea un **secondo alert** su quella condizione (es. “Near breakout”) per prepararti.

---

# 6) Scelta degli asset (lista e criteri)

L’indicatore rende meglio su titoli **liquidi** e con **buona escursione**.

**Criteri facili da usare in uno Screener:**

* Capitalizzazione: **> 10 miliardi** (qualità).
* Volume medio: **> 2 milioni** di azioni/giorno.
* Volatilità (range medio giornaliero): **> 2%**.
* Prezzo sopra **SMA200** se cerchi **solo Long**.
* **Benchmark** coerente con il settore (es. Energy → XLE; Tech/Semis → XLK/SMH).

**Esempi utili (USA):**

* **Tech / Growth**: NVDA, AMD, AVGO, AAPL, MSFT, META, GOOGL, AMZN, ORCL, CRM, NOW, PANW, CRWD.
* **Semis** (benchmark **SMH/XLK**): NVDA, AMD, AVGO, MU, LRCX, TSM, AMAT, KLAC.
* **Energy** (**XLE**): XOM, CVX, OXY, SLB, HAL, EOG, DVN.
* **Industrials** (**XLI**): CAT, DE, GE, BA, LMT.
* **Financials** (**XLF**): JPM, GS, MS.
* **Healthcare** (**XLV**): LLY, UNH, MRK.

Suggerimento pratico:

1. guarda prima l’ETF di settore (es. **SMH**): se è forte,
2. scorri i componenti del settore con l’indicatore: i segnali saranno più “puliti”.

---

# 7) Problemi comuni (e soluzioni rapide)

* **Non vedo segnali**:

  * Il grafico deve essere **1H** (consigliato) e **candele standard**.
  * Il **benchmark** scelto deve esistere (es. su alcuni feed **XLE** non c’è → metti **SPY** o **QQQ**).
  * A volte serve **più storico**: per contare giorni e medie, qualche settimana di dati è necessaria.
  * Se hai attivo “**10:30 ET**”, i segnali scattano **solo** a quell’ora: disattivalo per test.
* **Segnale arriva “tardi”**:

  * È voluto se usi **Conferma a chiusura barra** (modalità più sicura).
  * Vuoi prima? Attiva **Intrabar** (accetta più falsi) o usa **pre-segnale**.
* **Troppe notifiche**:

  * Alza **Relative Volume minimo** (2.8–3.0).
  * Aumenta **Base minima** (da 12 a 15 giorni).
  * Seleziona meglio gli asset (vedi criteri sopra).

---

# 8) Domande frequenti

**Il “Buy & Hold” perché sembra migliore su certi titoli?**
Perché compra all’inizio del **periodo di backtest** e tiene fino alla fine. Se il titolo (es. NVDA) fa un mega-trend, stare sempre dentro vince. L’indicatore/strategia entra-esce e usa filtri: è più prudente, perde meno nei periodi brutti ma in trend “mostruosi” sarà sotto al B&H.

**L’indicatore fa ordini o calcola P&L?**
No. Per quello serve la **strategia** (un altro script). L’indicatore dà **segnali e alert**.

**Che orario uso?**
Per azioni USA la finestra **10:30 ET** può evitare il caos dell’apertura. Per crypto/24×7 tienila **OFF**.

---

# 9) Legenda (mini-glossario)

* **Breakout (Donchian)**: rottura del massimo/minimo degli ultimi X giorni/ore.
* **EMA20D**: media mobile esponenziale a **20 giorni** (trend “breve”).
* **SMA200D**: media mobile semplice a **200 giorni** (trend “di fondo”).
* **RS (Forza Relativa)**: confronto del titolo vs **Benchmark** (es. SPY/XLE). Se il titolo “batte” l’indice/settore, è un buon segnale di forza.
* **RV (Relative Volume)**: volumi di oggi rispetto alla media: **più è alto, meglio è**.
* **Conferma a chiusura barra**: il segnale arriva **solo a candela chiusa** (più affidabile, meno precoce).
* **Intrabar**: segnale **mentre** la candela si forma (più veloce, più falsi).
* **Pre-segnale**: avviso quando il prezzo **si avvicina** al livello di breakout (ti prepara all’ordine).

---

Se vuoi, ti consegno anche:

* la **versione aggiornata del codice** con i toggle “Conferma a chiusura / Intrabar / Pre-segnale” già inclusi e con esempi di **alert** pronti;
* un **file CSV** con una watchlist organizzata per settore (così li importi in blocco su TradingView).
