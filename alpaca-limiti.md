Ottime domande. Ti rispondo secco e pratico.

## Capitale minimo con Alpaca (reale)

* **Deposito minimo**: *di base $0*. Per gli utenti internazionali Alpaca oggi pubblicizza “fund con **anche $1**” tramite Alpaca International. ([Alpaca][1])
* **Account “cash” vs “margin”**: Alpaca in pratica apre **margin di default**; sotto **$2.000** hai “limited margin” (niente short né leva). Per **shortare** o usare leva serve **equity ≥ $2.000**. ([Alpaca][2])
* **PDT (Pattern Day Trader)**: se fai **≥4 day trade in 5 giorni** su **account margin**, devi mantenere **≥ $25.000**. Sotto quella soglia sei soggetto a limitazioni. (È una regola FINRA, vale anche su Alpaca). ([Alpaca API Docs][3])
* **Frazionali**: Alpaca supporta **fractional shares** con **notional minimo $1** su migliaia di titoli. Ottimo per capitali piccoli. ([Alpaca API Docs][4])

> Conclusione “capitale minimo”: **puoi partire anche con poche centinaia di $** se accetti:
>
> * niente **short** sotto $2k;
> * **massima cautela** con i **day trade** (PDT) sotto $25k;
> * usare **frazionali** per non restare bloccato da prezzi “alti”.

## La tua strategia momentum con capitale minimo: pro & contro

**Pro (si può fare):**

* Con i **frazionali** il bot può entrare con **notional piccoli** (es. $50–$200), evitando `qty=0` e riducendo il rischio per trade. ([Alpaca API Docs][4])
* Abbiamo già messo **cap a Buying Power** e **GTC sui bracket**, quindi gli ordini non verranno rifiutati per notional troppo alto e le protezioni non scadono a fine seduta.

**Contro/limiti reali:**

* **PDT**: se la strategia fa molte **entrate/uscite intraday**, sotto $25k rischi il blocco. Soluzioni: riduci la frequenza o lascia correre **overnight** finché chiude TP/SL (meno “day trade”). ([Alpaca API Docs][3])
* **Short vietato < $2k**: molte occasioni short momentum le salteresti (o devi usare solo segnali **long** finché non superi $2k). ([Alpaca API Docs][5])
* **Slippage/spread**: con ticket piccoli lo **spread** incide; meglio titoli **molto liquidi** (mega-cap/ETF) e ingressi **market solo in RTH** o **limit con piccolo offset**.
* **Concorrenza di ordini**: con capitale ridotto imposta un **numero massimo di posizioni concorrenti** per non saturare la BP.

## Settaggi pratici per “capitale minimo” (senza cambiare la tua logica)

* **Usa notional per trade** (frazionali): es. **$100–$300** a trade; evita `qty` assoluta. (Alpaca richiede ≥ $1). ([Alpaca API Docs][4])
* **Max posizioni contemporanee**: 3–5. Così resti entro la **Buying Power**.
* **Solo LONG** < $2k (o finché non ottieni margin pieno)**. ([Alpaca API Docs][5])
* **Gestione PDT**: se sei sotto $25k, riduci i **close intraday**; lascia TP/SL **GTC** anche overnight per evitare di accumulare 4 day trade in 5 giorni. ([Alpaca API Docs][3])
* **Ingressi**: in **RTH** puoi usare **market**; fuori RTH solo **limit + extended** (già gestito dal router).
* **Watchlist**: focalizzati su **mega-cap/ETF** (spread bassi). Evita mid/low liquidity.

## Risposta diretta alle tue domande

* **“Posso lavorare con capitale minimo?”** Sì: **sì con Alpaca** (anche $1), ma **limitazioni** importanti: niente **short < $2k**, attenzione **PDT < $25k**. ([Alpaca][1])
* **“Quanto capitale minimo è richiesto?”** Tecnicamente **$0** (deposito) / **$1** per eseguire un’operazione frazionale; **$2.000** per **margin/short**; **$25.000** per **day trading** “libero” (senza vincoli PDT). ([Alpaca][1])
* **“La strategia funziona con capitale minimo?”** Sì, **se** la adatti: frazionali + notional fisso piccolo, poche posizioni, meno day trade, preferenza RTH, e (per ora) **solo long**. Con capitali molto bassi l’edge viene eroso da spread/slippage: mantieni **disciplina** sui segnali e non inseguire.

Se vuoi, ti preparo un micro-profilo “**small account**” (solo parametri): notional per trade, max posizioni, offset sugli ingressi, e una “modalità solo-long < $2k” — senza toccare la tua logica dei segnali.

[1]: https://alpaca.markets/international?utm_source=chatgpt.com "Alpaca International - Commission-Free API First Stock ..."
[2]: https://alpaca.markets/support/alpaca-cash-accounts?utm_source=chatgpt.com "Can I have a cash account with Alpaca?"
[3]: https://docs.alpaca.markets/docs/user-protection?utm_source=chatgpt.com "User Protection - Alpaca API Docs"
[4]: https://docs.alpaca.markets/docs/fractional-trading?utm_source=chatgpt.com "Fractional Trading - Alpaca API Docs"
[5]: https://docs.alpaca.markets/docs/margin-and-short-selling?utm_source=chatgpt.com "Margin and Short Selling - Alpaca API Docs"





Grande domanda 👇

