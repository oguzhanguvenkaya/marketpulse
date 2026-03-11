"""SSE streaming endpoint — /api/ai/chat/stream + Conversations API"""

import logging
import uuid as uuid_mod
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ChatConversation, ChatMessage, User
from app.services.ai_streaming_service import ai_streaming_service
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Streaming"])


class ChatStreamRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    page_context: Optional[dict] = None
    search_scope: Optional[str] = "auto"  # "page" | "global" | "auto"


@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    SSE stream dondurur.
    Event tipleri: tool_start, tool_done, token, done, error
    """
    conversation_id = request.conversation_id or str(uuid_mod.uuid4())

    # page_context field'larini sanitize et (prompt injection onlemi)
    safe_context = _sanitize_context(request.page_context)

    # search_scope validate
    search_scope = request.search_scope or "auto"
    if search_scope not in ("page", "global", "auto"):
        search_scope = "auto"

    async def generate():
        async for event in ai_streaming_service.stream_chat(
            user=current_user,
            conversation_id=conversation_id,
            message=request.message,
            page_context=safe_context,
            search_scope=search_scope,
            db=db,
        ):
            yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Conversation-Id": conversation_id,
        },
    )


def _sanitize_context(ctx: Optional[dict]) -> Optional[dict]:
    """
    page_context field'larini kisalt ve guvenli yap.

    Izin verilen key whitelist'i: prompt injection'a karsi sadece
    bilinen field'lar gecirilebilir. Deger uzunlugu 200 karakterle
    sinirlandirilir. filters objesi icin de ayni kural uygulanir.
    """
    if not ctx:
        return None

    allowed_keys = {
        "page",
        "product_id",
        "sku",
        "product_name",
        "platform",
        "category_name",
        "session_id",
        "merchant_id",
        "seller_name",
        "keyword",
    }

    result: dict = {}
    for k, v in ctx.items():
        if k not in allowed_keys:
            continue
        result[k] = str(v)[:200]

    # filters objesi icin ayri sanitize — sadece dict kabul et
    if isinstance(ctx.get("filters"), dict):
        safe_filters: dict = {}
        allowed_filter_keys = {"brand", "seller", "min_price", "max_price", "platform"}
        for fk, fv in ctx["filters"].items():
            if fk in allowed_filter_keys:
                safe_filters[fk] = str(fv)[:100]
        if safe_filters:
            result["filters"] = safe_filters

    return result or None


# ---------------------------------------------------------------------------
# Conversations API — chat gecmisi CRUD
# ---------------------------------------------------------------------------

def _parse_conversation_uuid(conversation_id: str) -> uuid_mod.UUID:
    """conversation_id string'ini UUID'ye donustur."""
    try:
        return uuid_mod.UUID(conversation_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Gecersiz conversation ID")


def _get_user_conversation(
    conversation_id: str,
    user: User,
    db: Session,
) -> ChatConversation:
    """Conversation'i bul ve kullaniciya ait oldugundan emin ol."""
    conv_uuid = _parse_conversation_uuid(conversation_id)
    conversation = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conv_uuid,
            ChatConversation.user_id == user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Konusma bulunamadi")
    return conversation


@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Kullanicinin tum chat konusmalarini listele.
    updated_at'e gore azalan sirada, mesaj sayisi dahil.
    """
    message_count_subq = (
        db.query(
            ChatMessage.conversation_id,
            func.count(ChatMessage.id).label("message_count"),
        )
        .group_by(ChatMessage.conversation_id)
        .subquery()
    )

    rows = (
        db.query(ChatConversation, message_count_subq.c.message_count)
        .outerjoin(
            message_count_subq,
            ChatConversation.id == message_count_subq.c.conversation_id,
        )
        .filter(ChatConversation.user_id == current_user.id)
        .order_by(ChatConversation.updated_at.desc())
        .all()
    )

    return [
        {
            "id": str(conv.id),
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            "message_count": msg_count or 0,
        }
        for conv, msg_count in rows
    ]


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Belirli bir konusmanin mesajlarini getir.
    Kronolojik sirada (created_at ASC), varsayilan 50 mesaj.
    """
    conversation = _get_user_conversation(conversation_id, current_user, db)

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content,
            "tool_calls": msg.tool_calls,
            "tool_call_id": msg.tool_call_id,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        for msg in messages
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Konusmayi ve bagli tum mesajlari sil.
    Cascade delete model relationship'te tanimli.
    """
    conversation = _get_user_conversation(conversation_id, current_user, db)

    db.delete(conversation)
    db.commit()
    logger.info(
        "Konusma silindi: %s (kullanici: %s)", conversation_id, current_user.id
    )

    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Export Downloads — dosya indirme endpoint'i
# ---------------------------------------------------------------------------


@router.get("/exports/{file_id}")
async def download_export(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Olusturulan export dosyasini indir."""
    from app.services.ai_tools.export_tools import get_export_file

    file_info = get_export_file(file_id)
    if not file_info:
        raise HTTPException(
            status_code=404, detail="Dosya bulunamadi veya suresi dolmus"
        )

    return Response(
        content=file_info["data"],
        media_type=file_info["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{file_info["filename"]}"',
        },
    )
