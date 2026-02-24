import logging
import uuid
from typing import Optional, Generator

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.chat import ChatMessage
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
    """Builds a context string about current portfolio positions for LLM."""
    positions = db.query(Position).all()
    if not positions:
        return "The portfolio is currently empty."

    lines = ["Current portfolio positions:"]
    for pos in positions:
        line = f"- {pos.ticker}: {float(pos.quantity):.0f} shares @ ${float(pos.average_purchase_price):.2f} avg"
        if ticker and pos.ticker == ticker:
            # Add latest recommendations for this ticker
            recs = (
                db.query(ExpertRecommendation)
                .filter(ExpertRecommendation.position_id == pos.id)
                .order_by(ExpertRecommendation.created_at.desc())
                .limit(3)
                .all()
            )
            if recs:
                line += f"\n  Latest recommendations:"
                for rec in recs:
                    line += f"\n    [{rec.expert_type.upper()}] {rec.recommendation_action.upper()} — {rec.reasoning[:150]}..."
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
        "2. Give CONCRETE, actionable recommendations — not vague commentary.\n"
        "3. Cite specific numbers (prices, percentages, ratios) when you have them.\n"
        "4. Keep your response to 2–4 paragraphs.\n"
        "5. Do not contradict your previous recommendations unless you explicitly explain why the situation changed.\n"
        "6. Do not pretend to have real-time data you don't have — acknowledge if data is unavailable.\n"
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
