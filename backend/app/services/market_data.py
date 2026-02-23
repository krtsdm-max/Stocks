import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import redis
import yfinance as yf
from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def _cache_key(prefix: str, ticker: str) -> str:
    return f"market:{prefix}:{ticker.upper()}"


def _cache_get(key: str) -> Optional[dict]:
    try:
        r = get_redis()
        raw = r.get(key)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
    return None


def _cache_set(key: str, data: dict, ttl: int) -> None:
    try:
        r = get_redis()
        r.setex(key, ttl, json.dumps(data, default=str))
    except Exception as e:
        logger.warning(f"Redis set error: {e}")


def get_current_price(ticker: str) -> Optional[dict]:
    """Returns current price + day change for a ticker."""
    key = _cache_key("price", ticker)
    cached = _cache_get(key)
    if cached:
        return cached

    try:
        tk = yf.Ticker(ticker)
        info = tk.fast_info
        data = {
            "ticker": ticker,
            "current_price": float(info.last_price) if info.last_price else None,
            "previous_close": float(info.previous_close) if info.previous_close else None,
            "day_change": None,
            "day_change_pct": None,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if data["current_price"] and data["previous_close"]:
            data["day_change"] = data["current_price"] - data["previous_close"]
            data["day_change_pct"] = (data["day_change"] / data["previous_close"]) * 100
        _cache_set(key, data, settings.PRICE_CACHE_TTL)
        return data
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        return None


def get_historical_data(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """Returns OHLCV historical data as DataFrame."""
    key = _cache_key(f"history_{period}", ticker)
    cached = _cache_get(key)
    if cached:
        df = pd.DataFrame(cached["data"])
        df.index = pd.to_datetime(df.index)
        return df

    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period=period)
        if df.empty:
            return None
        serialized = {"data": df.to_dict()}
        _cache_set(key, serialized, settings.HISTORY_CACHE_TTL)
        return df
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}")
        return None


def get_fundamentals(ticker: str) -> Optional[dict]:
    """Returns fundamental metrics (P/E, P/B, dividend yield, sector, etc.)."""
    key = _cache_key("fundamentals", ticker)
    cached = _cache_get(key)
    if cached:
        return cached

    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        def safe_float(val):
            try:
                if val is None:
                    return None
                f = float(val)
                return f if not (f != f) else None  # filter NaN
            except Exception:
                return None

        data = {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName", ticker),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "market_cap": safe_float(info.get("marketCap")),
            "pe_ratio": safe_float(info.get("trailingPE")),
            "forward_pe": safe_float(info.get("forwardPE")),
            "pb_ratio": safe_float(info.get("priceToBook")),
            "ps_ratio": safe_float(info.get("priceToSalesTrailing12Months")),
            "ev_ebitda": safe_float(info.get("enterpriseToEbitda")),
            "dividend_yield": safe_float(info.get("dividendYield")),
            "beta": safe_float(info.get("beta")),
            "52w_high": safe_float(info.get("fiftyTwoWeekHigh")),
            "52w_low": safe_float(info.get("fiftyTwoWeekLow")),
            "avg_volume": safe_float(info.get("averageVolume")),
            "current_price": safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        }
        _cache_set(key, data, settings.FUNDAMENTALS_CACHE_TTL)
        return data
    except Exception as e:
        logger.error(f"Error fetching fundamentals for {ticker}: {e}")
        return None


def calculate_technical_indicators(ticker: str) -> Optional[dict]:
    """Calculates RSI, MACD, moving averages, momentum from historical data."""
    df = get_historical_data(ticker, period="1y")
    if df is None or len(df) < 50:
        return None

    close = df["Close"]

    # Moving averages
    ma50 = float(close.rolling(50).mean().iloc[-1])
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else None
    current = float(close.iloc[-1])

    # RSI (14-period)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = float((100 - 100 / (1 + rs)).iloc[-1])

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_histogram = macd_line - signal_line

    # Price momentum
    price_3m_ago = float(close.iloc[-63]) if len(df) >= 63 else None
    price_6m_ago = float(close.iloc[-126]) if len(df) >= 126 else None
    momentum_3m = ((current - price_3m_ago) / price_3m_ago * 100) if price_3m_ago else None
    momentum_6m = ((current - price_6m_ago) / price_6m_ago * 100) if price_6m_ago else None

    # Volume trend (compare last 20 days avg vs prior 20 days avg)
    vol_recent = float(df["Volume"].iloc[-20:].mean())
    vol_prior = float(df["Volume"].iloc[-40:-20].mean()) if len(df) >= 40 else vol_recent
    volume_trend = (vol_recent - vol_prior) / vol_prior * 100

    # Volatility (annualised)
    returns = close.pct_change().dropna()
    volatility_annual = float(returns.std() * np.sqrt(252) * 100)

    # Support / resistance (52w high/low)
    high_52w = float(close.iloc[-252:].max()) if len(df) >= 252 else float(close.max())
    low_52w = float(close.iloc[-252:].min()) if len(df) >= 252 else float(close.min())

    return {
        "ticker": ticker,
        "current_price": current,
        "ma50": ma50,
        "ma200": ma200,
        "above_ma50": current > ma50,
        "above_ma200": current > ma200 if ma200 else None,
        "golden_cross": (ma50 > ma200) if ma200 else None,  # MA50 > MA200
        "rsi": round(rsi, 2),
        "rsi_signal": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
        "macd_line": float(macd_line.iloc[-1]),
        "macd_signal": float(signal_line.iloc[-1]),
        "macd_histogram": float(macd_histogram.iloc[-1]),
        "macd_bullish": float(macd_histogram.iloc[-1]) > 0,
        "momentum_3m_pct": round(momentum_3m, 2) if momentum_3m else None,
        "momentum_6m_pct": round(momentum_6m, 2) if momentum_6m else None,
        "volume_trend_pct": round(volume_trend, 2),
        "volatility_annual_pct": round(volatility_annual, 2),
        "high_52w": high_52w,
        "low_52w": low_52w,
        "pct_from_52w_high": round((current - high_52w) / high_52w * 100, 2),
        "pct_from_52w_low": round((current - low_52w) / low_52w * 100, 2),
    }


