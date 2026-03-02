# Agentic Chat Streaming Upgrade — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Mevcut kara kutu chat'i SSE streaming + görünür tool adımları + sayfa bağlamı inject eden Notion/Particle benzeri bir agentic chat'e yükselt.

**Architecture:** FastAPI `StreamingResponse` ile yeni `/api/ai/chat/stream` SSE endpoint yazılır. Mevcut tool registry (`registry.py`) dokunulmadan kalır — sadece yeni bir `ai_streaming_service.py` servisi tool loop'u `AsyncGenerator` olarak sarar. Frontend `fetch()` + `ReadableStream` ile token-by-token render eder; tool adımları ayrı event olarak gelir ve `ToolSteps` component'inde gösterilir.

**Tech Stack:** FastAPI StreamingResponse, OpenAI streaming API (`stream=True`), React ReadableStream, react-markdown

---

## Ön Koşullar

```bash
cd /Users/projectx/Desktop/marketpulse

# Frontend bağımlılığı kontrol
cat frontend/package.json | grep react-markdown
# Yoksa: cd frontend && npm install react-markdown
```

---

## Task 1: Backend — Streaming Service

**Files:**
- Create: `backend/app/services/ai_streaming_service.py`

**Step 1: Dosyayı oluştur**

```python
# backend/app/services/ai_streaming_service.py
"""
AI Chat Streaming Service — SSE event'leri yield eden streaming chat loop.
Mevcut ai_chat_service.py'den bağımsız; tool registry'yi değiştirmez.
"""

import json
import logging
from typing import AsyncGenerator
from uuid import uuid4
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User

logger = logging.getLogger(__name__)

# Her tool için kullanıcıya gösterilecek Türkçe etiket
TOOL_LABELS: dict[str, str] = {
    "get_price_alerts": "Fiyat alarmları kontrol ediliyor...",
    "compare_seller_prices": "Satıcı fiyatları karşılaştırılıyor...",
    "get_product_insights": "Ürün fiyat geçmişi alınıyor...",
    "calculate_profitability": "Kârlılık hesaplanıyor...",
    "search_keyword_analysis": "Keyword analizi yapılıyor...",
    "get_portfolio_summary": "Portfolio özeti hazırlanıyor...",
    "add_sku_to_monitor": "SKU izleme listesine ekleniyor...",
    "add_competitor": "Rakip ekleniyor...",
    "set_price_alert": "Fiyat alarmı ayarlanıyor...",
    "start_keyword_search": "Keyword araması başlatılıyor...",
}

BASE_SYSTEM_PROMPT = """Sen MarketPulse AI asistanısın. Türk e-ticaret pazaryerlerinde (Hepsiburada, Trendyol)
ürün fiyat takibi, rakip analizi ve kârlılık hesaplama konularında yardımcı oluyorsun.

Kurallar:
- Türkçe yanıt ver
- Fiyatları TL cinsinden göster
- Verilere dayalı öneriler sun
- Kullanıcının kendi verisini kullan (tool'lar ile eriş)
- Emin olmadığın konularda tool kullan, tahmin yapma
- Kısa ve öz yanıtlar ver
- Markdown kullan: **bold**, listeler, tablo
"""


def _build_system_prompt(page_context: dict | None) -> str:
    """Base prompt + sayfa bağlamını birleştir."""
    if not page_context:
        return BASE_SYSTEM_PROMPT

    lines = ["\n[Mevcut Sayfa Bağlamı]"]
    page = page_context.get("page", "")
    if page:
        page_labels = {
            "price_monitor": "Fiyat İzleme",
            "dashboard": "Dashboard",
            "category_explorer": "Kategori Keşif",
            "competitors": "Rakip Takibi",
        }
        lines.append(f"Sayfa: {page_labels.get(page, page)}")
    if page_context.get("product_name"):
        product_line = f"İzlenen ürün: {page_context['product_name']}"
        if page_context.get("sku"):
            product_line += f" (SKU: {page_context['sku']})"
        lines.append(product_line)
    if page_context.get("product_id"):
        lines.append(f"Ürün ID: {page_context['product_id']}")

    return BASE_SYSTEM_PROMPT + "\n".join(lines)


def _sse(event_type: str, data: dict) -> str:
    """SSE formatında string üret."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class AIChatStreamingService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None and settings.OPENAI_API_KEY:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def stream_chat(
        self,
        user: User,
        conversation_id: str,
        message: str,
        page_context: dict | None,
        db: Session,
    ) -> AsyncGenerator[str, None]:
        """
        SSE event stream yield eder:
          event: tool_start  {"name": str, "label": str}
          event: tool_done   {"name": str, "summary": str}
          event: token       {"content": str}
          event: done        {}
          event: error       {"message": str}
        """
        if not self.client:
            yield _sse("error", {"message": "AI servisi yapılandırılmamış."})
            return

        from app.services.ai_tools.registry import TOOL_DEFINITIONS, execute_tool
        from app.db.models import ChatConversation, ChatMessage

        # --- Conversation yönet ---
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

        user_msg = ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        db.add(user_msg)
        db.flush()

        # --- Mesaj geçmişi ---
        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        messages = [{"role": "system", "content": _build_system_prompt(page_context)}]
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

        # --- Tool calling + streaming loop ---
        final_content = ""
        max_iterations = 5

        try:
            for _ in range(max_iterations):
                # Tool calling aşaması: streaming=False (tool calls text olmadığı için)
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=1000,
                    stream=False,  # Tool phase: non-streaming
                )

                choice = response.choices[0]

                if choice.finish_reason == "tool_calls":
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

                    for tc in choice.message.tool_calls:
                        tool_name = tc.function.name
                        label = TOOL_LABELS.get(tool_name, f"{tool_name} çalışıyor...")

                        # Frontend'e "tool başladı" event'i gönder
                        yield _sse("tool_start", {"name": tool_name, "label": label})

                        args = json.loads(tc.function.arguments)
                        result = await execute_tool(tool_name, args, str(user.id), db)
                        result_str = json.dumps(result, ensure_ascii=False, default=str)

                        # Özet çıkar (ilk 100 karakter)
                        summary = _extract_summary(result, tool_name)
                        yield _sse("tool_done", {"name": tool_name, "summary": summary})

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
                    # Final response: streaming=True ile token'ları yield et
                    stream = self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1000,
                        stream=True,
                    )

                    for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            final_content += delta.content
                            yield _sse("token", {"content": delta.content})

                    break  # Loop bitti

            # DB'ye kaydet
            assistant_final = ChatMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=final_content,
            )
            db.add(assistant_final)

            # Conversation title
            if len(history) <= 1:
                conversation.title = message[:50]

            db.commit()
            yield _sse("done", {})

        except Exception as e:
            logger.error(f"Streaming chat hatası: {e}")
            db.rollback()
            yield _sse("error", {"message": "Yanıt oluşturulamadı. Lütfen tekrar deneyin."})


def _extract_summary(result: dict, tool_name: str) -> str:
    """Tool sonucundan kısa özet çıkar."""
    if isinstance(result, dict):
        if "hata" in result:
            return f"Hata: {result['hata'][:60]}"
        # Tool'a özgü özet mantıkları
        if tool_name == "get_price_alerts":
            count = len(result.get("alerts", []))
            return f"{count} aktif alarm bulundu"
        if tool_name == "get_portfolio_summary":
            count = result.get("total_products", 0)
            return f"{count} ürün bulundu"
        if tool_name == "compare_seller_prices":
            sellers = result.get("sellers", [])
            return f"{len(sellers)} satıcı karşılaştırıldı"
        if tool_name == "calculate_profitability":
            margin = result.get("margin_percent", "")
            return f"Kâr marjı: %{margin}" if margin else "Hesaplama tamamlandı"
    return "Tamamlandı"


ai_streaming_service = AIChatStreamingService()
```

