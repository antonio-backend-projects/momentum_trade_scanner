import os, requests
from db import insert_order, update_order_status

ALP_ENV = os.environ.get("ALPACA_ENV","paper")
ALPACA_TRADING_BASE = "https://paper-api.alpaca.markets" if ALP_ENV=="paper" else "https://api.alpaca.markets"

def _headers():
    return {
        "APCA-API-KEY-ID": os.environ.get("ALPACA_API_KEY",""),
        "APCA-API-SECRET-KEY": os.environ.get("ALPACA_API_SECRET","")
    }

def _panic(): return os.environ.get("PANIC_CLOSE","0")=="1"

def place_simple_equity(symbol, side, qty, type_="market", limit_price=None, tif="gtc", extended=False, client_id=None):
    if _panic():
        print("PANIC_CLOSE=1: skip order"); return None
    url = f"{ALPACA_TRADING_BASE}/v2/orders"
    body = {"symbol": symbol, "side": side, "type": type_, "qty": str(int(qty)), "time_in_force": tif, "extended_hours": bool(extended)}
    if client_id: body["client_order_id"] = client_id
    if type_=="limit" and limit_price is not None: body["limit_price"] = float(limit_price)
    r = requests.post(url, json=body, headers=_headers(), timeout=15); r.raise_for_status()
    resp = r.json(); insert_order(client_id or resp.get("client_order_id"), resp.get("id"), symbol, "equity", side, qty, type_, "simple", limit_price, None, None, resp.get("status","new"))
    return resp

def place_bracket_equity(symbol, side, qty, entry_type, entry_px, tp_px, sl_px, tif="gtc", extended=False, client_id=None):
    if _panic():
        print("PANIC_CLOSE=1: skip order"); return None
    url = f"{ALPACA_TRADING_BASE}/v2/orders"
    body = {"symbol": symbol, "side": side, "type": entry_type, "qty": str(int(qty)), "time_in_force": tif, "extended_hours": bool(extended),
            "order_class": "bracket", "take_profit": {"limit_price": float(tp_px)}, "stop_loss": {"stop_price": float(sl_px)}}
    if entry_type=="limit": body["limit_price"] = float(entry_px)
    if client_id: body["client_order_id"] = client_id
    r = requests.post(url, json=body, headers=_headers(), timeout=15); r.raise_for_status()
    resp = r.json(); insert_order(client_id or resp.get("client_order_id"), resp.get("id"), symbol, "equity", side, qty, entry_type, "bracket", entry_px, sl_px, tp_px, resp.get("status","new"), legs=resp.get("legs"))
    return resp

def replace_order_stop_to_be(alpaca_order_id, be_price):
    url = f"{ALPACA_TRADING_BASE}/v2/orders/{alpaca_order_id}"
    r = requests.patch(url, json={"stop_price": float(be_price)}, headers=_headers(), timeout=15); r.raise_for_status()
    update_order_status(alpaca_order_id, r.json().get("status","replaced"), legs=None)
    return r.json()

def place_limit_partial(symbol, qty, limit_px, side="sell", tif="gtc"):
    if _panic(): print("PANIC_CLOSE=1: skip order"); return None
    url = f"{ALPACA_TRADING_BASE}/v2/orders"
    body = {"symbol": symbol, "side": side, "type": "limit", "limit_price": float(limit_px), "qty": str(int(qty)), "time_in_force": tif}
    r = requests.post(url, json=body, headers=_headers(), timeout=15); r.raise_for_status()
    return r.json()

def panic_close_all():
    if not _panic(): return {"ok": True, "detail": "not in panic mode"}
    requests.delete(f"{ALPACA_TRADING_BASE}/v2/orders", headers=_headers(), timeout=15)
    r = requests.get(f"{ALPACA_TRADING_BASE}/v2/positions", headers=_headers(), timeout=15)
    if r.status_code!=200: return {"ok": False, "detail": "positions list failed"}
    for p in r.json():
        sym = p["symbol"]; qty = abs(int(float(p["qty"])))
        side = "sell" if float(p["qty"])>0 else "buy"
        place_simple_equity(sym, side, qty, type_="market")
    return {"ok": True}
