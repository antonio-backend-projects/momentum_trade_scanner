from sqlalchemy import Column, Integer, String, JSON, DateTime, func, Text
from .database import Base

class TradeLog(Base):
    __tablename__ = "trade_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(50), index=True)    # e.g., 'PLACE_ORDER', 'CLOSE_POSITION'
    request = Column(JSON)                     # json payload sent
    response = Column(JSON)                    # json response (or error)
    status = Column(String(20), default="OK")  # OK/ERROR
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())