**Step 2: Sözdizimi kontrolü**

```bash
cd /Users/projectx/Desktop/marketpulse/backend
python -c "from app.services.ai_streaming_service import ai_streaming_service; print('OK')"
```

Beklenen çıktı: `OK`

**Step 3: Commit**

```bash
git add backend/app/services/ai_streaming_service.py
git commit -m "feat: add ai streaming service with SSE events and page context"
```

---

## Task 2: Backend — Streaming Route

**Files:**
- Create: `backend/app/api/ai_streaming_routes.py`
- Modify: `backend/app/api/__init__.py`

**Step 1: Route dosyasını oluştur**

```python
# backend/app/api/ai_streaming_routes.py
"""SSE streaming endpoint — /api/ai/chat/stream"""

from uuid import uuid4
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.services.ai_streaming_service import ai_streaming_service
from app.api._shared import get_current_user

router = APIRouter(prefix="/api/ai", tags=["AI Streaming"])


class ChatStreamRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    page_context: dict | None = None
    # page_context örnek:
    # {
    #   "page": "price_monitor",        # veya "dashboard", "category_explorer"
    #   "product_id": "uuid-string",    # opsiyonel
    #   "sku": "PROD-123",              # opsiyonel
    #   "product_name": "Sony XM5"      # opsiyonel
    # }


@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    SSE stream döndürür.
    Event tipleri: tool_start, tool_done, token, done, error
    """
    conversation_id = request.conversation_id or str(uuid4())

    # page_context field'larını sanitize et (XSS / prompt injection önlemi)
    safe_context = _sanitize_context(request.page_context)

    async def generate():
        async for event in ai_streaming_service.stream_chat(
            user=current_user,
            conversation_id=conversation_id,
            message=request.message,
            page_context=safe_context,
            db=db,
        ):
            yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx buffering'i kapat
            "X-Conversation-Id": conversation_id,
        },
    )


def _sanitize_context(ctx: dict | None) -> dict | None:
    """page_context field'larını kısalt ve güvenli yap."""
    if not ctx:
        return None
    allowed_keys = {"page", "product_id", "sku", "product_name"}
    return {
        k: str(v)[:200]  # Max 200 karakter, string'e çevir
        for k, v in ctx.items()
        if k in allowed_keys
    }
```

