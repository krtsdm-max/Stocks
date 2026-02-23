from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.chat import ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse, ExpertChatResponse
from app.services.chat_service import ask_experts

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_message(request: ChatRequest, db: Session = Depends(get_db)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    msg = ask_experts(
        db=db,
        user_message=request.message,
        session_id=request.session_id,
        position_ticker=request.position_ticker,
    )

    return ChatResponse(
        id=msg.id,
        user_message=msg.user_message,
        expert_responses=[
            ExpertChatResponse(
                expert_type=r["expert_type"],
                expert_name=r["expert_name"],
                response=r["response"],
            )
            for r in msg.expert_responses
        ],
        session_id=msg.session_id,
        created_at=msg.created_at,
    )


@router.get("/history")
def get_chat_history(session_id: str = None, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(ChatMessage).order_by(ChatMessage.created_at.desc())
    if session_id:
        query = query.filter(ChatMessage.session_id == session_id)
    messages = query.limit(limit).all()
    messages.reverse()

    return [
        {
            "id": m.id,
            "user_message": m.user_message,
            "expert_responses": m.expert_responses,
            "session_id": m.session_id,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
