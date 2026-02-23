from sqlalchemy import Column, Integer, String, DateTime, JSON, func, Text
from app.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_message = Column(Text, nullable=False)
    expert_responses = Column(JSON, nullable=False)  # {value: {...}, momentum: {...}, risk: {...}}
    context_references = Column(JSON, nullable=True)  # referenced positions/recommendations
    session_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
