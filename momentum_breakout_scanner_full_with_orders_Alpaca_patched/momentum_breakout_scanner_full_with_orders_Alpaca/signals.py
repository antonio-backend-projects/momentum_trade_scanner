import math, pytz, requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

ALPACA_BASE = "https://data.alpaca.markets"

def _alpaca_headers(key, sec):
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}

def _ny_time(ts_utc): return ts_utc.astimezone(pytz.timezone("America/New_York"))

def _tf_norm(tf: str) -> str:
    tf = (tf or "").strip()
    return {"1H":"1Hour","1h":"1Hour","1hour":"1Hour"}.get(tf, tf)

def fetch_bars_multi_symbols(symbols, timeframe, start_iso, end_iso, key, sec):
    url = f"{ALPACA_BASE}/v2/stocks/bars"
    headers = _alpaca_headers(key, sec)
    params = {"timeframe": timeframe, "symbols": ",".join(symbols), "start": start_iso, "end": end_iso, "limit": 10000, "adjustment": "all", "feed": "iex"}
    all_bars, next_token = {}, None
    while True:
        if next_token: params["page_token"] = next_token
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status(); data = resp.json(); bars = data.get("bars", {})
        for sym, entries in bars.items(): all_bars.setdefault(sym, []).extend(entries)
        next_token = data.get("next_page_token")
        if not next_token: break
    out = {}
    for sym, entries in all_bars.items():
        if not entries:
            out[sym] = pd.DataFrame(columns=["t","o","h","l","c","v"]); continue
        df = pd.DataFrame(entries)
        df["t"] = pd.to_datetime(df["t"], utc=True)
        df = df.sort_values("t").reset_index(drop=True)
        out[sym] = df.rename(columns={"t":"time","o":"open","h":"high","l":"low","c":"close","v":"volume"})
    return out

def linreg_slope(y_vals):
    y = np.array(y_vals, dtype=float); x = np.arange(len(y), dtype=float)
    if len(y) < 2: return 0.0
    return np.polyfit(x, y, 1)[0]

