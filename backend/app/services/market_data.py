import json
import logging
import re as _re
import time
import threading
from datetime import datetime, timedelta
from typing import Optional

import httpx as _httpx
import numpy as np
import pandas as pd
import redis
import requests as _requests
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


_yf_session_lock = threading.Lock()
_yf_session_state: dict = {"session": None, "expires": 0.0}

_YF_REQ_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
}


def _get_yf_session() -> _requests.Session:
    """Return a requests.Session pre-loaded with Yahoo Finance cookies.
    Refreshed at most once per hour so we don't hammer the consent page.
    """
    with _yf_session_lock:
        now = time.monotonic()
        if _yf_session_state["session"] and now < _yf_session_state["expires"]:
            return _yf_session_state["session"]

        sess = _requests.Session()
        sess.headers.update(_YF_REQ_HEADERS)
        try:
            r = sess.get("https://finance.yahoo.com", timeout=8)
            r.raise_for_status()
            logger.debug("yfinance session cookies refreshed")
        except Exception as e:
            logger.warning(f"_get_yf_session: failed to seed cookies: {e}")

        _yf_session_state.update({"session": sess, "expires": now + 3600.0})
        return sess


def get_current_price(ticker: str) -> Optional[dict]:
    """Returns current price + day change for a ticker."""
    key = _cache_key("price", ticker)
    cached = _cache_get(key)
    if cached:
        return cached

    try:
        sess = _get_yf_session()
        tk = yf.Ticker(ticker, session=sess)
        info = tk.fast_info
        current_price = None
        try:
            current_price = float(info.last_price) if info.last_price else None
        except Exception:
            pass
        previous_close = None
        try:
            previous_close = float(info.previous_close) if info.previous_close else None
        except Exception:
            pass
        data = {
            "ticker": ticker,
            "current_price": current_price,
            "previous_close": previous_close,
            "day_change": None,
            "day_change_pct": None,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if data["current_price"] and data["previous_close"]:
            data["day_change"] = data["current_price"] - data["previous_close"]
            data["day_change_pct"] = (data["day_change"] / data["previous_close"]) * 100
        if data["current_price"] is not None:
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
        sess = _get_yf_session()
        tk = yf.Ticker(ticker, session=sess)
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
        sess = _get_yf_session()
        tk = yf.Ticker(ticker, session=sess)
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
            position_values[ticker] = position_values.get(ticker, 0.0) + val
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


# Valid ticker pattern: 1-5 uppercase letters, optionally followed by
# a dot/dash suffix for share classes or ETFs (e.g. BRK.B, BF-B)
_TICKER_RE = _re.compile(r'^[A-Z]{1,5}([.\-][A-Z]{1,2})?$')

_YF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://finance.yahoo.com",
    "Referer": "https://finance.yahoo.com/",
}

# ---------------------------------------------------------------------------
# Yahoo Finance crumb / cookie session (refreshed once per hour)
# ---------------------------------------------------------------------------
_crumb_lock = threading.Lock()
_crumb_state: dict = {"crumb": None, "cookies": {}, "expires": 0.0}


def _get_yf_crumb() -> tuple[str | None, dict]:
    """Return (crumb, cookies) for Yahoo Finance API calls.
    Fetches a fresh crumb at most once per hour; cached otherwise.
    Returns (None, {}) on any failure — callers must tolerate absent crumb.
    """
    with _crumb_lock:
        now = time.monotonic()
        if _crumb_state["crumb"] and now < _crumb_state["expires"]:
            return _crumb_state["crumb"], _crumb_state["cookies"]

        crumb: str | None = None
        cookies: dict = {}
        try:
            with _httpx.Client(timeout=8.0, follow_redirects=True) as client:
                # Step 1 — land on finance.yahoo.com to collect consent cookies
                r = client.get("https://finance.yahoo.com", headers=_YF_HEADERS)
                cookies = dict(r.cookies)

                # Step 2 — fetch crumb using the session cookies
                cr = client.get(
                    "https://query2.finance.yahoo.com/v1/test/getcrumb",
                    headers=_YF_HEADERS,
                    cookies=cookies,
                )
                if cr.status_code == 200 and cr.text and cr.text.strip() not in ("", "null"):
                    crumb = cr.text.strip()
                    logger.debug(f"Yahoo Finance crumb acquired: {crumb[:6]}…")
        except Exception as e:
            logger.warning(f"_get_yf_crumb failed: {e}")

        _crumb_state.update({"crumb": crumb, "cookies": cookies, "expires": now + 3600.0})
        return crumb, cookies


# ---------------------------------------------------------------------------
# Minimal token-bucket rate-limiter — max 2 requests/sec to Yahoo Finance
# ---------------------------------------------------------------------------
_rl_lock = threading.Lock()
_rl_tokens: float = 2.0
_rl_last_refill: float = time.monotonic()
_RL_RATE = 2.0   # tokens per second
_RL_MAX = 2.0


