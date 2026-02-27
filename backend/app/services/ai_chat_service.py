"""
AI Chat Service — OpenAI tool-calling ile kullanıcıya yardımcı olan chatbot.
"""

import json
import logging
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen MarketPulse AI asistanısın. Türk e-ticaret pazaryerlerinde (Hepsiburada, Trendyol)
ürün fiyat takibi, rakip analizi ve kârlılık hesaplama konularında yardımcı oluyorsun.

Kurallar:
- Türkçe yanıt ver
- Fiyatları TL cinsinden göster
- Verilere dayalı öneriler sun
- Kullanıcının kendi verisini kullan (tool'lar ile eriş)
- Emin olmadığın konularda tool kullan, tahmin yapma
- Kısa ve öz yanıtlar ver
"""


class AIChatService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None and settings.OPENAI_API_KEY:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def chat(
        self,
        user: User,
        conversation_id: str,
        message: str,
        db: Session,
    ) -> str:
        """Mesajı işle, tool calling ile yanıt üret."""
        if not self.client:
            return "AI servisi yapılandırılmamış. OPENAI_API_KEY ayarlanmalı."

        from app.services.ai_tools.registry import TOOL_DEFINITIONS, execute_tool
        from app.db.models import ChatConversation, ChatMessage

        # Conversation bul veya oluştur
        conversation = db.query(ChatConversation).filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user.id,
        ).first()

        if not conversation:
            conversation = ChatConversation(
                id=conversation_id,
                user_id=user.id,
                title=message[:50],
            )
            db.add(conversation)
            db.flush()

        # Kullanıcı mesajını kaydet
        user_msg = ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        db.add(user_msg)
        db.flush()

        # Mesaj geçmişini oluştur
        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history[-20:]:
            if msg.role == "tool":
                messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id,
                })
            elif msg.tool_calls:
                messages.append({
                    "role": msg.role,
                    "content": msg.content or "",
                    "tool_calls": msg.tool_calls,
                })
            else:
                messages.append({"role": msg.role, "content": msg.content})

        # OpenAI API çağrısı (tool calling loop)
        max_iterations = 5
        for _ in range(max_iterations):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=1000,
                )
            except Exception as e:
                logger.error(f"OpenAI API hatası: {e}")
                return "AI servisiyle iletişim kurulamadı. Lütfen tekrar deneyin."

            choice = response.choices[0]

            if choice.finish_reason == "tool_calls":
                # Tool call'ları çalıştır
                tool_calls_data = []
                for tc in choice.message.tool_calls:
                    tool_calls_data.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })

                # Assistant mesajını kaydet (tool calls ile)
                assistant_msg = ChatMessage(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=choice.message.content or "",
                    tool_calls=tool_calls_data,
                )
                db.add(assistant_msg)
                messages.append({
                    "role": "assistant",
                    "content": choice.message.content or "",
                    "tool_calls": tool_calls_data,
                })

                # Her tool'u çalıştır
                for tc in choice.message.tool_calls:
                    args = json.loads(tc.function.arguments)
                    result = await execute_tool(
                        tc.function.name, args, str(user.id), db
                    )
                    result_str = json.dumps(result, ensure_ascii=False, default=str)

                    tool_msg = ChatMessage(
                        conversation_id=conversation.id,
                        role="tool",
                        content=result_str,
                        tool_call_id=tc.id,
                    )
                    db.add(tool_msg)
                    messages.append({
                        "role": "tool",
                        "content": result_str,
                        "tool_call_id": tc.id,
                    })
            else:
                # Final response
                final_content = choice.message.content or ""
                assistant_msg = ChatMessage(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=final_content,
                )
                db.add(assistant_msg)
                db.commit()

                # Conversation title'ı güncelle
                if len(history) <= 1:
                    conversation.title = message[:50]
                    db.commit()

                return final_content

        db.commit()
        return "Üzgünüm, yanıt oluşturulamadı. Lütfen tekrar deneyin."


ai_chat_service = AIChatService()
