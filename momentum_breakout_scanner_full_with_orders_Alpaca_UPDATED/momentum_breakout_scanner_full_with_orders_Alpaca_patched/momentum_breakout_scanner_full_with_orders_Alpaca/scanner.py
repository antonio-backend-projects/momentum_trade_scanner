
def _alp_headers():
    import os
    return {"APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY",""),
            "APCA-API-SECRET-KEY": os.getenv("ALPACA_API_SECRET","")}

def _alpaca_clock_open():
    try:
        r = requests.get("https://paper-api.alpaca.markets/v2/clock", headers=_alp_headers(), timeout=10)
        r.raise_for_status()
        return r.json().get("is_open", False)
    except Exception:
        return False

def _open_positions_count():
    try:
        r = requests.get("https://paper-api.alpaca.markets/v2/positions", headers=_alp_headers(), timeout=10)
        if r.status_code == 200:
            return len(r.json())
    except Exception:
        pass
    return 0

def _compute_notional():
    equity = float(get_account_equity() or 0.0)
    rp = cfg_get("riskPct", 1.0)
    # allow rp expressed as 1.0 (=100%) or 0.01 (=1%)
    risk = float(rp) if float(rp) <= 1.0 else float(rp)/100.0
    min_notional = float(cfg_get("minNotional", 50.0) or 0)
    max_notional = cfg_get("maxNotional", None)
    try:
        max_notional = None if max_notional is None else float(max_notional)
    except:
        max_notional = None
    n = max(min_notional, equity * risk)
    if max_notional: n = min(n, max_notional)
    return n

def place_order_from_signal(sym, side, entry_type, entry_px, tp_px, sl_px):
    if cfg_get("useLongOnly", False) and side.lower() == "sell":
        notify(f"SKIP {sym}: long-only mode")
        return None

    if cfg_get("rthOnly", True) and not _alpaca_clock_open():
        if cfg_get("retryMissedSignals", True):
            enqueue(sym, side, {"entry_type":entry_type, "entry_px":entry_px, "tp_px":tp_px, "sl_px":sl_px})
            notify(f"QUEUED {sym}: market closed")
            return "queued"
        else:
            notify(f"SKIP {sym}: market closed")
            return None

    if _open_positions_count() >= int(cfg_get("maxConcurrentPositions",5) or 5):
        if cfg_get("retryMissedSignals", True):
            enqueue(sym, side, {"entry_type":entry_type, "entry_px":entry_px, "tp_px":tp_px, "sl_px":sl_px})
            notify(f"QUEUED {sym}: max positions reached")
            return "queued"
        else:
            notify(f"SKIP {sym}: max positions reached")
            return None

    notional = _compute_notional()
    tif = cfg_get("time_in_force", "gtc") or "gtc"
    res = place_bracket_equity(sym, side, qty=None, entry_type=entry_type, entry_px=entry_px,
                               tp_px=tp_px, sl_px=sl_px, tif=tif, extended=False, client_id=None, notional=notional)
    notify(f"ORDER sent (bracket): {sym} notional={notional:.2f} entry={entry_px} tp={tp_px} sl={sl_px}")
    return res

def process_queued_signals():
    ttl_min = int(cfg_get("signalQueueTTLMinutes", 240) or 0)
    ttl_sec = ttl_min * 60
    if cfg_get("rthOnly", True) and not _alpaca_clock_open():
        return 0
    processed = 0
    for sid, sym, side, payload in fetch_due(ttl_sec):
        try:
            place_order_from_signal(sym, side, payload.get("entry_type"), payload.get("entry_px"),
                                    payload.get("tp_px"), payload.get("sl_px"))
            mark_done(sid, "sent")
            processed += 1
        except Exception as e:
            notify(f"RETRY LATER {sym}: {e}")
    return processed


CFG_DEFAULTS = {
    "useLongOnly": False,
    "rthOnly": True,
    "time_in_force": "gtc",
    "riskPct": 1.0,
    "minNotional": 50.0,
    "maxNotional": None,
    "maxConcurrentPositions": 5,
    "retryMissedSignals": True,
    "signalQueueTTLMinutes": 240
}
def cfg_get(name, fallback=None):
    try:
        return CFG.get(name, CFG_DEFAULTS.get(name, fallback))
    except NameError:
        return CFG_DEFAULTS.get(name, fallback)

import json
from signal_queue import enqueue, fetch_due, mark_done
from trade import get_account_equity, place_bracket_equity
import os, time, json, sys, yaml
import pandas as pd
from dotenv import load_dotenv
from signals import compute_signals_for_symbols
from notify.telegram import send_telegram
from db import init_db, insert_signal
from trade import place_bracket_equity

load_dotenv()
with open("config.yaml", "r") as f:
    CFG = yaml.safe_load(f)

ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SEC = os.getenv("ALPACA_API_SECRET")
TG_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_ENABLED = bool(TG_TOKEN and TG_CHAT_ID and os.getenv("TELEGRAM_SILENT","0") != "1")

if not (ALPACA_KEY and ALPACA_SEC):
    print("Missing Alpaca API keys in environment (.env)."); sys.exit(1)

STATE_PATH = "state/state.json"
os.makedirs("state", exist_ok=True)
if not os.path.exists(STATE_PATH):
    with open(STATE_PATH, "w") as f: json.dump({}, f)

init_db()

def load_tickers():
    df = pd.read_csv("tickers.csv").dropna()
    df["Symbol"] = df["Symbol"].astype(str).str.upper().str.strip()
    df["Benchmark"] = df["Benchmark"].astype(str).str.upper().str.strip()
    return df[df["Symbol"].str.len() > 0]

def load_state():
    try:
        with open(STATE_PATH, "r") as f: return json.load(f)
    except Exception: return {}

