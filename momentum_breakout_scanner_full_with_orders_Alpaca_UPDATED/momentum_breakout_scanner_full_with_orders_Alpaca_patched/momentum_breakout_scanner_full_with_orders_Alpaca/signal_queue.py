
import os, sqlite3, time, json

DB_PATH = os.environ.get("SIGNALS_DB_PATH", os.path.join(os.path.dirname(__file__), "signals.db"))

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS pending_signals (         id INTEGER PRIMARY KEY AUTOINCREMENT,         symbol TEXT NOT NULL,         side TEXT NOT NULL,         payload TEXT NOT NULL,         created_ts INTEGER NOT NULL,         status TEXT NOT NULL DEFAULT 'queued'     )")
    conn.commit()
    return conn

def enqueue(symbol:str, side:str, payload:dict):
    c = _conn()
    c.execute("INSERT INTO pending_signals(symbol, side, payload, created_ts, status) VALUES (?,?,?,?,?)",
              (symbol, side, json.dumps(payload), int(time.time()), "queued"))
    c.commit()
    c.close()

def fetch_due(ttl_seconds:int):
    now = int(time.time())
    c = _conn()
    rows = c.execute("SELECT id, symbol, side, payload, created_ts FROM pending_signals WHERE status='queued'").fetchall()
    out = []
    for rid, sym, side, payload, created in rows:
        if ttl_seconds <= 0 or now - int(created) <= ttl_seconds:
            out.append((rid, sym, side, json.loads(payload)))
        else:
            c.execute("UPDATE pending_signals SET status='expired' WHERE id=?", (rid,))
    c.commit()
    c.close()
    return out

def mark_done(signal_id:int, status:str="sent"):
    c = _conn()
    c.execute("UPDATE pending_signals SET status=? WHERE id=?", (status, signal_id))
    c.commit()
    c.close()