def compute_signals_for_symbols(symbols, bench_map, alpaca_key, alpaca_sec,
                                timeframe="1Hour", base_len_days=12, donch_len_hours=288,
                                rv_min=2.5, confirm_on_close=True, use_high_intrabar=False,
                                use_1030_et=False, batch_size=80,
                                show_pre_signal=False, pre_buffer_pct=0.3):

    timeframe = _tf_norm(timeframe) or "1Hour"
    now_utc = datetime.now(timezone.utc)
    end_utc = now_utc - timedelta(minutes=1)
    hours_back = max(donch_len_hours + 60, 400)
    start_h = now_utc - timedelta(hours=hours_back)
    start_d = now_utc - timedelta(days=400)
    benches = sorted(set([b for b in bench_map.values() if b and b != "-"]))
    unique_symbols = list(dict.fromkeys(symbols + benches))
    hourly, daily = {}, {}
    for i in range(0, len(unique_symbols), batch_size):
        chunk = unique_symbols[i:i+batch_size]
        out = fetch_bars_multi_symbols(chunk, timeframe, start_h.isoformat(), end_utc.isoformat(), alpaca_key, alpaca_sec)
        hourly.update(out)
    for i in range(0, len(unique_symbols), batch_size):
        chunk = unique_symbols[i:i+batch_size]
        out = fetch_bars_multi_symbols(chunk, "1Day", start_d.isoformat(), end_utc.isoformat(), alpaca_key, alpaca_sec)
        daily.update(out)
    results = {}
    for sym in symbols:
        res = {"benchmark": bench_map.get(sym, "SPY"), "rv_min": rv_min, "debug": {}}
        try:
            hdf = hourly.get(sym, pd.DataFrame()); ddf = daily.get(sym, pd.DataFrame())
            bmk = bench_map.get(sym, "SPY"); bdf = daily.get(bmk, pd.DataFrame())
            if hdf is None or ddf is None or hdf.empty or ddf.empty or bdf is None or bdf.empty:
                res["debug"]["reason"] = "missing_data"; results[sym] = res; continue
            ddf = ddf.set_index("time"); bdf = bdf.set_index("time")
            join = ddf[["close"]].join(bdf[["close"]].rename(columns={"close":"bench"}), how="inner")
            join["ema20"] = join["close"].ewm(span=20, adjust=False).mean()
            join["sma200"] = join["close"].rolling(200).mean()
            join["rs"] = join["close"] / join["bench"]
            join["rs_ma50"] = join["rs"].rolling(50).mean()
            lr_window = join["rs"].tail(10).dropna().values
            rs_slope = linreg_slope(lr_window) if len(lr_window) >= 2 else 0.0
            last3 = join.tail(3)
            ema_bias_long  = bool((last3["close"] > last3["ema20"]).all())
            ema_bias_short = bool((last3["close"] < last3["ema20"]).all())
            trend_ok_long  = bool(join["close"].iloc[-1] > join["sma200"].iloc[-1])
            trend_ok_short = bool(join["close"].iloc[-1] < join["sma200"].iloc[-1])
            rs_up   = bool((join["rs"].iloc[-1] > join["rs_ma50"].iloc[-1]) and (rs_slope > 0))
            rs_down = bool((join["rs"].iloc[-1] < join["rs_ma50"].iloc[-1]) and (rs_slope < 0))
            hdf = hdf.set_index("time")
            lookback = max(donch_len_hours, base_len_days*24)
            prev = hdf.iloc[:-1] if len(hdf) > 1 else hdf.iloc[:0]
            hh = prev["high"].tail(lookback).max() if not prev.empty else np.nan
            ll = prev["low"].tail(lookback).min() if not prev.empty else np.nan
            last_bar = hdf.iloc[-1]
            last_time = last_bar.name
            last_close = float(last_bar["close"]); last_high = float(last_bar["high"]); last_low = float(last_bar["low"]); last_vol = float(last_bar["volume"])
            vol_ma50 = prev["volume"].tail(50).mean() if not prev.empty else np.nan
            rv_val = float(last_vol / vol_ma50) if (vol_ma50 and vol_ma50 > 0) else np.nan
            rv_ok  = bool(rv_val >= float(rv_min)) if not math.isnan(rv_val) else False
            if confirm_on_close:
                break_up   = (not math.isnan(hh)) and (last_close > hh)
                break_down = (not math.isnan(ll)) and (last_close < ll)
                trig_info = "close vs Donchian (confirmed)"
            else:
                if use_high_intrabar:
                    break_up   = (not math.isnan(hh)) and (last_high > hh)
                    break_down = (not math.isnan(ll)) and (last_low  < ll)
                    trig_info = "intrabar HIGH/LOW vs Donchian"
                else:
                    break_up   = (not math.isnan(hh)) and (last_close > hh)
                    break_down = (not math.isnan(ll)) and (last_close < ll)
                    trig_info = "close intrabar vs Donchian"
            allow_bar = True
            if use_1030_et:
                ny = last_time.tz_convert("America/New_York"); allow_bar = (ny.hour==10 and ny.minute==30)
            long_core  = (ema_bias_long and rs_up   and trend_ok_long  and break_up   and rv_ok and allow_bar)
            short_core = (ema_bias_short and rs_down and trend_ok_short and break_down and rv_ok and allow_bar)
            pre_long = pre_short = False
            dist_up_pct = dist_down_pct = None
            if show_pre_signal and not long_core and not short_core:
                if not math.isnan(hh) and hh > 0:
                    dist_up_pct = abs((last_high if use_high_intrabar else last_close) / hh - 1.0) * 100.0
                    pre_long = (ema_bias_long and rs_up and trend_ok_long and dist_up_pct is not None and dist_up_pct <= pre_buffer_pct)
                if not math.isnan(ll) and ll > 0:
                    dist_down_pct = abs((last_low if use_high_intrabar else last_close) / ll - 1.0) * 100.0
                    pre_short = (ema_bias_short and rs_down and trend_ok_short and dist_down_pct is not None and dist_down_pct <= pre_buffer_pct)
            res["debug"] = {
                "ema_bias_long": ema_bias_long,
                "ema_bias_short": ema_bias_short,
                "rs_up": rs_up,
                "rs_down": rs_down,
                "trend_ok_long": trend_ok_long,
                "trend_ok_short": trend_ok_short,
                "break_up": bool(break_up),
                "break_down": bool(break_down),
                "rv_ok": rv_ok,
                "rv_val": None if math.isnan(rv_val) else round(rv_val, 2),
                "hh": None if math.isnan(hh) else round(hh, 4),
                "ll": None if math.isnan(ll) else round(ll, 4),
                "last_close": round(last_close, 4),
                "last_high": round(last_high, 4),
                "last_low": round(last_low, 4),
                "dist_up_pct": None if dist_up_pct is None else round(dist_up_pct, 3),
                "dist_down_pct": None if dist_down_pct is None else round(dist_down_pct, 3),
            }
            res.update({
                "LONG": bool(long_core), "SHORT": bool(short_core),
                "pre_long": bool(pre_long), "pre_short": bool(pre_short),
                "rv_val": None if math.isnan(rv_val) else round(rv_val, 2),
                "ema_bias": f"L:{ema_bias_long} / S:{ema_bias_short}",
                "rs_dir": f"UP:{rs_up} / DOWN:{rs_down}",
                "trend_ok": f"L:{trend_ok_long} / S:{trend_ok_short}",
                "trigger_info": trig_info,
                "bar_time": last_bar.name.tz_convert("UTC").isoformat(),
            })
        except Exception as e:
            res["error"] = str(e)
        results[sym] = res
    return results
