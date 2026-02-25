import logging
import uuid
from typing import Optional, Generator

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.chat import ChatMessage
from app.models.consensus import ConsensusDecision
from app.models.recommendation import ExpertRecommendation
from app.models.position import Position

logger = logging.getLogger(__name__)

EXPERT_PERSONAS = {
    "value": {
        "name": "Victoria Chen",
        "title": "Value Investor",
        "philosophy": (
            "I focus on fundamental analysis — P/E ratios, book value, dividend yield, "
            "and sector comparisons. I look for stocks trading below intrinsic value and "
            "hold positions with conviction. My decisions are data-driven and long-term oriented."
        ),
        "style": "analytical, precise, references specific financial ratios",
    },
    "momentum": {
        "name": "Marcus Rivera",
        "title": "Momentum Trader",
        "philosophy": (
            "I trade with the trend. Moving averages, RSI, MACD, and price momentum guide my decisions. "
            "I care deeply about entry and exit timing. Strong momentum confirms thesis; "
            "deteriorating technicals signal risk regardless of fundamentals."
        ),
        "style": "direct, action-oriented, references chart patterns and technical levels",
    },
    "risk": {
        "name": "Sophie Nakamura",
        "title": "Risk Manager",
        "philosophy": (
            "My job is to protect the portfolio. I monitor concentration limits, correlation clustering, "
            "volatility budgets, and drawdowns. I will always recommend trimming when risk parameters "
            "are exceeded, regardless of how attractive an opportunity seems."
        ),
        "style": "cautious, systematic, references percentages and risk thresholds",
    },
}


def _build_position_context(db: Session, ticker: Optional[str] = None) -> str:
    """Builds portfolio context with raw market data snapshots for LLM reasoning."""
    positions = db.query(Position).all()
    if not positions:
        return "The portfolio is currently empty."

    lines = ["Current portfolio positions with real market data:"]
    for pos in positions:
        is_focused = ticker and pos.ticker == ticker
        line = f"\n{'>>>' if is_focused else '-'} {pos.ticker}: {float(pos.quantity):.4g} shares @ ${float(pos.average_purchase_price):.2f} avg cost"

        # Gather latest market snapshot per expert type
        recs = (
            db.query(ExpertRecommendation)
            .filter(ExpertRecommendation.position_id == pos.id)
            .order_by(ExpertRecommendation.created_at.desc())
            .limit(9)  # up to 3 runs × 3 experts
            .all()
        )
        if recs:
            # Collect most recent snapshot per expert type
            snapshots: dict[str, dict] = {}
            for r in recs:
                if r.expert_type not in snapshots and r.market_snapshot:
                    snapshots[r.expert_type] = r.market_snapshot

            # Merge key market data fields from all snapshots
            merged: dict = {}
            for snap in snapshots.values():
                for k, v in snap.items():
                    if v is not None and k not in merged:
                        merged[k] = v

            # Format key metrics compactly
            metrics = []
            if "price" in merged:
                metrics.append(f"price=${merged['price']:.2f}")
            if "pe_ratio" in merged and merged["pe_ratio"]:
                metrics.append(f"P/E={merged['pe_ratio']:.1f}")
            if "pb_ratio" in merged and merged["pb_ratio"]:
                metrics.append(f"P/B={merged['pb_ratio']:.2f}")
            if "rsi" in merged:
                metrics.append(f"RSI={merged['rsi']:.1f}")
            if "ma50" in merged:
                metrics.append(f"MA50={merged['ma50']:.2f}")
            if "ma200" in merged:
                metrics.append(f"MA200={merged['ma200']:.2f}")
            if "macd_histogram" in merged:
                metrics.append(f"MACD_hist={merged['macd_histogram']:.3f}")
            if "momentum_3m_pct" in merged and merged["momentum_3m_pct"] is not None:
                metrics.append(f"mom3m={merged['momentum_3m_pct']:.1f}%")
            if "position_weight_pct" in merged:
                metrics.append(f"portfolio_weight={merged['position_weight_pct']:.1f}%")
            if "position_volatility_pct" in merged:
                metrics.append(f"volatility={merged['position_volatility_pct']:.1f}%")
            if "position_drawdown_pct" in merged:
                metrics.append(f"drawdown={merged['position_drawdown_pct']:.1f}%")
            if "sector" in merged:
                metrics.append(f"sector={merged['sector']}")
            if "beta" in merged and merged["beta"]:
                metrics.append(f"beta={merged['beta']:.2f}")
            if metrics:
                line += f"\n  Market data: {', '.join(metrics)}"

            # Quantitative model output as reference (not as constraint)
            consensus = (
                db.query(ConsensusDecision)
                .filter(ConsensusDecision.position_id == pos.id)
                .order_by(ConsensusDecision.timestamp.desc())
                .first()
            )
            if consensus:
                votes = consensus.expert_votes or {}
                vote_parts = []
                for etype, vote in votes.items():
                    act = vote.get("action", "?").upper()
                    conf = vote.get("confidence_level", "?")
                    vote_parts.append(f"{etype}={act}({conf}%)")
                line += f"\n  Quant model: {consensus.aggregated_action.upper()} [{consensus.consensus_level}] | {', '.join(vote_parts)}"

            # For focused ticker: include full reasoning from quant model
            if is_focused and consensus:
                for etype, vote in (consensus.expert_votes or {}).items():
                    reasoning = vote.get("reasoning", "")
                    if reasoning:
                        line += f"\n  {etype.upper()} quant reasoning: {reasoning}"
        else:
            line += "\n  Market data: not yet computed (run Refresh to generate)"

        lines.append(line)
    return "\n".join(lines)


