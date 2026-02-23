from sqlalchemy import Column, Integer, String, Numeric, DateTime, func
from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    risk_profile = Column(String(20), nullable=False, default="balanced")  # conservative/balanced/aggressive
    max_position_concentration = Column(Numeric(5, 2), nullable=False, default=10.0)
    sector_concentration_limit = Column(Numeric(5, 2), nullable=False, default=25.0)
    target_volatility = Column(String(20), nullable=False, default="medium")  # low/medium/high
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
