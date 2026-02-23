from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.recommendation import ExpertRecommendation
from app.models.position import Position
from app.services.chat_service import EXPERT_PERSONAS

router = APIRouter(prefix="/api/experts", tags=["experts"])


def _compute_track_record(recs: list) -> dict:
    """Compute track record accuracy metrics."""
    total = len(recs)
    direction_correct = 0
    price_errors_1w = []
    price_errors_1m = []
    price_errors_3m = []

    for rec in recs:
        snap_price = rec.market_snapshot.get("price") if rec.market_snapshot else None
        target = float(rec.target_price) if rec.target_price else None
        action = rec.recommendation_action

        # 1-week direction accuracy
        if snap_price and rec.actual_price_1w:
            actual = float(rec.actual_price_1w)
            price_moved_up = actual > snap_price
            recommended_buy = action in ("buy", "add", "hold")
            recommended_sell = action in ("sell", "reduce", "close")
            if (recommended_buy and price_moved_up) or (recommended_sell and not price_moved_up):
                direction_correct += 1

            if target:
                error_pct = abs(target - actual) / snap_price * 100
                price_errors_1w.append(error_pct)

        if snap_price and rec.actual_price_1m:
            actual = float(rec.actual_price_1m)
            if target:
                price_errors_1m.append(abs(target - actual) / snap_price * 100)

        if snap_price and rec.actual_price_3m:
            actual = float(rec.actual_price_3m)
            if target:
                price_errors_3m.append(abs(target - actual) / snap_price * 100)

    evaluated = len([r for r in recs if r.actual_price_1w is not None])

    return {
        "total_recommendations": total,
        "evaluated_1w": evaluated,
        "direction_accuracy_pct": round(direction_correct / evaluated * 100, 1) if evaluated > 0 else None,
        "avg_price_error_1w_pct": round(sum(price_errors_1w) / len(price_errors_1w), 1) if price_errors_1w else None,
        "avg_price_error_1m_pct": round(sum(price_errors_1m) / len(price_errors_1m), 1) if price_errors_1m else None,
        "avg_price_error_3m_pct": round(sum(price_errors_3m) / len(price_errors_3m), 1) if price_errors_3m else None,
    }


@router.get("/{expert_type}/track-record")
def get_expert_track_record(expert_type: str, db: Session = Depends(get_db)):
    if expert_type not in ("value", "momentum", "risk"):
        return {"error": "Unknown expert type"}

    persona = EXPERT_PERSONAS.get(expert_type, {})
    recs = (
        db.query(ExpertRecommendation)
        .filter(ExpertRecommendation.expert_type == expert_type)
        .order_by(ExpertRecommendation.created_at.desc())
        .limit(200)
        .all()
    )

    track_record = _compute_track_record(recs)

    # Action distribution
    action_dist = {}
    for rec in recs:
        action_dist[rec.recommendation_action] = action_dist.get(rec.recommendation_action, 0) + 1

    # Recent recommendations (last 10)
    recent = []
    for rec in recs[:10]:
        pos = db.query(Position).filter(Position.id == rec.position_id).first()
        recent.append({
            "id": rec.id,
            "ticker": pos.ticker if pos else "?",
            "action": rec.recommendation_action,
            "target_price": float(rec.target_price) if rec.target_price else None,
            "confidence_level": rec.confidence_level,
            "reasoning": rec.reasoning[:200],
            "created_at": rec.created_at.isoformat(),
            "actual_price_1w": float(rec.actual_price_1w) if rec.actual_price_1w else None,
            "actual_price_1m": float(rec.actual_price_1m) if rec.actual_price_1m else None,
        })

    return {
        "expert_type": expert_type,
        "expert_name": persona.get("name", expert_type),
        "expert_title": persona.get("title", ""),
        "philosophy": persona.get("philosophy", ""),
        "track_record": track_record,
        "action_distribution": action_dist,
        "recent_recommendations": recent,
    }