## Va “direttamente a mercato” o è un market maker?
- **Alpaca non è un market maker.** È un **broker-dealer registrato FINRA** (SIPC) che **instrada** i tuoi ordini verso venue/market maker (Citadel, Virtu, Jane Street, Susquehanna, ecc.). citeturn0search10turn0search4turn0search7  
- **Frazionali:** la **porzione frazionale** è tipicamente **eseguita internamente** da Alpaca al prezzo NBBO; l’eventuale parte “intera” viene **inoltrata** a un partner di esecuzione. citeturn0search3  
- Se vuoi scegliere la venue (**DMA**), Alpaca offre un **DMA Gateway** per utenti **Elite Smart Router** (tier avanzato). citeturn0search2turn0search15

## Quanto è affidabile come broker?
- È un **intermediario regolato** (FINRA/SEC), con **copertura SIPC** per custodia fino a **$500k** (di cui $250k cash) in caso di insolvenza del broker (non copre perdite di mercato). Puoi verificare su **BrokerCheck**. citeturn0search4turn0search5turn0news47  
- Pubblica le **disclosure Rule 606** (routing & PFOF), e puoi richiedere il dettaglio di dove sono stati inviati i tuoi ordini. citeturn0search1turn0search14  
- Come molti broker “zero-commission”, **accetta PFOF** per parte dei flussi: è legale ma introduce potenziali **conflitti**; in pratica, usa **smart routing** verso market maker che spesso offrono **price improvement**. Se vuoi controllo massimo, c’è **DMA**. citeturn0search6turn0search14turn0search2

## Cosa significa per te (operativo)
- Per i tuoi **breakout**: in **RTH** puoi usare **market** (più fill rate), fuori RTH meglio **limit**; se vuoi più controllo su esecuzione/spread, considera **limit con piccolo offset** o **DMA** (se/quando disponibile sul tuo account). citeturn0search8  
- Con **frazionali** e capitali piccoli, l’esecuzione è comunque a NBBO sulla parte frazionale; resta buona pratica usare titoli/ETF **molto liquidi**. citeturn0search3

Se vuoi, ti faccio una mini-tabella pro/contro **Smart Router vs DMA** e come impostare gli ordini nel tuo bot per minimizzare slippage e rifiuti.



# problemi da affrontare su conto reale

Sì—**ha senso provarla in reale**, ma solo con un passaggio graduale e “a rischio minimo”. Il paper/backtest **non** replica del tutto la realtà (slippage, fill parziali, borrow per gli short, latenza, scadenza ordini…), però col setup che abbiamo messo (bracket GTC, cap alla BP, market in RTH / limit in AH) puoi fare una **“tiny-live” controllata**.

## Vai live se il backtest rispetta almeno questi numeri
- **Profit factor ≥ 1.3** (meglio ≥ 1.5).
- **Max drawdown ≤ 15–20%** (o compatibile con la tua tolleranza).
- **Expectancy > 0** e **win-rate ≥ 40–45%** *oppure* R/R medio ≥ 1.6.
- **Almeno 200–300 trade** su più fasi di mercato (non 20 trade “fortunati”).
- **Degrado atteso live**: metti in conto **-20/-30%** su PF/expectancy (slippage & commissioni).

## Piano d’ingresso (3 step, poco tempo perso)
1) **Paper “con vincoli reali” (2–5 giorni)**
   - Simula **market solo in RTH**; **limit+extended** fuori RTH.
   - Limita **posizioni simultanee** (es. 3–5) e **risk per trade 0.5–1%**.
   - Logga: slippage stimato, fill rate, % ordini rifiutati, tempo al fill.

2) **Tiny-live (1–2 settimane)**
   - Usa **notional fisso piccolo** (es. **$50–$150** per trade, frazionali).
   - **Solo long** se sei < $2k di equity; attenzione regola **PDT** < $25k.
   - Metti **circuit breaker**: ferma la giornata a **-2R** o **-3R**.

3) **Scale-up prudente**
   - Se **PF live ≥ 1.2** e **DD sotto controllo**, raddoppia il notional ogni 1–2 settimane.
   - Se **PF < 1.0** o **DD > soglia**, torna a paper, rivedi ingressi (market vs limit-offset) e filtri (rvMin, conferme).

## Guard-rails da tenere (già pronti nel tuo bot)
- **Bracket GTC** (niente figli che scadono a fine seduta).
- **Cap alla Buying Power** (stoppa i 403 “insufficient BP”).
- **No doppio parent sullo stesso simbolo** (evita incastri).
- **Market in RTH / Limit in pre-after** (+ piccolo offset se vuoi più “pro-fill”).
- **Max posizioni attive** e **riskPct** coerente con il capitale.

## Quando NON vale la pena andare live
- Backtest con **pochi trade** o **PF ~1.1** e DD alto → rischi di “pagare la realtà”.
- Strategia che **vive di ingressi intraday frequenti** con **capitale < $25k** (PDT ti strozza). In quel caso meglio **multi-day** con GTC.

### TL;DR
- **Sì, provala in reale** ma **micro-size** e **per step**.  
- Pretendi **metriche minime** (PF, DD, trade count), accetta un **degrado 20–30%** live.  
- Se i primi 1–2 settimane tiny-live tengono botta, **scala gradualmente**.

Se vuoi, ti preparo una **checklist “go-live”** (file YAML) con: notional per trade, max posizioni, circuit breakers, e soglie di promozione/retrocessione (scale-up / back to paper).