import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.api import positions, portfolio, recommendations, chat, experts, settings as settings_api, cash as cash_api
from app.scheduler.jobs import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_tables():
    from app.models import Position, ExpertRecommendation, ConsensusDecision, ChatMessage, UserSettings, CashBalance  # noqa
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Stock Portfolio Advisor API",
    description="Intelligent portfolio management with three expert recommendation engines",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(positions.router)
app.include_router(portfolio.router)
app.include_router(recommendations.router)
app.include_router(chat.router)
app.include_router(experts.router)
app.include_router(settings_api.router)
app.include_router(cash_api.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/validate-ticker/{ticker}")
def validate_ticker_endpoint(ticker: str):
    from app.services.market_data import lookup_ticker
    info = lookup_ticker(ticker.upper())
    # valid: True = confirmed, False = not found, None = network unavailable
    return {
        "ticker": ticker.upper(),
        "valid": info["valid"],   # null in JSON when network unavailable
        "name": info.get("name"),
        "price": info.get("price"),
        "exchange": info.get("exchange"),
    }
