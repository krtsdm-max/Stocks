from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cash import CashBalance

router = APIRouter(prefix="/api/cash", tags=["cash"])


def _get_or_create(db: Session) -> CashBalance:
    cash = db.query(CashBalance).first()
    if not cash:
        cash = CashBalance(amount=Decimal("0"))
        db.add(cash)
        db.commit()
        db.refresh(cash)
    return cash


class CashUpdate(BaseModel):
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Cash amount cannot be negative")
        return v


def _serialize(cash: CashBalance) -> dict:
    return {
        "amount": float(cash.amount),
        "updated_at": cash.updated_at.isoformat() if cash.updated_at else None,
    }


@router.get("")
def get_cash(db: Session = Depends(get_db)):
    return _serialize(_get_or_create(db))


@router.patch("")
def update_cash(data: CashUpdate, db: Session = Depends(get_db)):
    cash = _get_or_create(db)
    cash.amount = data.amount
    db.commit()
    db.refresh(cash)
    return _serialize(cash)
