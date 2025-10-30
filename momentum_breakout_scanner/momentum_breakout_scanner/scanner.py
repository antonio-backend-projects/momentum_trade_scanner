import os, time, json, sys, pytz, yaml
import pandas as pd
from dotenv import load_dotenv

from signals import compute_signals_for_symbols
from notify.telegram import send_telegram  # import pulito dal package notify

# ==== ENV & CONFIG ====
load_dotenv()
with open("config.yaml", "r") as f:
    CFG = yaml.safe_load(f)

ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SEC = os.getenv("ALPACA_API_SECRET")

TG_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_ENABLED = bool(TG_TOKEN and TG_CHAT_ID and os.getenv("TELEGRAM_SILENT","0") != "1")

if not (ALPACA_KEY and ALPACA_SEC):
    print("Missing Alpaca API keys in environment (.env).")
    sys.exit(1)

STATE_PATH = "state/state.json"
os.makedirs("state", exist_ok=True)
if not os.path.exists(STATE_PATH):
    with open(STATE_PATH, "w") as f:
        json.dump({}, f)

# ==== HELPERS ====
def load_tickers():
    df = pd.read_csv("tickers.csv").dropna()
    df["Symbol"] = df["Symbol"].astype(str).str.upper().str.strip()
    df["Benchmark"] = df["Benchmark"].astype(str).str.upper().str.strip()
    return df[df["Symbol"].str.len() > 0]

def load_state():
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)

# ==== MAIN SCAN ====
def run_scan():
    tickers_df = load_tickers()
    symbols = tickers_df["Symbol"].tolist()
    bench_map = {
        row["Symbol"]: (row["Benchmark"] if row["Benchmark"] and row["Benchmark"] != "-" else "SPY")
        for _, row in tickers_df.iterrows()
    }

    results = compute_signals_for_symbols(
        symbols=symbols,
        bench_map=bench_map,
        alpaca_key=ALPACA_KEY,
        alpaca_sec=ALPACA_SEC,
        timeframe=CFG.get("timeframe","1H"),
        base_len_days=int(CFG.get("baseLenDays",12)),
        donch_len_hours=int(CFG.get("donchLenHours",288)),
        rv_min=float(CFG.get("rvMin",2.5)),
        confirm_on_close=bool(CFG.get("confirmOnClose", True)),
        use_high_intrabar=bool(CFG.get("useHighIntrabar", False)),
        use_1030_et=bool(CFG.get("use1030ET", False)),
        # nuovi flag per test/diagnostica
        show_pre_signal=bool(CFG.get("showPreSignal", False)),
        pre_buffer_pct=float(CFG.get("preBufferPct", 0.3)),
    )

    state = load_state()
    alerts_sent = 0

    # ALERT “pieni”
    for sym, res in results.items():
        for side in ("LONG","SHORT"):
            if not res.get(side, False):
                continue
            key = f"{sym}:{side}"
            last_ts = res.get("bar_time")
            if state.get(key) == last_ts:
                continue  # de-dup

            parts = [
                f"🔔 {side} on {sym}",
                f"Time: {last_ts}",
                f"Benchmark: {res.get('benchmark','SPY')}",
                f"RV: {res.get('rv_val', None)}  (min {res.get('rv_min', None)})",
                f"Bias3D: {res.get('ema_bias','?')} | RS: {res.get('rs_dir','?')} | Trend200D: {res.get('trend_ok','?')}",
                f"Trigger: {res.get('trigger_info','')}"
            ]
            text = "\n".join([p for p in parts if p])

            if TELEGRAM_ENABLED:
                send_telegram(TG_TOKEN, TG_CHAT_ID, text)
            else:
                print("\n=== ALERT (console preview) ===\n" + text + "\n===============================\n")

            state[key] = last_ts
            alerts_sent += 1

    save_state(state)
    print(f"Scan complete. Alerts sent: {alerts_sent}")

    # --- Se nessun alert: stampa PRE-SIGNALS e mini DEBUG ---
    if alerts_sent == 0:
        # PRE-SIGNALS
        pre_lines = []
        for sym, res in results.items():
            if res.get("pre_long") or res.get("pre_short"):
                d = res.get("debug", {})
                side = "LONG" if res.get("pre_long") else "SHORT"
                pre_lines.append(
                    f"{sym} PRE-{side} | rv={d.get('rv_val')} hh={d.get('hh')} ll={d.get('ll')} "
                    f"dist_up%={d.get('dist_up_pct')} dist_dn%={d.get('dist_down_pct')}"
                )
        if pre_lines:
            print("\n--- PRE-SIGNALS ---")
            print("\n".join(pre_lines))

        # DEBUG SAMPLE (5 simboli random) se non ci sono pre-signals
        if not pre_lines:
            import random
            sample = random.sample(list(results.items()), k=min(5, len(results)))
            print("\n--- DEBUG SAMPLE (5) ---")
            for sym, res in sample:
                d = res.get("debug", {})
                print(
                    f"{sym}: Lbias={d.get('ema_bias_long')} RSup={d.get('rs_up')} "
                    f"T200L={d.get('trend_ok_long')} BU={d.get('break_up')} "
                    f"RVok={d.get('rv_ok')} rv={d.get('rv_val')}"
                )

if __name__ == "__main__":
    watch = os.getenv("WATCH","0") == "1"
    if not watch:
        run_scan()
    else:
        interval = int(CFG.get("scanEveryMinutes",60))
        while True:
            try:
                run_scan()
            except Exception as e:
                print("Scan error:", e, file=sys.stderr)
            time.sleep(interval * 60)
