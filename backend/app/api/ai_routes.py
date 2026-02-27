"""AI Chat API endpoint'leri."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.db.models import User, ChatConversation, ChatMessage
from app.core.auth import get_current_user
from app.services.ai_chat_service import ai_chat_service

router = APIRouter(prefix="/api/ai", tags=["AI Chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI chatbot ile sohbet."""
    conv_id = request.conversation_id or str(uuid.uuid4())
    response = await ai_chat_service.chat(user, conv_id, request.message, db)
    return ChatResponse(response=response, conversation_id=conv_id)


@router.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının sohbet geçmişi."""
    conversations = (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == user.id)
        .order_by(desc(ChatConversation.updated_at))
        .limit(20)
        .all()
    )
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sohbet mesajlarını getir."""
    conv = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == user.id,
    ).first()
    if not conv:
        raise HTTPException(404, "Sohbet bulunamadı")

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conv.id,
            ChatMessage.role.in_(["user", "assistant"]),
        )
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sohbeti sil."""
    conv = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == user.id,
    ).first()
    if not conv:
        raise HTTPException(404, "Sohbet bulunamadı")
    db.delete(conv)
    db.commit()
    return {"status": "ok"}