def _build_expert_system_prompt(expert_type: str, portfolio_context: str, user_message: str) -> str:
    persona = EXPERT_PERSONAS[expert_type]
    return (
        f"You are {persona['name']}, {persona['title']} on an investment committee.\n\n"
        f"Your philosophy: {persona['philosophy']}\n\n"
        f"Communication style: {persona['style']}.\n\n"
        f"Portfolio context:\n{portfolio_context}\n\n"
        "Rules:\n"
        "1. Always stay in character as this specific expert.\n"
        "2. The portfolio context includes real market data (price, RSI, P/E, MACD, volatility, etc.) "
        "and a 'Quant model' reference showing what a rule-based algorithm concluded. "
        "Use the market data to form YOUR OWN independent analysis. "
        "If you agree with the quant model, say so. If you disagree, explain why — that disagreement is valuable.\n"
        "3. Give CONCRETE, actionable recommendations — not vague commentary.\n"
        "4. Cite specific numbers from the market data provided (RSI, P/E, price vs MA, etc.).\n"
        "5. Keep your response to 2–4 paragraphs.\n"
        "6. Do not pretend to have real-time data beyond what is in the context — acknowledge if data is missing.\n"
        "7. Always end with a clear action statement.\n"
    )


def _get_conversation_history(db: Session, session_id: str) -> list[dict]:
    """Returns last 10 messages in session for context."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(5)
        .all()
    )
    messages.reverse()

    history = []
    for msg in messages:
        history.append({"role": "user", "content": msg.user_message})
        # Combine all expert responses as assistant context
        combined = "\n\n".join(
            f"[{r.get('expert_name', r.get('expert_type', '?'))}]: {r.get('response', '')}"
            for r in msg.expert_responses
        )
        if combined:
            history.append({"role": "assistant", "content": combined})
    return history


def _call_expert(
    client: anthropic.Anthropic,
    expert_type: str,
    persona: dict,
    portfolio_context: str,
    conversation_history: list,
    user_message: str,
) -> dict:
    system_prompt = _build_expert_system_prompt(expert_type, portfolio_context, user_message)
    msgs = conversation_history + [{"role": "user", "content": user_message}]
    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1500,
            system=system_prompt,
            messages=msgs,
        )
        expert_text = response.content[0].text
    except Exception as e:
        logger.error(f"Anthropic API error for expert {expert_type}: {e}")
        expert_text = "I'm unable to provide analysis at the moment. Please try again shortly."
    return {
        "expert_type": expert_type,
        "expert_name": persona["name"],
        "expert_title": persona["title"],
        "response": expert_text,
    }


def ask_experts_stream(
    user_message: str,
    portfolio_context: str,
    conversation_history: list,
) -> Generator[dict, None, None]:
    """Yields expert responses one by one in order: value → momentum → risk."""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    for expert_type, persona in EXPERT_PERSONAS.items():
        result = _call_expert(client, expert_type, persona, portfolio_context, conversation_history, user_message)
        yield result


def ask_experts(
    db: Session,
    user_message: str,
    session_id: Optional[str] = None,
    position_ticker: Optional[str] = None,
) -> ChatMessage:
    if not session_id:
        session_id = str(uuid.uuid4())

    portfolio_context = _build_position_context(db, ticker=position_ticker)
    conversation_history = _get_conversation_history(db, session_id)

    expert_responses = list(ask_experts_stream(user_message, portfolio_context, conversation_history))

    chat_msg = ChatMessage(
        user_message=user_message,
        expert_responses=expert_responses,
        context_references={"ticker": position_ticker} if position_ticker else {},
        session_id=session_id,
    )
    db.add(chat_msg)
    db.commit()
    db.refresh(chat_msg)
    return chat_msg
