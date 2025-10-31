import os, requests
ALP_ENV = os.environ.get("ALPACA_ENV","paper")
ALPACA_TRADING_BASE = "https://paper-api.alpaca.markets" if ALP_ENV=="paper" else "https://api.alpaca.markets"

def _headers():
    return {
        "APCA-API-KEY-ID": os.environ.get("ALPACA_API_KEY",""),
        "APCA-API-SECRET-KEY": os.environ.get("ALPACA_API_SECRET","")
    }

def buy_call(option_symbol, qty=1, limit_px=None, tif="gtc"):
    body = {"symbol": option_symbol, "asset_class": "option", "side": "buy", "type": ("limit" if limit_px else "market"), "qty": str(qty), "time_in_force": tif}
    if limit_px: body["limit_price"] = float(limit_px)
    r = requests.post(f"{ALPACA_TRADING_BASE}/v2/orders", json=body, headers=_headers(), timeout=15)
    r.raise_for_status(); return r.json()
