from dataclasses import dataclass
from datetime import datetime

@dataclass
class Trade:
    ts: datetime
    symbol: str
    side: str
    px_entry: float
    px_exit: float
    qty: int
    pnl: float
    R: float

@dataclass
class Position:
    symbol: str
    side: str
    qty: int
    entry: float
