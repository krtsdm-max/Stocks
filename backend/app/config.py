from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://stocks_user:stocks_pass@localhost:5432/stocks_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Market data cache TTL (seconds)
    PRICE_CACHE_TTL: int = 300        # 5 min for current prices
    HISTORY_CACHE_TTL: int = 3600     # 1 hour for historical data
    FUNDAMENTALS_CACHE_TTL: int = 7200  # 2 hours for fundamentals

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