def _rl_acquire() -> None:
    """Block until a rate-limit token is available."""
    with _rl_lock:
        global _rl_tokens, _rl_last_refill
        now = time.monotonic()
        elapsed = now - _rl_last_refill
        _rl_tokens = min(_RL_MAX, _rl_tokens + elapsed * _RL_RATE)
        _rl_last_refill = now
        if _rl_tokens >= 1.0:
            _rl_tokens -= 1.0
            return
        wait = (1.0 - _rl_tokens) / _RL_RATE
    time.sleep(wait)


def _yf_get(client: _httpx.Client, url: str, params: dict | None = None) -> _httpx.Response:
    """Rate-limited GET to Yahoo Finance with crumb + cookie injection."""
    _rl_acquire()
    crumb, cookies = _get_yf_crumb()
    p = dict(params or {})
    if crumb:
        p["crumb"] = crumb
    return client.get(url, params=p, headers=_YF_HEADERS, cookies=cookies)


def lookup_ticker(ticker: str) -> dict:
    """Return ticker info with one of three states:
      valid=True   — confirmed exists, includes name/price/exchange
      valid=False  — confirmed does not exist (bad format or Yahoo returned empty)
      valid=None   — could not reach any data source (network error / rate limited)

    Tries multiple sources in order:
      1. Yahoo Finance v8 chart API with crumb session (query2 then query1)
      2. yfinance library (fast_info, then history)
    """
    t = ticker.strip().upper()

    # Format check first — rejects garbage without any network call
    if not _TICKER_RE.match(t):
        return {"valid": False, "name": None, "price": None, "exchange": None}

    network_error = False
    rate_limited = False

    # --- Strategy 1: Yahoo Finance v8 chart with crumb ---
    for base in ("https://query2.finance.yahoo.com", "https://query1.finance.yahoo.com"):
        try:
            url = f"{base}/v8/finance/chart/{t}"
            with _httpx.Client(timeout=8.0, follow_redirects=True) as client:
                resp = _yf_get(client, url, {"interval": "1d", "range": "5d"})

            if resp.status_code == 200:
                data = resp.json()
                result = (data.get("chart") or {}).get("result") or []
                if result:
                    meta = result[0].get("meta", {})
                    price = meta.get("regularMarketPrice") or meta.get("previousClose")
                    name = meta.get("longName") or meta.get("shortName") or t
                    exchange = meta.get("exchangeName") or meta.get("fullExchangeName")
                    if price:
                        return {"valid": True, "name": name, "price": float(price), "exchange": exchange}
                # 200 but empty result → ticker doesn't exist on this exchange
                return {"valid": False, "name": None, "price": None, "exchange": None}
            elif resp.status_code == 404:
                return {"valid": False, "name": None, "price": None, "exchange": None}
            elif resp.status_code == 429:
                logger.warning(f"lookup_ticker: 429 rate-limited by Yahoo Finance ({base}) for {t}")
                rate_limited = True
                # Invalidate crumb so next call fetches a fresh one
                with _crumb_lock:
                    _crumb_state["expires"] = 0.0
                # Don't bother trying the other Yahoo base — same IP, same limit
                break
            else:
                logger.debug(f"lookup_ticker {base} returned {resp.status_code} for {t}")
                network_error = True
        except Exception as e:
            logger.debug(f"lookup_ticker {base} failed for {t}: {e}")
            network_error = True

    # If we're hard rate-limited by Yahoo, skip yfinance (it uses the same endpoint)
    if rate_limited:
        logger.warning(f"lookup_ticker: Yahoo Finance rate-limited for {t}, returning unknown state")
        return {"valid": None, "name": None, "price": None, "exchange": None}

    # --- Strategy 2: yfinance fast_info ---
    try:
        sess = _get_yf_session()
        tk = yf.Ticker(t, session=sess)
        price = tk.fast_info.last_price
        if price and price > 0:
            full = tk.info
            name = full.get("longName") or full.get("shortName") or t
            return {"valid": True, "name": name, "price": float(price), "exchange": full.get("exchange")}
        # fast_info returned but no price — symbol likely invalid
        return {"valid": False, "name": None, "price": None, "exchange": None}
    except Exception as e:
        logger.debug(f"lookup_ticker yfinance fast_info failed for {t}: {e}")
        network_error = True

    # --- Strategy 3: yfinance history ---
    try:
        sess = _get_yf_session()
        tk = yf.Ticker(t, session=sess)
        hist = tk.history(period="5d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            full = tk.info
            name = full.get("longName") or full.get("shortName") or t
            return {"valid": True, "name": name, "price": price, "exchange": full.get("exchange")}
        return {"valid": False, "name": None, "price": None, "exchange": None}
    except Exception as e:
        logger.debug(f"lookup_ticker yfinance history failed for {t}: {e}")
        network_error = True

    # All sources failed due to network — return unknown state
    if network_error:
        logger.warning(f"lookup_ticker: all sources unreachable for {t}, returning unknown state")
        return {"valid": None, "name": None, "price": None, "exchange": None}

    return {"valid": False, "name": None, "price": None, "exchange": None}


def validate_ticker(ticker: str) -> bool:
    """Returns True if confirmed valid or if data sources are unreachable (fail-open)."""
    result = lookup_ticker(ticker)
    # valid=None means network error — fail open so users aren't blocked
    return result["valid"] is not False


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
