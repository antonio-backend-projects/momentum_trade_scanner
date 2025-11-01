import os
import httpx
from typing import Dict, Any

DATA_BASE = os.getenv("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets")

def get_base_url():
    env = os.getenv("ALPACA_ENV", "paper").lower()
    if env == "live":
        return os.getenv("ALPACA_LIVE_BASE_URL", "https://api.alpaca.markets")
    return os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

def get_headers():
    key_id = os.getenv("ALPACA_API_KEY_ID")
    secret = os.getenv("ALPACA_API_SECRET")
    if not key_id or not secret:
        raise RuntimeError("Missing ALPACA_API_KEY_ID / ALPACA_API_SECRET")
    return {
        "APCA-API-KEY-ID": key_id,
        "APCA-API-SECRET-KEY": secret,
        "Content-Type": "application/json"
    }

async def list_assets(query: str|None = None):
    url = f"{get_base_url()}/v2/assets"
    params = {"status": "active", "asset_class": "us_equity"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=get_headers(), params=params)
        resp.raise_for_status()
        assets = resp.json()
        if query:
            q = query.upper()
            assets = [a for a in assets if q in a.get("symbol","").upper() or q in (a.get("name") or "").upper()]
        return assets

async def list_positions():
    url = f"{get_base_url()}/v2/positions"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=get_headers())
        resp.raise_for_status()
        return resp.json()

async def list_orders():
    url = f"{get_base_url()}/v2/orders"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=get_headers(), params={"status":"all","limit":50,"nested":True})
        resp.raise_for_status()
        return resp.json()

async def place_bracket_order(payload: Dict[str, Any]):
    url = f"{get_base_url()}/v2/orders"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=get_headers(), json=payload)
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        return resp.status_code, body

async def close_position(symbol: str):
    url = f"{get_base_url()}/v2/positions/{symbol}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(url, headers=get_headers(), params={"cancel_orders": True})
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        return resp.status_code, body

async def get_bars(symbol: str, timeframe: str = "1Day", limit: int = 100, start: str|None=None, end: str|None=None):
    # Alpaca Market Data v2 endpoint
    url = f"{DATA_BASE}/v2/stocks/{symbol}/bars"
    params = {"timeframe": timeframe, "limit": limit}
    if start: params["start"] = start
    if end: params["end"] = end
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=get_headers(), params=params)
        resp.raise_for_status()
        return resp.json()


async def get_account():
    url = f"{get_base_url()}/v2/account"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=get_headers())
        resp.raise_for_status()
        return resp.json()

async def get_clock():
    url = f"{get_base_url()}/v2/clock"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=get_headers())
        resp.raise_for_status()
        return resp.json()

async def latest_trade(symbol: str):
    url = f"{DATA_BASE}/v2/stocks/{symbol}/trades/latest"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=get_headers())
        resp.raise_for_status()
        return resp.json()

async def latest_quote(symbol: str):
    url = f"{DATA_BASE}/v2/stocks/{symbol}/quotes/latest"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=get_headers())
        resp.raise_for_status()
        return resp.json()
