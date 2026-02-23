from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any
from decimal import Decimal


class ExpertVote(BaseModel):
    expert_type: str
    action: str
    target_price: Optional[float]
    quantity_change: Optional[float]
    confidence_level: int
    reasoning: str


class RecommendationResponse(BaseModel):
    id: int
    position_id: int
    expert_type: str
    recommendation_action: str
    target_price: Optional[Decimal]
    quantity_change: Optional[Decimal]
    confidence_level: int
    reasoning: str
    market_snapshot: dict
    created_at: datetime

    # Track record
    actual_price_1w: Optional[Decimal] = None
    actual_price_1m: Optional[Decimal] = None
    actual_price_3m: Optional[Decimal] = None

    class Config:
        from_attributes = True


class ConsensusResponse(BaseModel):
    id: int
    position_id: int
    aggregated_action: str
    consensus_level: str
    expert_votes: dict
    timestamp: datetime

    class Config:
        from_attributes = True


class PortfolioPositionDetail(BaseModel):
    position_id: int
    ticker: str
    current_price: Optional[float]
    day_change: Optional[float]
    day_change_pct: Optional[float]
    total_value: Optional[float]
    total_pnl: Optional[float]
    total_pnl_pct: Optional[float]
    portfolio_weight: Optional[float]
    quantity: float
    average_purchase_price: float
    latest_consensus: Optional[ConsensusResponse]
    latest_recommendations: list[RecommendationResponse]