def calculate_portfolio_metrics(positions: list[dict]) -> dict:
    """
    Calculates portfolio-level metrics: weights, correlations, overall volatility.
    positions: list of {ticker, quantity, average_purchase_price}
    """
    if not positions:
        return {}

    tickers = [p["ticker"] for p in positions]

    # Fetch historical data for all tickers
    price_data = {}
    for ticker in tickers:
        df = get_historical_data(ticker, period="1y")
        if df is not None and not df.empty:
            price_data[ticker] = df["Close"]

    if not price_data:
        return {}

    # Align all series on common dates
    prices_df = pd.DataFrame(price_data).dropna()

    # Current portfolio value
    current_prices = {}
    for ticker in tickers:
        if ticker in prices_df.columns:
            current_prices[ticker] = float(prices_df[ticker].iloc[-1])

    position_values = {}
    total_value = 0.0
    for p in positions:
        ticker = p["ticker"]
        if ticker in current_prices:
            val = current_prices[ticker] * float(p["quantity"])
            position_values[ticker] = val
            total_value += val

    weights = {t: (v / total_value if total_value > 0 else 0) for t, v in position_values.items()}

    # Returns and correlations
    returns_df = prices_df.pct_change().dropna()

    correlation_matrix = {}
    if len(returns_df.columns) > 1:
        corr = returns_df.corr()
        correlation_matrix = corr.to_dict()

    # Drawdowns from peak
    drawdowns = {}
    for ticker in tickers:
        if ticker in prices_df.columns:
            series = prices_df[ticker]
            peak = series.cummax()
            dd = (series - peak) / peak * 100
            drawdowns[ticker] = float(dd.iloc[-1])

    # Annualised volatility per position
    volatilities = {}
    for ticker in tickers:
        if ticker in returns_df.columns:
            volatilities[ticker] = float(returns_df[ticker].std() * np.sqrt(252) * 100)

    return {
        "total_value": total_value,
        "weights": weights,
        "current_prices": current_prices,
        "correlation_matrix": correlation_matrix,
        "drawdowns_from_peak_pct": drawdowns,
        "volatilities_annual_pct": volatilities,
    }


import re as _re

# Valid ticker pattern: 1-5 uppercase letters, optionally followed by
# a dot/dash suffix for share classes or ETFs (e.g. BRK.B, BF-B)
_TICKER_RE = _re.compile(r'^[A-Z]{1,5}([.\-][A-Z]{1,2})?$')


def validate_ticker(ticker: str) -> bool:
    """Validate ticker symbol.

    Step 1: format check (fast, offline) — rejects obvious garbage like
            'ABC123', '!!', empty strings, etc.
    Step 2: try Yahoo Finance to confirm the symbol actually trades.
            If Yahoo is unreachable (network error), fall back to format-only
            validation so Docker/firewall issues don't block users.
    """
    t = ticker.strip().upper()

    # Fast offline check — reject non-ticker strings immediately
    if not _TICKER_RE.match(t):
        return False

    # Online confirmation
    try:
        tk = yf.Ticker(t)

        try:
            price = tk.fast_info.last_price
            if price and price > 0:
                return True
        except Exception:
            pass

        try:
            hist = tk.history(period="5d")
            if not hist.empty:
                return True
        except Exception:
            pass

        try:
            info = tk.info
            if info.get("exchange") or info.get("regularMarketPrice") or info.get("currentPrice"):
                return True
        except Exception:
            pass

        # Yahoo returned nothing for this symbol — treat as invalid
        return False

    except Exception as e:
        # Network / connectivity error — format already passed, allow it
        logger.warning(f"validate_ticker: cannot reach Yahoo Finance for {t}: {e}. Accepting based on format.")
        return True


def get_sector_median_pe(sector: str) -> Optional[float]:
    """Approximate sector median P/E from a lookup table (no live API call needed)."""
    sector_pe = {
        "Technology": 28.0,
        "Healthcare": 22.0,
        "Financial Services": 14.0,
        "Consumer Cyclical": 20.0,
        "Consumer Defensive": 18.0,
        "Energy": 12.0,
        "Utilities": 17.0,
        "Industrials": 19.0,
        "Basic Materials": 15.0,
        "Communication Services": 20.0,
        "Real Estate": 25.0,
        "Unknown": 18.0,
    }
    return sector_pe.get(sector, 18.0)


def get_ohlcv_for_chart(ticker: str, period: str = "1y") -> list[dict]:
    """Returns OHLCV as list of dicts for frontend charting."""
    df = get_historical_data(ticker, period=period)
    if df is None or df.empty:
        return []
    result = []
    for ts, row in df.iterrows():
        result.append({
            "date": ts.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        })
    return result
