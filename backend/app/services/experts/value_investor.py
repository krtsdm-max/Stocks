import logging
from typing import Optional
from app.services.experts.base import ExpertRecommendationResult
from app.services import market_data as md

logger = logging.getLogger(__name__)


class ValueInvestorExpert:
    """
    Value Investor: focuses on fundamental valuation (P/E, P/B, dividend yield)
    relative to sector medians. Uses comparable multiples for fair value.
    """

    EXPERT_TYPE = "value"

    def analyze(
        self,
        position_id: int,
        ticker: str,
        quantity: float,
        avg_purchase_price: float,
        risk_profile: str,
        previous_recommendation: Optional[dict] = None,
    ) -> ExpertRecommendationResult:

        fundamentals = md.get_fundamentals(ticker)
        price_data = md.get_current_price(ticker)

        if not fundamentals or not price_data:
            return ExpertRecommendationResult(
                expert_type=self.EXPERT_TYPE,
                action="hold",
                target_price=None,
                quantity_change=None,
                confidence_level=20,
                reasoning="Unable to fetch market data. Defaulting to hold pending data availability.",
                market_snapshot={},
            )

        current_price = price_data.get("current_price") or fundamentals.get("current_price")
        if not current_price:
            return ExpertRecommendationResult(
                expert_type=self.EXPERT_TYPE,
                action="hold",
                target_price=None,
                quantity_change=None,
                confidence_level=20,
                reasoning="No current price available.",
                market_snapshot=fundamentals,
            )

        sector = fundamentals.get("sector", "Unknown")
        pe = fundamentals.get("pe_ratio")
        pb = fundamentals.get("pb_ratio")
        div_yield = fundamentals.get("dividend_yield") or 0.0
        sector_median_pe = md.get_sector_median_pe(sector)
        beta = fundamentals.get("beta")

        snapshot = {
            "price": current_price,
            "pe_ratio": pe,
            "pb_ratio": pb,
            "dividend_yield": div_yield,
            "sector": sector,
            "sector_median_pe": sector_median_pe,
            "beta": beta,
            "52w_high": fundamentals.get("52w_high"),
            "52w_low": fundamentals.get("52w_low"),
        }

        # --- Fair value estimation via comparable multiples ---
        fair_value = None
        reasoning_parts = []

        if pe and sector_median_pe:
            pe_discount = (sector_median_pe - pe) / sector_median_pe * 100
            if pe_discount > 0:
                reasoning_parts.append(
                    f"P/E {pe:.1f} is {pe_discount:.1f}% below sector median {sector_median_pe:.1f} → undervalued"
                )
            else:
                reasoning_parts.append(
                    f"P/E {pe:.1f} is {abs(pe_discount):.1f}% above sector median {sector_median_pe:.1f} → elevated valuation"
                )
            # Rough fair value: if P/E is in line with sector median
            forward_pe = fundamentals.get("forward_pe")
            if forward_pe:
                # EPS implied
                eps_implied = current_price / pe
                fair_value = eps_implied * sector_median_pe
                reasoning_parts.append(
                    f"Comparable-multiples fair value: ${fair_value:.2f} (sector P/E × implied EPS)"
                )

        if pb and pb < 1.5:
            reasoning_parts.append(f"P/B {pb:.2f} suggests asset backing is strong.")
        elif pb and pb > 4.0:
            reasoning_parts.append(f"P/B {pb:.2f} is elevated — market pricing in significant premium.")

        if div_yield and div_yield > 0.03:
            reasoning_parts.append(f"Dividend yield {div_yield*100:.1f}% provides income support.")

        # --- Decision logic ---
        action = "hold"
        confidence = 50
        quantity_change = None

        if pe and sector_median_pe:
            pe_overvaluation = (pe - sector_median_pe) / sector_median_pe * 100
            if pe_overvaluation > 30:
                action = "reduce"
                confidence = 70
                quantity_change = -quantity * 0.25  # reduce by 25%
                reasoning_parts.append(
                    f"P/E is {pe_overvaluation:.0f}% above sector median (threshold: 30%) → recommend reducing 25% of position."
                )
            elif pe_overvaluation > 50:
                action = "sell"
                confidence = 80
                quantity_change = -quantity * 0.5
                reasoning_parts.append(
                    "P/E >50% above sector — significant overvaluation. Recommend selling half position."
                )
            elif pe_overvaluation < -20:
                action = "add"
                confidence = 65
                quantity_change = quantity * 0.2  # add 20%
                reasoning_parts.append(
                    f"P/E is {abs(pe_overvaluation):.0f}% below sector median → attractive entry for adding 20%."
                )

        # Consistency with previous recommendation
        if previous_recommendation:
            prev_action = previous_recommendation.get("action", "hold")
            prev_snapshot = previous_recommendation.get("market_snapshot", {})
            prev_price = prev_snapshot.get("price")
            if prev_price and current_price and prev_action in ("add", "buy"):
                price_move = (current_price - prev_price) / prev_price * 100
                if price_move > 15 and action == "add":
                    action = "hold"
                    reasoning_parts.append(
                        f"Previously recommended adding at ${prev_price:.2f}; stock has risen {price_move:.1f}% since — upgrading to hold pending new entry level."
                    )

        if not reasoning_parts:
            reasoning_parts.append("Valuation metrics appear in line with sector. Maintaining hold.")

        return ExpertRecommendationResult(
            expert_type=self.EXPERT_TYPE,
            action=action,
            target_price=round(fair_value, 2) if fair_value else None,
            quantity_change=round(quantity_change, 2) if quantity_change else None,
            confidence_level=confidence,
            reasoning=" ".join(reasoning_parts),
            market_snapshot=snapshot,
        )