**Step 2: `__init__.py`'ye register et**

`backend/app/api/__init__.py` dosyasını aç. Mevcut import'ların sonuna şunu ekle:

```python
from app.api.ai_streaming_routes import router as ai_streaming_router
# ... (diğer router'lar)
app.include_router(ai_streaming_router)
```

> Not: `__init__.py` veya `main.py` nasıl çalışıyorsa ona göre register et. Mevcut `ai_routes` nasıl eklenmişse aynı pattern'ı kullan.

**Step 3: Endpoint'i test et (curl)**

Backend çalışırken:

```bash
curl -X POST http://localhost:8000/api/ai/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"message": "Merhaba"}' \
  --no-buffer
```

Beklenen: SSE event'leri satır satır görünür:
```
event: token
data: {"content": "Merhaba"}

event: token
data: {"content": "! Nasıl"}

event: done
data: {}
```

**Step 4: Commit**

```bash
git add backend/app/api/ai_streaming_routes.py backend/app/api/__init__.py
git commit -m "feat: add SSE streaming endpoint /api/ai/chat/stream"
```

---

## Task 3: Frontend — useChatContext Hook

**Files:**
- Create: `frontend/src/hooks/useChatContext.ts`

**Step 1: Hook dosyasını oluştur**

```typescript
// frontend/src/hooks/useChatContext.ts
/**
 * Kullanıcının hangi sayfada / üründe olduğunu döndürür.
 * ChatPanel bunu page_context olarak API'ye gönderir.
 */

import { useLocation, useParams } from 'react-router-dom'

export interface PageContext {
  page: string
  product_id?: string
  sku?: string
  product_name?: string
}

export interface SuggestedPrompt {
  text: string
}

export function useChatContext(): {
  context: PageContext | null
  suggestions: SuggestedPrompt[]
} {
  const location = useLocation()
  const params = useParams()

  // Price Monitor — ürün detay sayfası
  if (location.pathname.includes('/price-monitor') && params.id) {
    return {
      context: {
        page: 'price_monitor',
        product_id: params.id,
      },
      suggestions: [
        { text: 'Bu üründe rakip var mı?' },
        { text: 'Fiyat eşiğimi nasıl ayarlamalıyım?' },
        { text: 'Son 7 günlük fiyat trendi nedir?' },
      ],
    }
  }

  // Price Monitor — liste sayfası
  if (location.pathname.includes('/price-monitor')) {
    return {
      context: { page: 'price_monitor' },
      suggestions: [
        { text: 'Hangi ürünlerimde fiyat alarmı var?' },
        { text: 'En çok fiyat değişen ürünim hangisi?' },
        { text: 'Portföyümün genel durumu nedir?' },
      ],
    }
  }

  // Dashboard
  if (location.pathname.includes('/dashboard')) {
    return {
      context: { page: 'dashboard' },
      suggestions: [
        { text: 'Bugün kaç alarm tetiklendi?' },
        { text: 'En riskli ürünüm hangisi?' },
        { text: 'En karlı ürünüm hangisi?' },
      ],
    }
  }

  // Category Explorer
  if (location.pathname.includes('/category')) {
    return {
      context: { page: 'category_explorer' },
      suggestions: [
        { text: 'Bu kategorideki ortalama fiyat nedir?' },
        { text: 'Hangi kategori daha kârlı?' },
      ],
    }
  }

  // Genel fallback
  return {
    context: null,
    suggestions: [
      { text: 'Fiyat alarmı olan ürünlerim hangileri?' },
      { text: 'En karlı ürünüm hangisi?' },
      { text: 'Rakiplerimin fiyat durumu nasıl?' },
    ],
  }
}
```