def save_state(state):
    with open(STATE_PATH, "w") as f: json.dump(state, f, indent=2)

def notify(text: str):
    if TELEGRAM_ENABLED: send_telegram(TG_TOKEN, TG_CHAT_ID, text)
    else: print("\n=== ALERT / INFO ===\n" + text + "\n====================\n")

def calc_equity_qty(account_equity_usd: float, risk_pct: float, entry_px: float, stop_px: float):
    risk_value = account_equity_usd * (risk_pct/100.0)
    per_share_risk = max(abs(entry_px - stop_px), 1e-4)
    qty = int(risk_value // per_share_risk)
    return max(qty, 1)

def run_scan():
    tickers_df = load_tickers()
    symbols = tickers_df["Symbol"].tolist()
    bench_map = {row["Symbol"]: (row["Benchmark"] if row["Benchmark"] and row["Benchmark"] != "-" else "SPY") for _, row in tickers_df.iterrows()}

    results = compute_signals_for_symbols(
        symbols=symbols, bench_map=bench_map, alpaca_key=ALPACA_KEY, alpaca_sec=ALPACA_SEC,
        timeframe=CFG.get("timeframe","1Hour"), base_len_days=int(CFG.get("baseLenDays",12)),
        donch_len_hours=int(CFG.get("donchLenHours",288)), rv_min=float(CFG.get("rvMin",2.5)),
        confirm_on_close=bool(CFG.get("confirmOnClose", True)), use_high_intrabar=bool(CFG.get("useHighIntrabar", False)),
        use_1030_et=bool(CFG.get("use1030ET", False)), show_pre_signal=bool(CFG.get("showPreSignal", False)),
        pre_buffer_pct=float(CFG.get("preBufferPct", 0.3)), batch_size=int(CFG.get("batchSize", 80)),
    )

    state = load_state(); alerts_sent = 0; enable_trading = bool(CFG.get("enableTrading", False))
    for sym, res in results.items():
        for side in ("LONG","SHORT"):
            if not res.get(side, False): continue
            key = f"{sym}:{side}"; last_ts = res.get("bar_time")
            if state.get(key) == last_ts: continue
            parts = [
                f"🔔 {side} on {sym}", f"Time: {last_ts}", f"Benchmark: {res.get('benchmark','SPY')}",
                f"RV: {res.get('rv_val', None)}  (min {res.get('rv_min', None)})",
                f"Bias3D: {res.get('ema_bias','?')} | RS: {res.get('rs_dir','?')} | Trend200D: {res.get('trend_ok','?')}",
                f"Trigger: {res.get('trigger_info','')}"
            ]
            notify("\n".join([p for p in parts if p]))
            insert_signal(sym, side, res.get("rv_val"), res.get("trigger_info"), res.get("debug",{}).get("hh"), res.get("debug",{}).get("ll"), CFG)
            if enable_trading:
                entry_px = res.get("debug",{}).get("hh") if side=="LONG" else res.get("debug",{}).get("ll")
                if entry_px is None or entry_px==0: entry_px = res.get("debug",{}).get("last_close", 0.0)
                sl_px = entry_px * (0.99 if side=="LONG" else 1.01)
                rr = float(CFG.get("partialAtR", 2.0))
                tp_px = entry_px * (1 + 0.01*rr*2) if side=="LONG" else entry_px * (1 - 0.01*rr*2)
                qty = calc_equity_qty(100000.0, float(CFG.get("riskPct",1.0)), entry_px, sl_px)
                try:
                    place_bracket_equity(symbol=sym, side=("buy" if side=="LONG" else "sell"), qty=qty, entry_type="limit", entry_px=entry_px, tp_px=tp_px, sl_px=sl_px)
                    notify(f"ORDER sent (bracket): {sym} qty={qty} entry={entry_px} tp={tp_px} sl={sl_px}")
                except Exception as e:
                    msg = str(e)
                    try:
                        import requests
                        if isinstance(e, requests.HTTPError) and getattr(e, "response", None):
                            msg = e.response.text
                    except Exception:
                        pass
                    notify(f"ORDER error: {sym} {msg}")
            state[key] = last_ts; alerts_sent += 1
    save_state(state)
    print(f"Scan complete. Alerts sent: {alerts_sent}")
    if alerts_sent == 0:
        pre_lines = []
        for sym, res in results.items():
            if res.get("pre_long") or res.get("pre_short"):
                d = res.get("debug", {})
                side = "LONG" if res.get("pre_long") else "SHORT"
                pre_lines.append(f"{sym} PRE-{side} | rv={d.get('rv_val')} hh={d.get('hh')} ll={d.get('ll')} dist_up%={d.get('dist_up_pct')} dist_dn%={d.get('dist_down_pct')}")
        if pre_lines:
            print("\n--- PRE-SIGNALS ---\n" + "\n".join(pre_lines))
        else:
            import random
            sample = random.sample(list(results.items()), k=min(5, len(results)))
            print("\n--- DEBUG SAMPLE (5) ---")
            for sym, res in sample:
                d = res.get("debug", {})
                print(f"{sym}: Lbias={d.get('ema_bias_long')} RSup={d.get('rs_up')} T200L={d.get('trend_ok_long')} BU={d.get('break_up')} RVok={d.get('rv_ok')} rv={d.get('rv_val')}")

if __name__ == "__main__":
    watch = os.getenv("WATCH","0") == "1"
    if not watch:
        run_scan()
    else:
        import sys
        interval = int(CFG.get("scanEveryMinutes",60))
        while True:
            try:
                run_scan()
            except Exception as e:
                print("Scan error:", e, file=sys.stderr)
            time.sleep(interval * 60)
