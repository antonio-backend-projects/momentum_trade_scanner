import requests, os, math, time
from db import insert_order, update_order_status  # lasciato per compat; non obbligatorio

# ---- Alpaca endpoints ----
ALP_ENV = os.environ.get("ALPACA_ENV", "paper")
ALPACA_TRADING_BASE = "https://paper-api.alpaca.markets" if ALP_ENV == "paper" else "https://api.alpaca.markets"

SAFE_BP_BUFFER = float(os.environ.get("SAFE_BP_BUFFER", "0.95"))  # usa max 95% della buying power

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

def _get_account():
    r = requests.get(f"{ALPACA_TRADING_BASE}/v2/account", headers=_headers(), timeout=20)
    r.raise_for_status()
    return r.json()

def _cap_notional_to_bp(bp: float, requested_notional: float) -> float:
    """Cap del notional per restare entro BP * buffer."""
    return min(float(requested_notional), float(bp) * SAFE_BP_BUFFER)

def _qty_from_notional(notional: float, px: float) -> int:
    """Converte notional in qty intera non negativa."""
    if px is None or px <= 0:
        return 0
    return max(0, int(math.floor(float(notional) / float(px))))

# ---------- SIMPLE EQUITY ORDER ----------
def place_simple_equity(symbol, side, qty=None, type_="market", limit_price=None, tif="day", extended=False, client_id=None, notional=None):
    """
    - Passa o qty (int >=1) O notional (float >=1), non entrambi.
    - MARKET solo in RTH (extended=False). In pre/after: type_='limit' + extended=True.
    - Cap automatico a buying power per evitare 40310000.
    """
    if _panic():
        return {"ok": False, "detail": "panic mode active"}

    if qty is not None and notional is not None:
        raise ValueError("Pass only qty OR notional")

    # --- Cap a buying power ---
    acc = _get_account()
    bp = float(acc.get("buying_power", 0))

    if type_ == "limit" and limit_price is not None:
        px = float(limit_price)
        if notional is not None:
            notional = _cap_notional_to_bp(bp, float(notional))
        elif qty is not None:
            # riduci qty se necessario
            max_notional = _cap_notional_to_bp(bp, px * 1e12)  # numero enorme, serve solo per calcolare il cap qty
            qty_cap = _qty_from_notional(max_notional, px)
            qty = min(int(qty), int(qty_cap))
    else:
        # MARKET: se usi notional, cappalo direttamente a BP*buffer
        if notional is not None:
            notional = _cap_notional_to_bp(bp, float(notional))
        # se usi qty senza sapere il prezzo, non applichiamo cap (non abbiamo px certo)

    # --- Body ordine ---
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

    # MARKET + extended non è consentito
    if body["type"] == "market" and body.get("extended_hours"):
        raise ValueError("market orders are not allowed with extended_hours=True; use limit")

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
                         tif="gtc", extended=False, client_id=None, notional=None):
    """
    - entry_type: 'market' o 'limit' (limit richiede entry_px)
    - tp_px: take profit (limit)
    - sl_px: stop (stop-market)
    - Passa qty O notional; cap a BP applicato.
    """
    if _panic():
        return {"ok": False, "detail": "panic mode active"}

    if qty is not None and notional is not None:
        raise ValueError("Pass only qty OR notional")

    # --- Cap a buying power ---
    acc = _get_account()
    bp = float(acc.get("buying_power", 0))
    px = float(entry_px) if (entry_type == "limit" and entry_px is not None) else None

    if px is not None:
        if notional is not None:
            notional = _cap_notional_to_bp(bp, float(notional))
        elif qty is not None:
            max_notional = _cap_notional_to_bp(bp, px * 1e12)
            qty_cap = _qty_from_notional(max_notional, px)
            qty = min(int(qty), int(qty_cap))
    else:
        # MARKET bracket: consigliato notional → cappiamo a BP*buffer
        if notional is not None:
            notional = _cap_notional_to_bp(bp, float(notional))

    # --- Body ordine ---
    body = {
        "symbol": symbol,
        "side": side,
        "time_in_force": tif,
        "type": entry_type if entry_type in ("market", "limit") else "market",
        "order_class": "bracket",
        "extended_hours": bool(extended),
        "client_order_id": client_id or _client_id(symbol),
    }

    if body["type"] == "limit":
        if entry_px is None:
            raise ValueError("limit entry without entry_px")
        body["limit_price"] = round(float(entry_px), 2)

    if tp_px is not None:
        body["take_profit"] = {"limit_price": round(float(tp_px), 2)}
    if sl_px is not None:
        body["stop_loss"] = {"stop_price": round(float(sl_px), 2)}  # stop-market

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

    # MARKET + extended non è consentito
    if body["type"] == "market" and body.get("extended_hours"):
        raise ValueError("market orders are not allowed with extended_hours=True; use limit")

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
    # Cancella ordini aperti
    requests.delete(f"{ALPACA_TRADING_BASE}/v2/orders", headers=_headers(), timeout=20)
    # Chiude posizioni a market
    r = requests.get(f"{ALPACA_TRADING_BASE}/v2/positions", headers=_headers(), timeout=20)
    r.raise_for_status()
    for p in r.json():
        sym = p["symbol"]; q = abs(int(float(p["qty"])))
        side = "sell" if float(p["qty"]) > 0 else "buy"
        place_simple_equity(sym, side, qty=q, type_="market", tif="day", extended=False)
    return {"ok": True}
