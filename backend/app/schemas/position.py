from pydantic import BaseModel, field_validator
from datetime import date, datetime
from typing import Optional
from decimal import Decimal


class PositionCreate(BaseModel):
    ticker: str
    quantity: Decimal
    average_purchase_price: Decimal
    purchase_date: date
    notes: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("average_purchase_price")
    @classmethod
    def price_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class PositionUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    average_purchase_price: Optional[Decimal] = None
    purchase_date: Optional[date] = None
    notes: Optional[str] = None


class PositionResponse(BaseModel):
    id: int
    ticker: str
    quantity: Decimal
    average_purchase_price: Decimal
    purchase_date: date
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Live market data (populated at runtime)
    current_price: Optional[float] = None
    day_change: Optional[float] = None
    day_change_pct: Optional[float] = None
    total_value: Optional[float] = None
    total_pnl: Optional[float] = None
    total_pnl_pct: Optional[float] = None
    portfolio_weight: Optional[float] = None

    class Config:
        from_attributes = True
