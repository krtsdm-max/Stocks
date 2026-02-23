from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, func
from app.database import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    quantity = Column(Numeric(18, 6), nullable=False)
    average_purchase_price = Column(Numeric(18, 4), nullable=False)
    purchase_date = Column(Date, nullable=False)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
