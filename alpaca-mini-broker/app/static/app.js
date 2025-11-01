
// --- Diagnostics bootstrap ---
console.log("[app] boot");
window.addEventListener('error', (e)=>{
  try { fetch('/api/client-log', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({level:'error', message:String(e.message||e), stack:String(e.error&&e.error.stack||''), where:'window.onerror'})}); } catch(_){}
});
(async ()=>{
  try{ await fetch('/api/ping'); console.log("[app] ping ok"); }catch(e){ console.log("[app] ping fail", e); }
})();

(function(){
  const $ = (q) => document.querySelector(q);
  const pretty = (x)=>{ try{ return JSON.stringify(typeof x==='string'?JSON.parse(x):x,null,2);}catch(_){ return String(x);} };
  const byId = (id)=>document.getElementById(id);

  function safe(fn){ try{ fn(); } catch(e){ console.error(e); try { fetch('/api/client-log',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({level:'error', message:String(e), stack:e.stack||'', where:'safe'})}); } catch(_){}} }

  // Status bar
  async function loadStatus(){
    try {
      const acct = await (await fetch('/api/account')).json();
      byId('acct-id').textContent = acct.id || '?';
      byId('acct-status').textContent = acct.status || '?';
      byId('acct-blocked').textContent = String(acct.trading_blocked);
    } catch(e) {
      byId('acct-id').textContent = 'err';
    }
    try {
      const clk = await (await fetch('/api/clock')).json();
      byId('clock').textContent = `${clk.is_open ? 'OPEN' : 'CLOSED'} ${clk.next_open||''}`;
    } catch(e) {
      byId('clock').textContent = 'err';
    }
  }
  safe(()=> byId('btn-test').addEventListener('click', loadStatus));
  loadStatus();

  // Chart
  let _chart;
  async function drawChart(symbol, timeframe='1Day'){
    if (!symbol) return;
    try {
      const resp = await fetch(`/api/bars?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=200`);
      const js = await resp.json();
      const bars = js.bars || js.results || js || [];
      if (!Array.isArray(bars) || !bars.length) { byId('chart-hint').textContent = 'Nessun dato disponibile.'; return; }
      const labels = bars.map(b => (b.t || b.time || b.timestamp || b.start || '').toString().replace('T',' ').slice(0,16));
      const closes = bars.map(b => Number(b.c ?? b.close));
      if (window.Chart) {
        if (_chart) _chart.destroy();
        _chart = new Chart(byId('symbol-chart'), {
          type: 'line',
          data: { labels, datasets: [{ label: symbol + ' close', data: closes, tension: 0.2 }] },
          options: { responsive: true, interaction:{ intersect:false }, scales: { x: { display: true }, y: { display: true } } }
        });
        byId('chart-symbol').textContent = '('+symbol+')';
        byId('chart-hint').textContent = '';
      } else {
        byId('chart-hint').textContent = 'Chart.js non caricato.';
      }
    } catch(e){ byId('chart-hint').textContent = 'Errore dati grafico.'; }
  }
  safe(()=> byId('timeframe').addEventListener('change', ()=> drawChart(byId('symbol').value.trim(), byId('timeframe').value)));
  safe(()=> byId('refresh-chart').addEventListener('click', ()=> drawChart(byId('symbol').value.trim(), byId('timeframe').value)));

  // Tickers preload + filter
  let ALL_ASSETS = [];
  async function preloadAssets(){
    try{
      const r = await fetch('/api/assets');
      ALL_ASSETS = await r.json();
      renderAssets(ALL_ASSETS);
      byId('search-summary').textContent = `Caricati ${ALL_ASSETS.length} asset.`;
      console.log("[app] assets loaded:", ALL_ASSETS.length);
    }catch(e){
      byId('search-results').innerHTML = '<div class="text-danger small">Errore nel caricamento degli asset.</div>';
    }
  }
  function renderAssets(list){
    const rows = (list||[]).map(a => `
      <tr>
        <td style="white-space:nowrap"><button class="btn btn-sm btn-outline-primary me-1" data-sym="${a.symbol}">Seleziona</button> ${a.symbol}</td>
        <td>${a.name||''}</td>
        <td><span class="badge bg-secondary badge-mono">${a.exchange||''}</span></td>
        <td>${a.tradeable}</td>
      </tr>`).join('');
    byId('search-results').innerHTML = `
      <table class="table table-sm table-striped">
        <thead><tr><th>Symbol</th><th>Name</th><th>Exchange</th><th>Tradeable</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    byId('search-results').querySelectorAll('button[data-sym]').forEach(btn=>{
      btn.addEventListener('click', ()=> {
        const sym = btn.getAttribute('data-sym');
        byId('symbol').value = sym;
        drawChart(sym, byId('timeframe').value);
        byId('order-result').textContent = '';
        byId('symbol-chart').scrollIntoView({behavior:'smooth', block:'center'});
      });
    });
  }
  function filterAssets(term){
    term = (term||'').trim().toUpperCase();
    if (!term) { renderAssets(ALL_ASSETS); byId('search-summary').textContent = `Caricati ${ALL_ASSETS.length} asset.`; return; }
    const out = ALL_ASSETS.filter(a => (a.symbol||'').toUpperCase().includes(term) || (a.name||'').toUpperCase().includes(term));
    byId('search-summary').textContent = `Risultati: ${out.length}/${ALL_ASSETS.length}`;
    renderAssets(out);
  }
  safe(()=> byId('search-input').addEventListener('input', ()=> filterAssets(byId('search-input').value)));
  safe(()=> byId('clear-search').addEventListener('click', ()=> { byId('search-input').value=''; filterAssets(''); }));
  safe(()=> byId('go-symbol').addEventListener('click', ()=>{
    const sym = byId('search-input').value.trim().toUpperCase();
    if (!sym) return;
    byId('symbol').value = sym;
    drawChart(sym, byId('timeframe').value);
  }));

  // Quote hint for Limit price
  async function suggestPrice(){
    const sym = byId('symbol').value.trim();
    if (!sym) return;
    try{
      const r = await fetch(`/api/quote?symbol=${encodeURIComponent(sym)}`);
      const js = await r.json();
      const last = js?.trade?.trade?.p ?? js?.trade?.p;
      const bid = js?.quote?.quote?.bp ?? js?.quote?.bp;
      const ask = js?.quote?.quote?.ap ?? js?.quote?.ap;
      const hint = [`Last: ${last||'?'}`, `Bid: ${bid||'?'}`, `Ask: ${ask||'?'}`].join(' | ');
      byId('quote-hint').textContent = hint;
      if (!byId('limit_price').value && last) byId('limit_price').value = Number(last);
    }catch(e){ byId('quote-hint').textContent = 'N/A'; }
  }
  safe(()=> byId('btn-suggest').addEventListener('click', suggestPrice));

  // Orders / Positions
  async function loadOrders(){ try{ const r = await fetch('/api/orders'); byId('orders-json').textContent = pretty(await r.text()); }catch(e){ byId('orders-json').textContent = String(e);} }
  async function loadPositions(){ try{ const r = await fetch('/api/positions'); byId('positions-json').textContent = pretty(await r.text()); }catch(e){ byId('positions-json').textContent = String(e);} }
  safe(()=> byId('check-orders').addEventListener('click', loadOrders));
  safe(()=> byId('check-positions').addEventListener('click', loadPositions));

  // Toggle limit group
  const limitGroup = byId('limit_price_group');
  function toggleLimit(){ limitGroup.style.display = byId('order_type').value === 'limit' ? '' : 'none'; }
  safe(()=> byId('order_type').addEventListener('change', toggleLimit)); toggleLimit();

  // Send order
  safe(()=> byId('send-order').addEventListener('click', async ()=>{
    const form = byId('order-form');
    const fd = new FormData(form);
    const obj = {};
    for (const [k,v] of fd.entries()) {
      if (v === "" || v === null) continue;
      if (["qty","limit_price","tp_price","sl_price"].includes(k)) obj[k] = Number(v);
      else if (k === "extended_hours") obj[k] = true;
      else obj[k] = v;
    }
    const out = byId('order-result');
    out.textContent = "Invio ordine...";
    try {
      const resp = await fetch('/api/order', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(obj)});
      const txt = await resp.text();
      out.textContent = `HTTP ${resp.status}\n` + pretty(txt);
      loadOrders(); loadPositions();
    } catch (err) {
      out.textContent = 'Errore di rete: ' + err;
    }
  }));

  // Init
  preloadAssets();
  loadOrders(); loadPositions();
})();
