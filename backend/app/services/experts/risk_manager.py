import logging
from typing import Optional
from app.services.experts.base import ExpertRecommendationResult
from app.services import market_data as md

logger = logging.getLogger(__name__)

RISK_THRESHOLDS = {
    "conservative": {
        "max_position_pct": 5.0,
        "max_sector_pct": 15.0,
        "max_volatility_pct": 25.0,   # annualised
        "max_correlation": 0.6,
        "max_drawdown_pct": -15.0,
    },
    "balanced": {
        "max_position_pct": 10.0,
        "max_sector_pct": 25.0,
        "max_volatility_pct": 40.0,
        "max_correlation": 0.7,
        "max_drawdown_pct": -25.0,
    },
    "aggressive": {
        "max_position_pct": 15.0,
        "max_sector_pct": 35.0,
        "max_volatility_pct": 60.0,
        "max_correlation": 0.8,
        "max_drawdown_pct": -40.0,
    },
}


class RiskManagerExpert:
    """
    Risk Manager: monitors position concentration, portfolio correlations,
    drawdowns from peak, and overall volatility relative to risk profile.
    """

    EXPERT_TYPE = "risk"

    def analyze(
        self,
        position_id: int,
        ticker: str,
        quantity: float,
        avg_purchase_price: float,
        risk_profile: str,
        portfolio_metrics: Optional[dict] = None,
        sector: Optional[str] = None,
        portfolio_sector_weights: Optional[dict] = None,
        previous_recommendation: Optional[dict] = None,
    ) -> ExpertRecommendationResult:

        thresholds = RISK_THRESHOLDS.get(risk_profile, RISK_THRESHOLDS["balanced"])
        price_data = md.get_current_price(ticker)

        if not price_data or not portfolio_metrics:
            return ExpertRecommendationResult(
                expert_type=self.EXPERT_TYPE,
                action="hold",
                target_price=None,
                quantity_change=None,
                confidence_level=20,
                reasoning="Insufficient portfolio data for risk analysis. Hold.",
                market_snapshot={},
            )

        current_price = price_data.get("current_price", 0)
        weights = portfolio_metrics.get("weights", {})
        volatilities = portfolio_metrics.get("volatilities_annual_pct", {})
        correlation_matrix = portfolio_metrics.get("correlation_matrix", {})
        drawdowns = portfolio_metrics.get("drawdowns_from_peak_pct", {})

        position_weight = weights.get(ticker, 0) * 100  # as percentage
        position_volatility = volatilities.get(ticker, 0)
        position_drawdown = drawdowns.get(ticker, 0)

        # Correlation with other positions
        corr_data = correlation_matrix.get(ticker, {})
        high_corr_tickers = [
            t for t, v in corr_data.items()
            if t != ticker and v is not None and abs(v) >= thresholds["max_correlation"]
        ]

        snapshot = {
            "price": current_price,
            "position_weight_pct": position_weight,
            "position_volatility_pct": position_volatility,
            "position_drawdown_pct": position_drawdown,
            "high_correlation_tickers": high_corr_tickers,
            "sector": sector,
            "risk_profile": risk_profile,
            "thresholds": thresholds,
        }

        reasoning_parts = []
        warnings = []
        action = "hold"
        confidence = 55
        quantity_change = None

        # --- Concentration check ---
        if position_weight > thresholds["max_position_pct"]:
            excess = position_weight - thresholds["max_position_pct"]
            reduce_pct = excess / position_weight
            quantity_change = -quantity * reduce_pct
            action = "reduce"
            confidence = 75
            reasoning_parts.append(
                f"Position weight {position_weight:.1f}% exceeds {risk_profile} limit of "
                f"{thresholds['max_position_pct']:.0f}%. Recommend reducing by "
                f"{reduce_pct*100:.0f}% ({abs(quantity_change):.0f} shares) to rebalance."
            )

        # --- Sector concentration ---
        if sector and portfolio_sector_weights:
            sector_weight = portfolio_sector_weights.get(sector, 0) * 100
            if sector_weight > thresholds["max_sector_pct"]:
                warnings.append(
                    f"Sector '{sector}' represents {sector_weight:.1f}% of portfolio "
                    f"(limit: {thresholds['max_sector_pct']:.0f}%). Consider diversifying."
                )

        # --- Volatility check ---
        if position_volatility > thresholds["max_volatility_pct"]:
            warnings.append(
                f"Annual volatility {position_volatility:.1f}% exceeds "
                f"{risk_profile} threshold {thresholds['max_volatility_pct']:.0f}%."
            )
            if action == "hold":
                action = "reduce"
                confidence = 65
                quantity_change = -quantity * 0.15
                reasoning_parts.append(
                    f"High volatility ({position_volatility:.1f}%) for {risk_profile} strategy. Trim 15%."
                )

        # --- Drawdown check ---
        if position_drawdown < thresholds["max_drawdown_pct"]:
            warnings.append(
                f"Drawdown from peak: {position_drawdown:.1f}% (limit: {thresholds['max_drawdown_pct']:.0f}%)."
            )
            if action == "hold":
                action = "reduce"
                confidence = 70
                quantity_change = -quantity * 0.2
                reasoning_parts.append(
                    f"Position down {abs(position_drawdown):.1f}% from peak — exceeds max drawdown for {risk_profile} profile. Reduce 20%."
                )

        # --- Correlation warning ---
        if high_corr_tickers:
            warnings.append(
                f"High correlation (≥{thresholds['max_correlation']}) with: {', '.join(high_corr_tickers)}. "
                "Portfolio may be less diversified than it appears."
            )

        if not reasoning_parts:
            reasoning_parts.append(
                f"Position weight {position_weight:.1f}%, volatility {position_volatility:.1f}%, "
                f"drawdown {position_drawdown:.1f}% — all within {risk_profile} limits. Risk profile: OK."
            )

        if warnings:
            reasoning_parts.append("WARNINGS: " + " | ".join(warnings))

        return ExpertRecommendationResult(
            expert_type=self.EXPERT_TYPE,
            action=action,
            target_price=None,
            quantity_change=round(quantity_change, 2) if quantity_change else None,
            confidence_level=confidence,
            reasoning=" ".join(reasoning_parts),
            market_snapshot=snapshot,
        )
