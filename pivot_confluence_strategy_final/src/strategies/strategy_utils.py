from dataclasses import dataclass

@dataclass
class Position:
    symbol: str
    side: str
    qty: int
    avg_px: float

@dataclass
class Trade:
    ts: object
    symbol: str
    side: str
    px_entry: float
    px_exit: float
    qty: int
    pnl: float
    R: float
