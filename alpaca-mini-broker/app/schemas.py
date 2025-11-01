from pydantic import BaseModel, Field
from typing import Optional, Literal

class OrderIn(BaseModel):
    extended_hours: bool | None = False
    symbol: str
    side: Literal["buy", "sell"]
    qty: float = Field(gt=0)
    type: Literal["market", "limit"] = "market"
    time_in_force: Literal["day","gtc","opg","cls","ioc","fok"] = "gtc"
    limit_price: Optional[float] = None

    # Absolute prices for bracket legs
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None

class ClosePositionIn(BaseModel):
    symbol: str