**Step 2: TypeScript kontrol**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend
npx tsc --noEmit 2>&1 | head -20
```

Hata yoksa devam.

**Step 3: Commit**

```bash
git add frontend/src/hooks/useChatContext.ts
git commit -m "feat: add useChatContext hook for page-aware chat"
```

---

## Task 4: Frontend — ToolSteps Component

**Files:**
- Create: `frontend/src/components/chat/ToolSteps.tsx`

**Step 1: Component oluştur**

```tsx
// frontend/src/components/chat/ToolSteps.tsx
/**
 * Chatbot'un tool çağrılarını görsel olarak gösterir.
 * Particle/Notion AI tarzı "thinking" indicator.
 */

interface ToolStep {
  name: string
  label: string
  status: 'running' | 'done'
  summary?: string
}

interface ToolStepsProps {
  steps: ToolStep[]
}

export default function ToolSteps({ steps }: ToolStepsProps) {
  if (steps.length === 0) return null

  return (
    <div className="space-y-1 mb-2">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-text-muted">
          {step.status === 'running' ? (
            <svg
              className="w-3 h-3 animate-spin text-accent-primary flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          ) : (
            <svg
              className="w-3 h-3 text-green-500 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M5 13l4 4L19 7"
              />
            </svg>
          )}
          <span className="truncate">
            {step.status === 'running' ? step.label : (step.summary || step.label.replace('...', ''))}
          </span>
        </div>
      ))}
    </div>
  )
}

export type { ToolStep }
```

**Step 2: Commit**

```bash
git add frontend/src/components/chat/ToolSteps.tsx
git commit -m "feat: add ToolSteps component for visible reasoning"
```

---

## Task 5: Frontend — ChatPanel Streaming Upgrade

**Files:**
- Modify: `frontend/src/components/ChatPanel.tsx`

Bu en büyük değişiklik. Mevcut dosyayı tamamen değiştir:

**Step 1: react-markdown kontrol et**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend
cat package.json | grep react-markdown
```

Yoksa:
```bash
npm install react-markdown
```

**Step 2: ChatPanel.tsx'i güncelle**

Mevcut dosyayı aşağıdaki ile değiştir:

```tsx
// frontend/src/components/ChatPanel.tsx
import { useState, useRef, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import api from '../services/client'
import ToolSteps, { type ToolStep } from './chat/ToolSteps'
import { useChatContext } from '../hooks/useChatContext'

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolSteps?: ToolStep[]
  isStreaming?: boolean
  created_at?: string
}

interface Conversation {
  id: string
  title: string
  updated_at: string
}

export default function ChatPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Sayfa bağlamı ve önerilen promptlar
  const { context: pageContext, suggestions } = useChatContext()

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const loadConversations = async () => {
    try {
      const { data } = await api.get('/api/ai/conversations')
      setConversations(data)
    } catch {
      // Conversations endpoint may not be available yet
    }
  }

  const loadConversation = async (convId: string) => {
    try {
      const { data } = await api.get(`/api/ai/conversations/${convId}/messages`)
      setMessages(data)
      setConversationId(convId)
      setShowHistory(false)
    } catch {
      toast.error('Sohbet yüklenemedi')
    }
  }

  const startNewChat = () => {
    setMessages([])
    setConversationId(null)
    setShowHistory(false)
  }

  const sendMessage = async (overrideText?: string) => {
    const trimmed = (overrideText || input).trim()
    if (!trimmed || loading) return

    const userMessage: Message = { role: 'user', content: trimmed }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    // Boş assistant mesajı ekle — streaming doldurur
    const assistantIndex = messages.length + 1  // user msg index + 1
    setMessages(prev => [
      ...prev,
      { role: 'assistant', content: '', toolSteps: [], isStreaming: true },
    ])

    try {
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || ''

      const response = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: trimmed,
          conversation_id: conversationId,
          page_context: pageContext,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      // Conversation ID'yi header'dan al
      const newConvId = response.headers.get('X-Conversation-Id')
      if (newConvId) setConversationId(newConvId)

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let currentEvent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              setMessages(prev => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                if (!last || last.role !== 'assistant') return prev

                if (currentEvent === 'tool_start') {
                  const newStep: ToolStep = {
                    name: data.name,
                    label: data.label,
                    status: 'running',
                  }
                  return [
                    ...updated.slice(0, -1),
                    { ...last, toolSteps: [...(last.toolSteps || []), newStep] },
                  ]
                }

                if (currentEvent === 'tool_done') {
                  const steps = (last.toolSteps || []).map(s =>
                    s.name === data.name
                      ? { ...s, status: 'done' as const, summary: data.summary }
                      : s
                  )
                  return [...updated.slice(0, -1), { ...last, toolSteps: steps }]
                }

                if (currentEvent === 'token') {
                  return [
                    ...updated.slice(0, -1),
                    { ...last, content: last.content + data.content },
                  ]
                }

                if (currentEvent === 'done') {
                  return [...updated.slice(0, -1), { ...last, isStreaming: false }]
                }

                if (currentEvent === 'error') {
                  return [
                    ...updated.slice(0, -1),
                    { ...last, content: data.message, isStreaming: false },
                  ]
                }

                return prev
              })
            } catch {
              // JSON parse hatası — satırı atla
            }
          }
        }
      }
    } catch (err) {
      toast.error('Yanıt alınamadı', { id: 'chat-error' })
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last?.role === 'assistant') {
          updated[updated.length - 1] = {
            ...last,
            content: 'Bir hata oluştu. Lütfen tekrar deneyin.',
            isStreaming: false,
          }
        }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const togglePanel = () => {
    setIsOpen(prev => !prev)
    if (!isOpen) loadConversations()
  }

  return (
    <>
      {/* Floating Chat Button */}
      <button
        onClick={togglePanel}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-accent-primary text-white shadow-lg hover:bg-accent-primary/90 transition-all flex items-center justify-center"
        aria-label="AI Asistan"
      >
        {isOpen ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        )}
      </button>

      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-[420px] max-h-[640px] rounded-xl shadow-2xl border border-[var(--surface-border)] bg-[var(--surface-base)] flex flex-col overflow-hidden animate-fade-in">

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--surface-border)] bg-[var(--surface-raised)]">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-accent-primary/10 flex items-center justify-center">
                <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                </svg>
              </div>
              <div>
                <span className="font-semibold text-text-primary text-sm">MarketPulse AI</span>
                {pageContext && (
                  <div className="text-[10px] text-accent-primary">
                    {pageContext.product_name
                      ? `📍 ${pageContext.product_name}`
                      : `📍 ${pageContext.page}`}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => { setShowHistory(!showHistory); if (!showHistory) loadConversations() }}
                className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] text-text-muted transition-colors"
                title="Sohbet geçmişi"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
              <button
                onClick={startNewChat}
                className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] text-text-muted transition-colors"
                title="Yeni sohbet"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
          </div>

          {/* History Panel */}
          {showHistory && (
            <div className="border-b border-[var(--surface-border)] max-h-48 overflow-y-auto">
              {conversations.length === 0 ? (
                <div className="p-4 text-center text-text-muted text-xs">Henüz sohbet yok</div>
              ) : (
                conversations.map(conv => (
                  <button
                    key={conv.id}
                    onClick={() => loadConversation(conv.id)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-[var(--surface-hover)] transition-colors border-b border-[var(--surface-border)] last:border-b-0 ${conversationId === conv.id ? 'bg-accent-primary/5' : ''}`}
                  >
                    <div className="text-text-primary truncate text-xs">{conv.title}</div>
                    <div className="text-text-muted text-[10px] mt-0.5">
                      {new Date(conv.updated_at).toLocaleDateString('tr-TR')}
                    </div>
                  </button>
                ))
              )}
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[300px] max-h-[440px]">

            {/* Empty State */}
            {messages.length === 0 && (
              <div className="text-center py-6">
                <div className="w-12 h-12 rounded-full bg-accent-primary/10 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                  </svg>
                </div>
                <p className="text-text-muted text-sm font-medium">MarketPulse AI</p>
                <p className="text-text-muted text-xs mt-1">
                  {pageContext?.product_name
                    ? `${pageContext.product_name} hakkında soru sorun`
                    : 'Fiyat takibi, rakip analizi ve karlılık hakkında sorun'}
                </p>
                {/* Sayfa bazlı önerilen promptlar */}
                <div className="mt-4 space-y-2">
                  {suggestions.map(s => (
                    <button
                      key={s.text}
                      onClick={() => sendMessage(s.text)}
                      className="block w-full text-left px-3 py-2 rounded-lg bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-text-primary text-xs transition-colors"
                    >
                      {s.text}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message List */}
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[90%] rounded-xl px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-accent-primary text-white'
                      : 'bg-[var(--surface-raised)] text-text-primary border border-[var(--surface-border)]'
                  }`}
                >
                  {/* Tool Steps (sadece assistant için) */}
                  {msg.role === 'assistant' && msg.toolSteps && msg.toolSteps.length > 0 && (
                    <ToolSteps steps={msg.toolSteps} />
                  )}

                  {/* Message Content */}
                  {msg.role === 'assistant' ? (
                    <>
                      {msg.content ? (
                        <ReactMarkdown
                          className="prose prose-sm max-w-none text-text-primary [&_p]:mb-1 [&_ul]:mb-1 [&_li]:mb-0.5 [&_strong]:font-semibold [&_code]:bg-[var(--surface-hover)] [&_code]:px-1 [&_code]:rounded"
                        >
                          {msg.content}
                        </ReactMarkdown>
                      ) : msg.isStreaming ? null : (
                        <span className="text-text-muted">...</span>
                      )}
                      {/* Streaming cursor */}
                      {msg.isStreaming && msg.content && (
                        <span className="inline-block w-0.5 h-3.5 bg-accent-primary ml-0.5 animate-pulse" />
                      )}
                    </>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>
              </div>
            ))}

            {/* Global loading (tool phase, henüz token yok) */}
            {loading && messages[messages.length - 1]?.isStreaming &&
              !messages[messages.length - 1]?.content &&
              (messages[messages.length - 1]?.toolSteps?.length ?? 0) === 0 && (
              <div className="flex justify-start">
                <div className="bg-[var(--surface-raised)] rounded-xl px-4 py-2 border border-[var(--surface-border)]">
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-[var(--surface-border)] bg-[var(--surface-raised)]">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Bir soru sorun..."
                rows={1}
                disabled={loading}
                className="flex-1 resize-none rounded-lg bg-[var(--surface-base)] border border-[var(--surface-border)] px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent-primary max-h-20 disabled:opacity-60"
                style={{ minHeight: '36px' }}
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || loading}
                className="p-2 rounded-lg bg-accent-primary text-white disabled:opacity-50 hover:bg-accent-primary/90 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
```

**Step 3: TypeScript kontrol**

```bash
cd /Users/projectx/Desktop/marketpulse/frontend
npx tsc --noEmit 2>&1 | head -30
```

Tip hatası varsa düzelt. Yaygın sorun: `useParams()` type — `const { id } = useParams<{ id: string }>()` yap.

**Step 4: Token'ı nereden alıyoruz?**

Mevcut projede auth token nasıl saklanıyor kontrol et:

```bash
grep -r "access_token\|localStorage\|token" /Users/projectx/Desktop/marketpulse/frontend/src/services/client.ts | head -10
```

Eğer `api` instance zaten header'ı ekleyip gönderiyorsa ve backend `Bearer` token'ı alıyorsa, `fetch` çağrısında da aynı token'ı kullanman gerekiyor. Mevcut `api` interceptor'una bak ve `fetch` call'unda aynı token'ı kullan.

**Step 5: Manuel test**

1. Dev server'ı başlat
2. Herhangi bir sayfaya git
3. Chat ikonuna tıkla
4. "Portföyümün durumu nedir?" yaz
5. Beklenen:
   - Tool adımları "Portfolio özeti hazırlanıyor..." → "✓ X ürün bulundu" görünür
   - Yanıt token token akar
   - Markdown bold/liste render edilir
   - Panel header'da sayfa adı görünür

**Step 6: Commit**

```bash
git add frontend/src/components/ChatPanel.tsx
git commit -m "feat: upgrade ChatPanel with SSE streaming, tool visibility, page context, markdown"
```

---

## Task 6: Entegrasyon Testi

**Step 1: Backend health check**

```bash
cd /Users/projectx/Desktop/marketpulse/backend
# Test: streaming endpoint varlığı
python -c "
from app.api.ai_streaming_routes import router
routes = [r.path for r in router.routes]
print('Routes:', routes)
assert '/api/ai/chat/stream' in routes or any('stream' in r for r in routes)
print('OK')
"
```

**Step 2: Uçtan uca test (curl)**

```bash
# Token al (mevcut auth endpointine göre)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d "username=test@test.com&password=test123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Streaming test
curl -X POST http://localhost:8000/api/ai/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "Merhaba, portföy özetimi göster"}' \
  --no-buffer -s
```

Beklenen çıktı:
```
event: tool_start
data: {"name": "get_portfolio_summary", "label": "Portfolio özeti hazırlanıyor..."}

event: tool_done
data: {"name": "get_portfolio_summary", "summary": "X ürün bulundu"}

event: token
data: {"content": "Merhaba!"}

...

event: done
data: {}
```

**Step 3: Eski endpoint geriye uyumluluk**

```bash
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "Merhaba", "conversation_id": null}' -s | python3 -m json.tool
```

Beklenen: Eski format hâlâ çalışıyor.

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: agentic chat streaming upgrade complete"
```

---

## Sorun Giderme

### SSE stream gelmiyor / boş

- Nginx/proxy `proxy_buffering off;` ve `X-Accel-Buffering: no` ayarlı mı?
- `StreamingResponse` `media_type="text/event-stream"` var mı?
- Tarayıcı geliştirici araçları Network sekmesinde `chat/stream` isteğine bak → `EventStream` sekmesi

### Token event'leri birleşiyor

- `decoder.decode(value, { stream: true })` kullan
- Birden fazla event aynı chunk'ta gelebilir — `\n\n` ile split et

### TypeScript `useParams` type hatası

```typescript
const { id } = useParams<{ id?: string }>()
```

### ReactMarkdown import hatası

```bash
cd frontend && npm install react-markdown
# package.json'da "react-markdown": "^9.x.x" görünmeli
```

### Auth token `fetch`'te eksik

`api` client'ının interceptor'u incele, token'ı nereden aldığını bul ve aynı kaynağı kullan.

---

## Özet

| Task | Dosya | Süre |
|------|-------|------|
| 1 | ai_streaming_service.py | ~45 dk |
| 2 | ai_streaming_routes.py + register | ~20 dk |
| 3 | useChatContext.ts | ~15 dk |
| 4 | ToolSteps.tsx | ~15 dk |
| 5 | ChatPanel.tsx upgrade | ~45 dk |
| 6 | Entegrasyon testi | ~30 dk |
| **Toplam** | | **~3 saat** |
