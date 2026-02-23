from pydantic import BaseModel, field_validator
from typing import Optional
from decimal import Decimal


RISK_PROFILES = {
    "conservative": {
        "max_position_concentration": Decimal("5.0"),
        "sector_concentration_limit": Decimal("15.0"),
        "target_volatility": "low",
    },
    "balanced": {
        "max_position_concentration": Decimal("10.0"),
        "sector_concentration_limit": Decimal("25.0"),
        "target_volatility": "medium",
    },
    "aggressive": {
        "max_position_concentration": Decimal("15.0"),
        "sector_concentration_limit": Decimal("35.0"),
        "target_volatility": "high",
    },
}


class SettingsUpdate(BaseModel):
    risk_profile: str

    @field_validator("risk_profile")
    @classmethod
    def valid_profile(cls, v: str) -> str:
        if v not in RISK_PROFILES:
            raise ValueError(f"risk_profile must be one of {list(RISK_PROFILES.keys())}")
        return v


class SettingsResponse(BaseModel):
    id: int
    risk_profile: str
    max_position_concentration: Decimal
    sector_concentration_limit: Decimal
    target_volatility: str

    class Config:
        from_attributes = True
