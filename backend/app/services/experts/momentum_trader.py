import logging
from typing import Optional
from app.services.experts.base import ExpertRecommendationResult
from app.services import market_data as md

logger = logging.getLogger(__name__)


class MomentumTraderExpert:
    """
    Momentum Trader: focuses on technical indicators — MA crossovers, RSI, MACD,
    volume trends, and price momentum over 3 and 6 months.
    """

    EXPERT_TYPE = "momentum"

    def analyze(
        self,
        position_id: int,
        ticker: str,
        quantity: float,
        avg_purchase_price: float,
        risk_profile: str,
        previous_recommendation: Optional[dict] = None,
    ) -> ExpertRecommendationResult:

        technicals = md.calculate_technical_indicators(ticker)
        price_data = md.get_current_price(ticker)

        if not technicals:
            return ExpertRecommendationResult(
                expert_type=self.EXPERT_TYPE,
                action="hold",
                target_price=None,
                quantity_change=None,
                confidence_level=20,
                reasoning="Insufficient historical data for technical analysis. Holding pending data.",
                market_snapshot={},
            )

        current_price = technicals["current_price"]
        ma50 = technicals["ma50"]
        ma200 = technicals.get("ma200")
        rsi = technicals["rsi"]
        rsi_signal = technicals["rsi_signal"]
        macd_hist = technicals["macd_histogram"]
        macd_bullish = technicals["macd_bullish"]
        momentum_3m = technicals.get("momentum_3m_pct")
        momentum_6m = technicals.get("momentum_6m_pct")
        above_ma50 = technicals["above_ma50"]
        above_ma200 = technicals.get("above_ma200")
        golden_cross = technicals.get("golden_cross")
        vol_trend = technicals["volume_trend_pct"]

        snapshot = {
            "price": current_price,
            "ma50": ma50,
            "ma200": ma200,
            "rsi": rsi,
            "macd_histogram": macd_hist,
            "momentum_3m_pct": momentum_3m,
            "momentum_6m_pct": momentum_6m,
            "volume_trend_pct": vol_trend,
            "above_ma50": above_ma50,
            "above_ma200": above_ma200,
            "golden_cross": golden_cross,
        }

        reasoning_parts = []
        bullish_signals = 0
        bearish_signals = 0

        # --- MA analysis ---
        if above_ma50:
            reasoning_parts.append(f"Price ${current_price:.2f} is above 50-day MA ${ma50:.2f} (bullish).")
            bullish_signals += 1
        else:
            reasoning_parts.append(f"Price ${current_price:.2f} is below 50-day MA ${ma50:.2f} (bearish).")
            bearish_signals += 1

        if ma200:
            if above_ma200:
                reasoning_parts.append(f"Above 200-day MA ${ma200:.2f} — long-term uptrend intact.")
                bullish_signals += 1
            else:
                reasoning_parts.append(f"Below 200-day MA ${ma200:.2f} — long-term trend negative.")
                bearish_signals += 1

            if golden_cross:
                reasoning_parts.append("Golden cross (50 > 200 MA) — strong bull structure.")
                bullish_signals += 1
            else:
                reasoning_parts.append("Death cross (50 < 200 MA) — bearish alignment.")
                bearish_signals += 1

        # --- RSI ---
        if rsi > 70:
            reasoning_parts.append(f"RSI {rsi:.0f} is overbought (>70) — momentum overextended.")
            bearish_signals += 2
        elif rsi < 30:
            reasoning_parts.append(f"RSI {rsi:.0f} is oversold (<30) — potential bounce.")
            bullish_signals += 1
        elif 50 <= rsi <= 70:
            reasoning_parts.append(f"RSI {rsi:.0f} in healthy momentum zone (50–70).")
            bullish_signals += 1
        else:
            reasoning_parts.append(f"RSI {rsi:.0f} in neutral zone.")

        # --- MACD ---
        if macd_bullish:
            reasoning_parts.append("MACD histogram positive — bullish momentum.")
            bullish_signals += 1
        else:
            reasoning_parts.append("MACD histogram negative — momentum waning.")
            bearish_signals += 1

        # --- Price momentum ---
        if momentum_3m:
            if momentum_3m > 10:
                reasoning_parts.append(f"3M momentum +{momentum_3m:.1f}% — strong trend.")
                bullish_signals += 1
            elif momentum_3m < -10:
                reasoning_parts.append(f"3M momentum {momentum_3m:.1f}% — significant weakness.")
                bearish_signals += 1

        if momentum_6m:
            if momentum_6m > 20:
                bullish_signals += 1
            elif momentum_6m < -20:
                bearish_signals += 1

        # --- Volume ---
        if vol_trend > 20:
            reasoning_parts.append(f"Volume trending up {vol_trend:.0f}% — institutional interest.")
            bullish_signals += 1
        elif vol_trend < -20:
            reasoning_parts.append(f"Volume declining {abs(vol_trend):.0f}% — distribution.")
            bearish_signals += 1

        # --- Decision ---
        action = "hold"
        confidence = 50
        quantity_change = None
        target_price = None

        total_signals = bullish_signals + bearish_signals
        if total_signals == 0:
            total_signals = 1

        bull_ratio = bullish_signals / total_signals

        if bull_ratio >= 0.7:
            if rsi < 60 and above_ma50:  # healthy momentum, room to run
                action = "add"
                confidence = 70
                quantity_change = quantity * 0.15
                target_price = current_price * 1.10  # +10% target
                reasoning_parts.append("Strong technical setup → recommend adding 15% on dips.")
            else:
                action = "hold"
                confidence = 65
        elif bull_ratio <= 0.35:
            if rsi > 70:
                action = "reduce"
                confidence = 72
                quantity_change = -quantity * 0.3
                reasoning_parts.append("Overbought with deteriorating signals → reduce 30% to lock in gains.")
            elif not above_ma50 and not above_ma200:
                action = "sell"
                confidence = 68
                quantity_change = -quantity * 0.5
                reasoning_parts.append("Broken both MAs with negative momentum → sell 50% to limit drawdown.")
            else:
                action = "reduce"
                confidence = 60
                quantity_change = -quantity * 0.2
                reasoning_parts.append("Bearish signal majority → trim position by 20%.")

        # Consistency check with previous
        if previous_recommendation:
            prev_action = previous_recommendation.get("action")
            prev_snap = previous_recommendation.get("market_snapshot", {})
            prev_rsi = prev_snap.get("rsi")
            if prev_action == "add" and action == "add" and rsi > 65:
                action = "hold"
                reasoning_parts.append(
                    "Previously recommended adding; RSI has risen since — hold existing position, wait for better entry."
                )

        return ExpertRecommendationResult(
            expert_type=self.EXPERT_TYPE,
            action=action,
            target_price=round(target_price, 2) if target_price else None,
            quantity_change=round(quantity_change, 2) if quantity_change else None,
            confidence_level=confidence,
            reasoning=" ".join(reasoning_parts),
            market_snapshot=snapshot,
        )
