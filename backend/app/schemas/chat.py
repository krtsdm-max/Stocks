from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    position_ticker: Optional[str] = None  # optional context


class ExpertChatResponse(BaseModel):
    expert_type: str
    expert_name: str
    response: str


class ChatResponse(BaseModel):
    id: int
    user_message: str
    expert_responses: list[ExpertChatResponse]
    session_id: str
    created_at: datetime

    class Config:
        from_attributes = True
