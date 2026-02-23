from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import pytz

from app.database import get_db
from app.models.position import Position
from app.models.recommendation import ExpertRecommendation
from app.models.consensus import ConsensusDecision
from app.services import market_data as md

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

EST = pytz.timezone("America/New_York")


def _is_market_open() -> bool:
    now_est = datetime.now(tz=EST)
    if now_est.weekday() >= 5:
        return False
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now_est <= market_close


@router.get("")
def get_portfolio(db: Session = Depends(get_db)):
    positions = db.query(Position).order_by(Position.ticker).all()

    total_value = 0.0
    total_cost = 0.0
    total_day_pnl = 0.0
    positions_data = []

    for pos in positions:
        price_data = md.get_current_price(pos.ticker)
        qty = float(pos.quantity)
        avg = float(pos.average_purchase_price)
        current = price_data.get("current_price") if price_data else None
        prev_close = price_data.get("previous_close") if price_data else None

        pos_value = (current * qty) if current else (avg * qty)
        cost_basis = avg * qty
        total_value += pos_value
        total_cost += cost_basis
        if current and prev_close:
            total_day_pnl += (current - prev_close) * qty

        # Latest consensus
        latest_consensus = (
            db.query(ConsensusDecision)
            .filter(ConsensusDecision.position_id == pos.id)
            .order_by(ConsensusDecision.timestamp.desc())
            .first()
        )

        positions_data.append({
            "id": pos.id,
            "ticker": pos.ticker,
            "quantity": qty,
            "average_purchase_price": avg,
            "purchase_date": pos.purchase_date.isoformat(),
            "notes": pos.notes,
            "current_price": current,
            "day_change": price_data.get("day_change") if price_data else None,
            "day_change_pct": price_data.get("day_change_pct") if price_data else None,
            "total_value": pos_value,
            "total_pnl": pos_value - cost_basis,
            "total_pnl_pct": ((pos_value - cost_basis) / cost_basis * 100) if cost_basis > 0 else 0,
            "portfolio_weight": None,  # filled below
            "latest_consensus": {
                "aggregated_action": latest_consensus.aggregated_action,
                "consensus_level": latest_consensus.consensus_level,
                "expert_votes": latest_consensus.expert_votes,
                "timestamp": latest_consensus.timestamp.isoformat(),
            } if latest_consensus else None,
        })

    # Calculate weights
    for p in positions_data:
        p["portfolio_weight"] = (p["total_value"] / total_value * 100) if total_value > 0 else 0

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    total_day_pnl_pct = (total_day_pnl / (total_value - total_day_pnl) * 100) if (total_value - total_day_pnl) > 0 else 0

    return {
        "nav": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "day_pnl": round(total_day_pnl, 2),
        "day_pnl_pct": round(total_day_pnl_pct, 2),
        "positions_count": len(positions),
        "market_open": _is_market_open(),
        "last_updated": datetime.utcnow().isoformat(),
        "positions": positions_data,
    }


@router.get("/chart/{ticker}")
def get_position_chart(ticker: str, period: str = "1y"):
    """Returns OHLCV data for charting a specific position."""
    valid_periods = {"1w": "5d", "1m": "1mo", "3m": "3mo", "1y": "1y"}
    yf_period = valid_periods.get(period, "1y")
    data = md.get_ohlcv_for_chart(ticker.upper(), period=yf_period)
    return {"ticker": ticker.upper(), "period": period, "data": data}
