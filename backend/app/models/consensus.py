from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from app.database import Base


class ConsensusDecision(Base):
    __tablename__ = "consensus_decisions"

    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False, index=True)
    aggregated_action = Column(String(20), nullable=False)
    consensus_level = Column(String(20), nullable=False)  # unanimous, majority, split
    expert_votes = Column(JSON, nullable=False)  # {value: {...}, momentum: {...}, risk: {...}}
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
