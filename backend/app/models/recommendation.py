from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, JSON, func, Text
from app.database import Base


class ExpertRecommendation(Base):
    __tablename__ = "expert_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False, index=True)
    expert_type = Column(String(20), nullable=False)  # value, momentum, risk
    recommendation_action = Column(String(20), nullable=False)  # hold/buy/add/reduce/sell/close
    target_price = Column(Numeric(18, 4), nullable=True)
    quantity_change = Column(Numeric(18, 6), nullable=True)
    confidence_level = Column(Integer, nullable=False)  # 0-100
    reasoning = Column(Text, nullable=False)
    market_snapshot = Column(JSON, nullable=False)  # full market data at time of recommendation
    # Track record fields (filled in later)
    actual_price_1w = Column(Numeric(18, 4), nullable=True)
    actual_price_1m = Column(Numeric(18, 4), nullable=True)
    actual_price_3m = Column(Numeric(18, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
