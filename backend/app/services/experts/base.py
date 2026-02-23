from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass
class ExpertRecommendationResult:
    expert_type: str          # value / momentum / risk
    action: str               # hold / buy / add / reduce / sell / close
    target_price: Optional[float]
    quantity_change: Optional[float]   # signed: positive = buy more, negative = reduce
    confidence_level: int     # 0–100
    reasoning: str
    market_snapshot: dict
