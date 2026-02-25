import logging
from collections import Counter
from typing import Optional

from sqlalchemy.orm import Session

from app.models.recommendation import ExpertRecommendation
from app.models.consensus import ConsensusDecision
from app.models.position import Position
from app.models.settings import UserSettings
from app.services.experts.value_investor import ValueInvestorExpert
from app.services.experts.momentum_trader import MomentumTraderExpert
from app.services.experts.risk_manager import RiskManagerExpert
from app.services import market_data as md

logger = logging.getLogger(__name__)

EXPERTS = {
    "value": ValueInvestorExpert(),
    "momentum": MomentumTraderExpert(),
    "risk": RiskManagerExpert(),
}

ACTION_PRIORITY = {
    "close": 6,
    "sell": 5,
    "reduce": 4,
    "hold": 3,
    "add": 2,
    "buy": 1,
}


def _get_previous_recommendation(db: Session, position_id: int, expert_type: str) -> Optional[dict]:
    rec = (
        db.query(ExpertRecommendation)
        .filter(
            ExpertRecommendation.position_id == position_id,
            ExpertRecommendation.expert_type == expert_type,
        )
        .order_by(ExpertRecommendation.created_at.desc())
        .first()
    )
    if not rec:
        return None
    return {
        "action": rec.recommendation_action,
        "target_price": float(rec.target_price) if rec.target_price else None,
        "market_snapshot": rec.market_snapshot or {},
        "created_at": rec.created_at.isoformat(),
    }


def _aggregate_consensus(votes: list[str]) -> tuple[str, str]:
    """
    Returns (aggregated_action, consensus_level).
    consensus_level: unanimous (3/3), majority (2/3), split (1/3)
    """
    counts = Counter(votes)
    top_action, top_count = counts.most_common(1)[0]

    if top_count == 3:
        return top_action, "unanimous"
    elif top_count == 2:
        return top_action, "majority"
    else:
        # Pick most cautious/conservative action
        ranked = sorted(votes, key=lambda a: ACTION_PRIORITY.get(a, 3), reverse=True)
        return ranked[0], "split"


def run_recommendations_for_position(
    db: Session,
    position: Position,
    portfolio_metrics: Optional[dict] = None,
    portfolio_sector_weights: Optional[dict] = None,
) -> ConsensusDecision:
    """
    Runs all three experts for a single position, saves recommendations,
    and returns the consensus decision.
    """
    settings_row = db.query(UserSettings).first()
    risk_profile = settings_row.risk_profile if settings_row else "balanced"

    qty = float(position.quantity)
    avg_price = float(position.average_purchase_price)

    # Fetch sector for risk manager
    fundamentals = md.get_fundamentals(position.ticker)
    sector = fundamentals.get("sector", "Unknown") if fundamentals else "Unknown"

    expert_votes = {}
    actions = []

    for expert_type, expert in EXPERTS.items():
        prev = _get_previous_recommendation(db, position.id, expert_type)
        try:
            if expert_type == "risk":
                result = expert.analyze(
                    position_id=position.id,
                    ticker=position.ticker,
                    quantity=qty,
                    avg_purchase_price=avg_price,
                    risk_profile=risk_profile,
                    portfolio_metrics=portfolio_metrics,
                    sector=sector,
                    portfolio_sector_weights=portfolio_sector_weights,
                    previous_recommendation=prev,
                )
            else:
                result = expert.analyze(
                    position_id=position.id,
                    ticker=position.ticker,
                    quantity=qty,
                    avg_purchase_price=avg_price,
                    risk_profile=risk_profile,
                    previous_recommendation=prev,
                )
        except Exception as e:
            logger.error(f"Expert {expert_type} failed for {position.ticker}: {e}")
            continue

        # Persist recommendation
        rec = ExpertRecommendation(
            position_id=position.id,
            expert_type=result.expert_type,
            recommendation_action=result.action,
            target_price=result.target_price,
            quantity_change=result.quantity_change,
            confidence_level=result.confidence_level,
            reasoning=result.reasoning,
            market_snapshot=result.market_snapshot,
        )
        db.add(rec)

        expert_votes[expert_type] = {
            "action": result.action,
            "target_price": result.target_price,
            "quantity_change": result.quantity_change,
            "confidence_level": result.confidence_level,
            "reasoning": result.reasoning,
        }
        actions.append(result.action)

    db.flush()

    # Aggregate
    if not actions:
        agg_action, consensus_level = "hold", "split"
    else:
        agg_action, consensus_level = _aggregate_consensus(actions)

    consensus = ConsensusDecision(
        position_id=position.id,
        aggregated_action=agg_action,
        consensus_level=consensus_level,
        expert_votes=expert_votes,
    )
    db.add(consensus)
    db.commit()
    db.refresh(consensus)
    return consensus


def run_all_recommendations(db: Session) -> dict:
    """Runs recommendations for all positions in portfolio."""
    positions = db.query(Position).all()
    if not positions:
        return {"updated": 0}

    # Compute portfolio metrics once
    portfolio_data = [
        {"ticker": p.ticker, "quantity": float(p.quantity), "average_purchase_price": float(p.average_purchase_price)}
        for p in positions
    ]
    try:
        portfolio_metrics = md.calculate_portfolio_metrics(portfolio_data)
    except Exception as e:
        logger.error(f"calculate_portfolio_metrics failed: {e}")
        portfolio_metrics = {}

    # Compute sector weights
    sector_map: dict[str, float] = {}
    total_val = portfolio_metrics.get("total_value", 0)
    if total_val > 0:
        weights = portfolio_metrics.get("weights", {})
        for pos in positions:
            try:
                fund = md.get_fundamentals(pos.ticker)
                sec = fund.get("sector", "Unknown") if fund else "Unknown"
                sector_map[sec] = sector_map.get(sec, 0) + weights.get(pos.ticker, 0)
            except Exception:
                pass

    updated = 0
    for position in positions:
        try:
            run_recommendations_for_position(
                db=db,
                position=position,
                portfolio_metrics=portfolio_metrics,
                portfolio_sector_weights=sector_map,
            )
            updated += 1
        except Exception as e:
            logger.error(f"Failed to run recommendations for {position.ticker}: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass

    return {"updated": updated, "total": len(positions)}


def update_track_record(db: Session) -> None:
    """
    Compares past recommendations against actual outcomes.
    Fills in actual_price_1w, _1m, _3m if the time has passed.
    """
    from datetime import datetime, timedelta
    import pytz

    now = datetime.now(tz=pytz.utc)

    recs = (
        db.query(ExpertRecommendation)
        .filter(
            (ExpertRecommendation.actual_price_1w == None) |
            (ExpertRecommendation.actual_price_1m == None) |
            (ExpertRecommendation.actual_price_3m == None)
        )
        .all()
    )

    for rec in recs:
        created = rec.created_at
        # Get current price of the position's ticker
        pos = db.query(Position).filter(Position.id == rec.position_id).first()
        if not pos:
            continue
        price_data = md.get_current_price(pos.ticker)
        if not price_data:
            continue
        current = price_data.get("current_price")
        if not current:
            continue

        age = now - created
        if age >= timedelta(weeks=1) and rec.actual_price_1w is None:
            rec.actual_price_1w = current
        if age >= timedelta(days=30) and rec.actual_price_1m is None:
            rec.actual_price_1m = current
        if age >= timedelta(days=90) and rec.actual_price_3m is None:
            rec.actual_price_3m = current

    db.commit()
