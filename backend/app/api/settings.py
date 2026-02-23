from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.settings import UserSettings
from app.schemas.settings import SettingsUpdate, SettingsResponse, RISK_PROFILES

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_or_create_settings(db: Session) -> UserSettings:
    settings = db.query(UserSettings).first()
    if not settings:
        settings = UserSettings(
            risk_profile="balanced",
            max_position_concentration=10.0,
            sector_concentration_limit=25.0,
            target_volatility="medium",
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    return _get_or_create_settings(db)


@router.post("", response_model=SettingsResponse)
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    settings_row = _get_or_create_settings(db)
    profile = data.risk_profile
    profile_defaults = RISK_PROFILES[profile]

    settings_row.risk_profile = profile
    settings_row.max_position_concentration = profile_defaults["max_position_concentration"]
    settings_row.sector_concentration_limit = profile_defaults["sector_concentration_limit"]
    settings_row.target_volatility = profile_defaults["target_volatility"]

    db.commit()
    db.refresh(settings_row)
    return settings_row
