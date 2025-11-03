
import os, time, requests
from db import insert_order, update_order_status  # kept for backward-compat; not strictly required in this minimal patch

# ---- Alpaca endpoints ----
ALP_ENV = os.environ.get("ALPACA_ENV", "paper")
ALPACA_TRADING_BASE = "https://paper-api.alpaca.markets" if ALP_ENV == "paper" else "https://api.alpaca.markets"

def _headers():
    return {
        "APCA-API-KEY-ID": os.environ.get("ALPACA_API_KEY", ""),
        "APCA-API-SECRET-KEY": os.environ.get("ALPACA_API_SECRET", ""),
        "Content-Type": "application/json"
    }

def _panic():
    return os.environ.get("PANIC_CLOSE", "0") == "1"

def _client_id(symbol: str) -> str:
    base = f"{symbol}-{int(time.time())}"
    return base[:48]

# ---------- SIMPLE EQUITY ORDER ----------
def place_simple_equity(symbol, side, qty=None, type_="market", limit_price=None, tif="day", extended=False, client_id=None, notional=None):
    """Submit a simple market/limit order.
    - Pass either qty (int >=1) or notional (float >= 1). Not both.
    - MARKET orders are RTH only (extended=False). For pre/after set type_='limit' + extended=True.
    """
    if _panic():
        return {"ok": False, "detail": "panic mode active"}

    if qty is not None and notional is not None:
        raise ValueError("Pass only qty OR notional")
    body = {
        "symbol": symbol,
        "side": side,
        "type": type_,
        "time_in_force": tif,
        "extended_hours": bool(extended),
        "client_order_id": client_id or _client_id(symbol),
    }

    if notional is not None:
        notional = float(notional)
        if notional < 1:
            raise ValueError("notional < 1$")
        body["notional"] = round(notional, 2)
    else:
        if qty is None:
            raise ValueError("qty or notional required")
        q = int(qty)
        if q < 1:
            raise ValueError("qty < 1")
        body["qty"] = str(q)

    if type_ == "limit":
        if limit_price is None:
            raise ValueError("limit order without limit_price")
        body["limit_price"] = round(float(limit_price), 2)
    elif type_ != "market":
        raise ValueError(f"unsupported order type: {type_}")

    url = f"{ALPACA_TRADING_BASE}/v2/orders"
    r = requests.post(url, json=body, headers=_headers(), timeout=20)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "")
        raise RuntimeError(f"Alpaca order error: {detail}") from e
    return r.json()

# ---------- BRACKET ORDER ----------
def place_bracket_equity(symbol, side, qty=None, entry_type="market", entry_px=None, tp_px=None, sl_px=None,
                         tif="day", extended=False, client_id=None, notional=None):
    """Submit a bracket order.
    - entry_type: 'market' or 'limit' (limit requires entry_px)
    - tp_px: take profit limit price (optional)
    - sl_px: stop price for stop-loss (optional)
    - Pass either qty OR notional.
    """
    if _panic():
        return {"ok": False, "detail": "panic mode active"}

    if qty is not None and notional is not None:
        raise ValueError("Pass only qty OR notional")

    body = {
        "symbol": symbol,
        "side": side,
        "time_in_force": tif,
        "type": entry_type if entry_type in ("market", "limit") else "market",
        "order_class": "bracket",
        "extended_hours": bool(extended),
        "client_order_id": client_id or _client_id(symbol),
    }

    if entry_type == "limit":
        if entry_px is None:
            raise ValueError("limit entry without entry_px")
        body["limit_price"] = round(float(entry_px), 2)

    if tp_px is not None:
        body["take_profit"] = {"limit_price": round(float(tp_px), 2)}
    if sl_px is not None:
        # stop-loss as stop-market (no limit leg); change to stop-limit if desired
        body["stop_loss"] = {"stop_price": round(float(sl_px), 2)}

    if notional is not None:
        notional = float(notional)
        if notional < 1:
            raise ValueError("notional < 1$")
        body["notional"] = round(notional, 2)
    else:
        if qty is None:
            raise ValueError("qty or notional required")
        q = int(qty)
        if q < 1:
            raise ValueError("qty < 1")
        body["qty"] = str(q)

    # MARKET orders in extended hours are rejected by Alpaca
    if body["type"] == "market" and body.get("extended_hours"):
        raise ValueError("market orders are not allowed with extended_hours=True; use limit" )

    url = f"{ALPACA_TRADING_BASE}/v2/orders"
    r = requests.post(url, json=body, headers=_headers(), timeout=20)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "")
        raise RuntimeError(f"Alpaca order error: {detail}") from e
    return r.json()

# ---------- PARTIAL LIMIT (helper) ----------
def place_limit_partial(symbol, side, qty, limit_px, tif="day", client_id=None):
    body = {
        "symbol": symbol, "side": side, "type": "limit",
        "limit_price": round(float(limit_px), 2),
        "time_in_force": tif, "qty": str(int(qty)),
        "client_order_id": client_id or _client_id(symbol),
    }
    url = f"{ALPACA_TRADING_BASE}/v2/orders"
    r = requests.post(url, json=body, headers=_headers(), timeout=20)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        detail = getattr(e.response, "text", "")
        raise RuntimeError(f"Alpaca order error: {detail}") from e
    return r.json()

def panic_close_all():
    if not _panic():
        return {"ok": True, "detail": "not in panic mode"}
    # Cancel all open orders
    requests.delete(f"{ALPACA_TRADING_BASE}/v2/orders", headers=_headers(), timeout=20)
    # Close positions with market orders
    r = requests.get(f"{ALPACA_TRADING_BASE}/v2/positions", headers=_headers(), timeout=20)
    r.raise_for_status()
    for p in r.json():
        sym = p["symbol"]; q = abs(int(float(p["qty"])))
        side = "sell" if float(p["qty"]) > 0 else "buy"
        place_simple_equity(sym, side, qty=q, type_="market", tif="day", extended=False)
    return {"ok": True}
