from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.position import Position
from app.models.recommendation import ExpertRecommendation
from app.models.consensus import ConsensusDecision
from app.services.recommendation_engine import run_recommendations_for_position, run_all_recommendations
from app.services import market_data as md

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/{position_id}")
def get_position_recommendations(position_id: int, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")

    # Latest consensus
    consensus = (
        db.query(ConsensusDecision)
        .filter(ConsensusDecision.position_id == position_id)
        .order_by(ConsensusDecision.timestamp.desc())
        .first()
    )

    # Latest per-expert recommendations
    recs = {}
    for expert_type in ("value", "momentum", "risk"):
        rec = (
            db.query(ExpertRecommendation)
            .filter(
                ExpertRecommendation.position_id == position_id,
                ExpertRecommendation.expert_type == expert_type,
            )
            .order_by(ExpertRecommendation.created_at.desc())
            .first()
        )
        if rec:
            recs[expert_type] = {
                "id": rec.id,
                "action": rec.recommendation_action,
                "target_price": float(rec.target_price) if rec.target_price else None,
                "quantity_change": float(rec.quantity_change) if rec.quantity_change else None,
                "confidence_level": rec.confidence_level,
                "reasoning": rec.reasoning,
                "market_snapshot": rec.market_snapshot,
                "created_at": rec.created_at.isoformat(),
            }

    # History (last 20 per expert)
    history = (
        db.query(ExpertRecommendation)
        .filter(ExpertRecommendation.position_id == position_id)
        .order_by(ExpertRecommendation.created_at.desc())
        .limit(30)
        .all()
    )

    # Fundamentals + technicals for the card
    fundamentals = md.get_fundamentals(pos.ticker)
    technicals = md.calculate_technical_indicators(pos.ticker)

    return {
        "position_id": position_id,
        "ticker": pos.ticker,
        "consensus": {
            "aggregated_action": consensus.aggregated_action,
            "consensus_level": consensus.consensus_level,
            "expert_votes": consensus.expert_votes,
            "timestamp": consensus.timestamp.isoformat(),
        } if consensus else None,
        "expert_recommendations": recs,
        "history": [
            {
                "id": r.id,
                "expert_type": r.expert_type,
                "action": r.recommendation_action,
                "target_price": float(r.target_price) if r.target_price else None,
                "confidence_level": r.confidence_level,
                "reasoning": r.reasoning,
                "actual_price_1w": float(r.actual_price_1w) if r.actual_price_1w else None,
                "actual_price_1m": float(r.actual_price_1m) if r.actual_price_1m else None,
                "actual_price_3m": float(r.actual_price_3m) if r.actual_price_3m else None,
                "created_at": r.created_at.isoformat(),
                "snapshot_price": r.market_snapshot.get("price") if r.market_snapshot else None,
            }
            for r in history
        ],
        "fundamentals": fundamentals,
        "technicals": technicals,
    }


@router.post("/refresh/{position_id}")
def refresh_position_recommendations(
    position_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")

    # Run synchronously (can be moved to background for production)
    portfolio_data = [
        {"ticker": p.ticker, "quantity": float(p.quantity), "average_purchase_price": float(p.average_purchase_price)}
        for p in db.query(Position).all()
    ]
    portfolio_metrics = md.calculate_portfolio_metrics(portfolio_data)
    consensus = run_recommendations_for_position(db, pos, portfolio_metrics=portfolio_metrics)

    return {
        "status": "refreshed",
        "position_id": position_id,
        "consensus_action": consensus.aggregated_action,
        "consensus_level": consensus.consensus_level,
    }


@router.post("/refresh-all")
def refresh_all_recommendations(db: Session = Depends(get_db)):
    result = run_all_recommendations(db)
    return {"status": "completed", **result}
