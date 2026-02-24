import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db, SessionLocal
from app.models.chat import ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse, ExpertChatResponse
from app.services.chat_service import (
    ask_experts,
    ask_experts_stream,
    _build_position_context,
    _get_conversation_history,
)

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


@router.post("/stream")
def send_message_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """SSE endpoint: calls experts sequentially, yields each result as it completes."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Read DB data synchronously before handing off to generator
    portfolio_context = _build_position_context(db, ticker=request.position_ticker)
    conversation_history = _get_conversation_history(db, request.session_id)
    session_id = request.session_id or str(uuid.uuid4())
    user_message = request.message
    position_ticker = request.position_ticker

    def generate():
        expert_responses = []

        for result in ask_experts_stream(user_message, portfolio_context, conversation_history):
            expert_responses.append(result)
            yield f"data: {json.dumps({'type': 'expert', 'expert': result})}\n\n"

        # Save to DB using a fresh session (Depends session may be closed by now)
        with SessionLocal() as new_db:
            msg = ChatMessage(
                user_message=user_message,
                expert_responses=expert_responses,
                context_references={"ticker": position_ticker} if position_ticker else {},
                session_id=session_id,
            )
            new_db.add(msg)
            new_db.commit()
            new_db.refresh(msg)
            yield f"data: {json.dumps({'type': 'done', 'message_id': msg.id, 'session_id': session_id, 'created_at': msg.created_at.isoformat()})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
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
