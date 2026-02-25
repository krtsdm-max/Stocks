from sqlalchemy import Column, Integer, Numeric, DateTime, func
from app.database import Base


class CashBalance(Base):
    __tablename__ = "cash_balance"

    id = Column(Integer, primary_key=True)
    amount = Column(Numeric(18, 2), nullable=False, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
