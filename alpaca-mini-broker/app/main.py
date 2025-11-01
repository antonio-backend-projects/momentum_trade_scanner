import os
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import TradeLog
from . import alpaca_client
from .schemas import OrderIn, ClosePositionIn

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title=os.getenv("APP_TITLE", "Alpaca Mini Broker"))

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# healthcheck
@app.get("/health")
async def health():
    return {"status": "ok"}

# ---- Pages ----
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/assets", response_class=HTMLResponse)
async def assets_page(request: Request):
    return templates.TemplateResponse("assets.html", {"request": request, "assets": []})

@app.get("/positions", response_class=HTMLResponse)
async def positions_page(request: Request):
    return templates.TemplateResponse("positions.html", {"request": request, "positions": []})

@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    return templates.TemplateResponse("orders.html", {"request": request, "orders": []})

# ---- API ----
@app.get("/api/assets")
async def api_assets(query: str | None = None, limit: int = 2000):
    try:
        assets = await alpaca_client.list_assets(query=query)
        if isinstance(assets, list) and limit:
            assets = assets[:max(1, min(limit, len(assets)))]
        return assets
    except Exception as e:
        raise HTTPException(502, f"Errore fetch assets: {e}")

@app.get("/api/account")
async def api_account():
    try:
        return await alpaca_client.get_account()
    except Exception as e:
        raise HTTPException(502, f"Errore account: {e}")

@app.get("/api/clock")
async def api_clock():
    try:
        return await alpaca_client.get_clock()
    except Exception as e:
        raise HTTPException(502, f"Errore clock: {e}")

@app.get("/api/positions")
async def api_positions():
    return await alpaca_client.list_positions()

@app.get("/api/orders")
async def api_orders():
    return await alpaca_client.list_orders()

@app.get("/api/bars")
async def api_bars(symbol: str, timeframe: str = "1Day", limit: int = 100, start: str | None = None, end: str | None = None):
    if not symbol:
        raise HTTPException(400, "symbol richiesto")
    return await alpaca_client.get_bars(symbol.upper(), timeframe=timeframe, limit=limit, start=start, end=end)

@app.get("/api/quote")
async def api_quote(symbol: str):
    if not symbol:
        raise HTTPException(400, "symbol richiesto")
    sym = symbol.upper()
    try:
        trade = await alpaca_client.latest_trade(sym)
    except Exception as e:
        trade = {"error": str(e)}
    try:
        quote = await alpaca_client.latest_quote(sym)
    except Exception as e:
        quote = {"error": str(e)}
    return {"symbol": sym, "trade": trade, "quote": quote}

@app.post("/api/order")
async def api_order(order: OrderIn, db: Session = Depends(get_db)):
    # raw input log
    # store raw request
    prelog = TradeLog(action="ORDER_INPUT", request=order.model_dump(), response=None, status="OK")
    db.add(prelog); db.commit()

    payload = {
        "symbol": order.symbol.upper(),
        "side": order.side,
        "type": order.type,
        "qty": order.qty,
        "time_in_force": order.time_in_force,
        "extended_hours": bool(order.extended_hours or False),
    }
    if order.type == "limit":
        if order.limit_price is None:
            raise HTTPException(400, "limit_price obbligatorio per ordini limit")
        payload["limit_price"] = str(order.limit_price)

    # Bracket legs if provided
    if order.tp_price is not None or order.sl_price is not None:
        payload["order_class"] = "bracket"
        if order.tp_price is not None:
            payload["take_profit"] = {"limit_price": str(order.tp_price)}
        if order.sl_price is not None:
            payload["stop_loss"] = {"stop_price": str(order.sl_price)}

    status_code, body = await alpaca_client.place_bracket_order(payload)

    # Log
    log = TradeLog(
        action="PLACE_ORDER",
        request=payload,
        response=body,
        status="OK" if 200 <= status_code < 300 else "ERROR",
        error=None if 200 <= status_code < 300 else str(body),
    )
    db.add(log); db.commit()

    if 200 <= status_code < 300:
        return body
    raise HTTPException(status_code, detail=body)

@app.post("/api/close_position")
async def api_close_position(data: ClosePositionIn, db: Session = Depends(get_db)):
    status_code, body = await alpaca_client.close_position(data.symbol.upper())
    log = TradeLog(
        action="CLOSE_POSITION",
        request={"symbol": data.symbol.upper()},
        response=body,
        status="OK" if 200 <= status_code < 300 else "ERROR",
        error=None if 200 <= status_code < 300 else str(body),
    )
    db.add(log); db.commit()

    if 200 <= status_code < 300:
        return body
    raise HTTPException(status_code, detail=body)

@app.get("/api/logs")
def api_logs(db: Session = Depends(get_db)):
    logs = db.query(TradeLog).order_by(TradeLog.id.desc()).limit(200).all()
    def to_dict(row):
        return {
            "id": row.id,
            "action": row.action,
            "status": row.status,
            "created_at": str(row.created_at),
            "request": row.request,
            "response": row.response,
            "error": row.error,
        }
    return [to_dict(l) for l in logs]

from fastapi import Body

@app.post("/api/client-log")
async def api_client_log(payload: dict = Body(...), db: Session = Depends(get_db)):
    try:
        log = TradeLog(action="CLIENT_LOG", request=payload, response=None, status="OK")
        db.add(log); db.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"log error: {e}")

@app.get("/api/ping")
async def api_ping():
    return {"pong": True}
