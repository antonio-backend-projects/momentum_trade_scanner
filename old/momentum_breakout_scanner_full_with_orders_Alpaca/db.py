import sqlite3, json, os
from datetime import datetime, timezone

DB_PATH = os.environ.get("DB_PATH", "state/mbs.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY,
  ts_utc TEXT,
  symbol TEXT,
  side TEXT,
  rv REAL,
  trigger TEXT,
  donch_h REAL,
  donch_l REAL,
  config TEXT
);
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY,
  client_id TEXT,
  alpaca_id TEXT,
  ts_utc TEXT,
  symbol TEXT,
  asset_class TEXT,
  side TEXT,
  qty REAL,
  type TEXT,
  order_class TEXT,
  limit_px REAL,
  stop_px REAL,
  takeprofit_px REAL,
  status TEXT,
  legs TEXT
);
CREATE TABLE IF NOT EXISTS fills (
  id INTEGER PRIMARY KEY,
  order_id TEXT,
  ts_utc TEXT,
  fill_qty REAL,
  fill_px REAL,
  leg TEXT
);
CREATE TABLE IF NOT EXISTS positions (
  symbol TEXT PRIMARY KEY,
  qty REAL,
  avg_px REAL,
  mode TEXT,
  risk_r REAL,
  state TEXT
);
"""

def _utcnow_str(): return datetime.now(timezone.utc).isoformat()

def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = connect()
    with conn:
        conn.executescript(SCHEMA_SQL)
    conn.close()

def insert_signal(symbol, side, rv, trigger, donch_h, donch_l, config_dict):
    conn = connect()
    with conn:
        conn.execute(
            """INSERT INTO signals(ts_utc, symbol, side, rv, trigger, donch_h, donch_l, config)
                VALUES (?,?,?,?,?,?,?,?)""",
            (_utcnow_str(), symbol, side, rv, trigger, donch_h, donch_l, json.dumps(config_dict or {}))
        )
    conn.close()

def insert_order(client_id, alpaca_id, symbol, asset_class, side, qty, type_, order_class, limit_px, stop_px, tp_px, status, legs=None):
    conn = connect()
    with conn:
        conn.execute(
            """INSERT INTO orders(client_id, alpaca_id, ts_utc, symbol, asset_class, side, qty, type, order_class, limit_px, stop_px, takeprofit_px, status, legs)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (client_id, alpaca_id, _utcnow_str(), symbol, asset_class, side, qty, type_, order_class, limit_px, stop_px, tp_px, status, json.dumps(legs or {}))
        )
    conn.close()

def update_order_status(alpaca_id, status, legs=None):
    conn = connect()
    with conn:
        conn.execute("UPDATE orders SET status=?, legs=? WHERE alpaca_id=?",
                     (status, json.dumps(legs or {}), alpaca_id))
    conn.close()

def insert_fill(order_id, fill_qty, fill_px, leg=None):
    conn = connect()
    with conn:
        conn.execute("INSERT INTO fills(order_id, ts_utc, fill_qty, fill_px, leg) VALUES (?,?,?,?,?)",
                     (order_id, _utcnow_str(), fill_qty, fill_px, leg))
    conn.close()
