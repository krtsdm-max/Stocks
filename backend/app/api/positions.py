from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models.position import Position
from app.schemas.position import PositionCreate, PositionUpdate, PositionResponse
from app.services import market_data as md

router = APIRouter(prefix="/api/positions", tags=["positions"])


def _enrich_position(pos: Position, total_portfolio_value: float = 0.0) -> dict:
    price_data = md.get_current_price(pos.ticker)
    current_price = price_data.get("current_price") if price_data else None
    day_change = price_data.get("day_change") if price_data else None
    day_change_pct = price_data.get("day_change_pct") if price_data else None
    qty = float(pos.quantity)
    avg_price = float(pos.average_purchase_price)
    total_value = (current_price * qty) if current_price else None
    total_pnl = ((current_price - avg_price) * qty) if current_price else None
    total_pnl_pct = ((current_price - avg_price) / avg_price * 100) if current_price and avg_price else None
    portfolio_weight = (total_value / total_portfolio_value * 100) if total_value and total_portfolio_value > 0 else None
    return {
        **{c.name: getattr(pos, c.name) for c in pos.__table__.columns},
        "current_price": current_price,
        "day_change": day_change,
        "day_change_pct": day_change_pct,
        "total_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "portfolio_weight": portfolio_weight,
    }


@router.get("", response_model=List[PositionResponse])
def list_positions(db: Session = Depends(get_db)):
    positions = db.query(Position).order_by(Position.ticker).all()
    if not positions:
        return []
    total_value = 0.0
    price_map = {}
    for pos in positions:
        pd_ = md.get_current_price(pos.ticker)
        if pd_ and pd_.get("current_price"):
            price_map[pos.ticker] = pd_["current_price"]
            total_value += pd_["current_price"] * float(pos.quantity)
    result = []
    for pos in positions:
        current = price_map.get(pos.ticker)
        qty = float(pos.quantity)
        avg = float(pos.average_purchase_price)
        tv = (current * qty) if current else None
        pd_ = md.get_current_price(pos.ticker)
        result.append(PositionResponse(
            **{c.name: getattr(pos, c.name) for c in pos.__table__.columns},
            current_price=current,
            day_change=pd_.get("day_change") if pd_ else None,
            day_change_pct=pd_.get("day_change_pct") if pd_ else None,
            total_value=tv,
            total_pnl=((current - avg) * qty) if current else None,
            total_pnl_pct=((current - avg) / avg * 100) if current and avg else None,
            portfolio_weight=(tv / total_value * 100) if tv and total_value > 0 else None,
        ))
    return result


@router.post("", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
def create_position(data: PositionCreate, db: Session = Depends(get_db)):
    if not md.validate_ticker(data.ticker):
        raise HTTPException(status_code=400, detail=f"Ticker '{data.ticker}' does not appear to be a valid stock symbol.")
    pos = Position(
        ticker=data.ticker,
        quantity=data.quantity,
        average_purchase_price=data.average_purchase_price,
        purchase_date=data.purchase_date,
        notes=data.notes,
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return PositionResponse(**{c.name: getattr(pos, c.name) for c in pos.__table__.columns})


@router.put("/{position_id}", response_model=PositionResponse)
def update_position(position_id: int, data: PositionUpdate, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pos, field, value)
    db.commit()
    db.refresh(pos)
    return PositionResponse(**{c.name: getattr(pos, c.name) for c in pos.__table__.columns})


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(position_id: int, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    db.delete(pos)
    db.commit()


class SellRequest(BaseModel):
    quantity: float


@router.post("/{ticker}/sell")
def sell_position(ticker: str, data: SellRequest, db: Session = Depends(get_db)):
    """FIFO sell: reduces quantities starting from the oldest purchase date."""
    positions = (
        db.query(Position)
        .filter(Position.ticker == ticker.upper())
        .order_by(Position.purchase_date)
        .all()
    )
    if not positions:
        raise HTTPException(status_code=404, detail=f"No positions found for {ticker.upper()}")
    total_qty = sum(float(p.quantity) for p in positions)
    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    if data.quantity > total_qty + 1e-9:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot sell {data.quantity} shares, only {total_qty:.4f} available",
        )
    remaining = data.quantity
    for pos in positions:
        qty = float(pos.quantity)
        if remaining >= qty - 1e-9:
            db.delete(pos)
            remaining -= qty
        else:
            pos.quantity = round(qty - remaining, 6)
            remaining = 0.0
            break
    db.commit()
    return {
        "sold": data.quantity,
        "ticker": ticker.upper(),
        "remaining": round(max(total_qty - data.quantity, 0), 6),
    }
