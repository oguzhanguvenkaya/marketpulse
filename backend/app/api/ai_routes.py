"""AI Chat API endpoint'leri."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.core.auth import get_current_user
from app.services.ai_chat_service import ai_chat_service

router = APIRouter(prefix="/api/ai", tags=["AI Chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


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
