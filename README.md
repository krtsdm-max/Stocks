# Stock Portfolio Advisor

A personal stock portfolio tracker with an intelligent recommendation engine powered by three virtual expert advisors.

## Expert Committee

| Expert | Role | Focus |
|--------|------|-------|
| **Victoria Chen** | Value Investor | P/E, P/B, dividend yield, sector comparisons, fair value |
| **Marcus Rivera** | Momentum Trader | MA crossovers, RSI, MACD, price momentum |
| **Sophie Nakamura** | Risk Manager | Concentration, correlation, drawdown, volatility |

## Features

- **Portfolio CRUD** — add, edit, delete positions with ticker validation via Yahoo Finance
- **Live Market Data** — current prices, day P&L, historical charts (yfinance)
- **Three Expert Engines** — rule-based analysis generating concrete `hold/buy/add/reduce/sell/close` recommendations with target prices and reasoning
- **Consensus Voting** — unanimous (3/3), majority (2/3), or split (1/3) with colour-coded dashboard
- **Hourly Scheduler** — auto-refresh recommendations during NYSE trading hours (9:30–16:00 EST)
- **Track Record** — direction accuracy and price target error tracked for each expert
- **Committee Chat** — ask all three experts questions; persistent context via Claude API
- **Risk Profiles** — conservative / balanced / aggressive with different concentration limits

## Quick Start

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set ANTHROPIC_API_KEY
```

### 2. Start with Docker Compose

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### 3. Development (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
# Ensure PostgreSQL and Redis are running locally
cp .env.example .env   # edit DATABASE_URL / REDIS_URL
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Frontend | React 18, TypeScript, Tailwind CSS, Recharts |
| Scheduler | APScheduler |
| Market Data | yfinance (Yahoo Finance) |
| AI Chat | Anthropic Claude API |

## API Reference

```
GET    /api/portfolio              Portfolio with live prices and latest consensus
GET    /api/positions              All positions
POST   /api/positions              Add position
PUT    /api/positions/{id}         Update position
DELETE /api/positions/{id}         Delete position
GET    /api/recommendations/{id}   Full analysis for position (experts + technicals + fundamentals)
POST   /api/recommendations/refresh/{id}  Regenerate recommendations
POST   /api/recommendations/refresh-all  Refresh all positions
POST   /api/chat                   Ask the expert committee
GET    /api/chat/history           Chat history
GET    /api/experts/{type}/track-record  Expert performance history
GET    /api/settings               Current risk settings
POST   /api/settings               Update risk profile
GET    /api/validate-ticker/{ticker}  Check ticker validity
```

## Risk Profiles

| Parameter | Conservative | Balanced | Aggressive |
|-----------|-------------|---------|-----------|
| Max position | 5% | 10% | 15% |
| Max sector | 15% | 25% | 35% |
| Volatility target | Low | Medium | High |
