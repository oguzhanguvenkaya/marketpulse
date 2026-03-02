# MarketPulse Agentic Chat Upgrade — Design Dokümanı

**Tarih**: 2026-03-01
**Durum**: Onaylandı
**Kapsam**: Chat upgrade (Streaming + Tool Visibility + Page Context)
**Tahmini Süre**: 5-7 gün

---

## 1. Bağlam ve Motivasyon

### Mevcut Durum

`ai_chat_service.py` iyi bir temel sağlıyor:
- OpenAI GPT-4o-mini + function calling loop ✅
- 10 tool tanımlı (fiyat, kârlılık, portfolio, action) ✅
- Conversation history (son 20 mesaj) ✅

**Eksikler:**
- Streaming yok → kullanıcı yanıtın tamamını bekliyor
- Tool adımları görünmüyor → kara kutu deneyimi
- Sayfa bağlamı yok → "bu ürün" dediğinde chatbot bilmiyor
- Markdown render yok → bold, liste, tablo ham text olarak görünüyor

### Hedef Deneyim

```
Kullanıcı: "En karlı ürünüm hangisi?"

Chat UI:
  ┌─────────────────────────────────────┐
  │ 🔍 Portfolio özeti alınıyor...      │  ← thinking step
  │ ✓ 12 ürün bulundu                   │
  │ 🔍 Kârlılık hesaplanıyor...         │  ← thinking step
  │ ✓ Hesaplama tamamlandı              │
  │                                     │
  │ En yüksek kârlılığınız **Sony       │  ← streaming tokens
  │ WH-1000XM5** ile %34 marjinle...    │
  └─────────────────────────────────────┘
```

---

## 2. Araştırma Notları

### AMA-Bench Makalesi Değerlendirmesi

AMA-Agent (arXiv:2602.22769v1) iki mekanizma öneriyor:
- **Causality Graph**: Her action-observation çiftinden durum + nedensellik kenarı
- **Tool-Augmented Retrieval**: Embedding → graph traversal → keyword search

**MarketPulse için uygulama değerlendirmesi:**

| Senaryo | Değer | Notlar |
|---------|-------|--------|
| Scraping hata hafızası | ✅ Yüksek | 403 hatalarında hangi workaround işe yaradı? |
| Fiyat anomali nedensellik | ✅ Yüksek | Düşüş gerçek mi, satıcı mı değişti? |
| Kategori strateji hafızası | ✅ Orta | Hangi kategori hangi scraping stratejisi |
| **User-facing chat** | ❌ Yok | AMA-Agent makine-trajektori için tasarlanmış, kullanıcı dialogu için değil |

**Sonuç**: AMA-Agent scraping pipeline'ı için gelecekte değerli (ayrı track). Chat upgrade için gereksiz.

### SSE vs WebSocket

Chat streaming için SSE seçildi:
- Tek yön yeterli (sunucu → istemci)
- HTTP üstünde çalışır, load balancer uyumlu
- Otomatik reconnect
- WebSocket: çift yön gerçek zamanlı gerektiğinde (canlı dashboard)

### Neden LangChain/CrewAI/Crawl4AI Değil?

Mevcut `ai_chat_service.py` zaten doğru şeyi yapıyor — OpenAI function calling loop:

```
Mevcut:  200 satır, 0 dependency, tam debuggable
LangChain: 200 satır + 50MB+ library + 15 abstraction katmanı
            + breaking change riski + platform-specific bug'lar
```

**CrewAI**: Multi-agent orchestration — birden fazla otonom agent gerektiğinde.
**Crawl4AI**: Web scraping için — chat'le ilgisi yok.
**Particle/Notion AI**: OpenAI API + SSE streaming + custom context injection kullanıyor. LangChain kullanmıyor.

---

## 3. Seçilen Yaklaşım: B (Streaming + Tool Visibility + Page Context)

### Mimari Genel Bakış

```
Mevcut:
  Frontend → POST /api/ai/chat → (tool loop, ~3-5sn) → response string

Yeni:
  Frontend → POST /api/ai/chat/stream → SSE stream:
    event: tool_start  {"name": "compare_seller_prices", "label": "Satıcı fiyatları karşılaştırılıyor..."}
    event: tool_done   {"name": "compare_seller_prices", "summary": "4 satıcı bulundu"}
    event: token       {"content": "Rakibiniz TechShop, sizi "}
    event: token       {"content": "12 TL altına almış."}
    event: done        {}
    event: error       {"message": "..."} (hata durumunda)
```

---

## 4. Backend Design

### 4.1 Yeni: `ai_streaming_service.py`

```python
class AIChatStreamingService:
    async def stream_chat(
        self,
        user: User,
        conversation_id: str,
        message: str,
        page_context: dict | None,
        db: Session,
    ) -> AsyncGenerator[str, None]:
        """
        SSE formatında yield eder:
        - tool_start / tool_done events
        - token events (streaming text)
        - done / error events
        """
        # 1. Conversation yönet (mevcut mantık aynı)
        # 2. Page context'i system prompt'a inject et
        # 3. OpenAI streaming=True ile çağır
        # 4. tool_calls gelirse: tool_start yield → execute → tool_done yield
        # 5. Text token'ları yield et
        # 6. DB'ye kaydet (done sonrası)
```

**Page Context Injection:**

```python
SYSTEM_PROMPT_BASE = """Sen MarketPulse AI asistanısın..."""

def build_system_prompt(page_context: dict | None) -> str:
    if not page_context:
        return SYSTEM_PROMPT_BASE

    context_block = f"""
[Mevcut Sayfa Bağlamı]
Sayfa: {page_context.get('page', 'genel')}
"""
    if page_context.get('product_name'):
        context_block += f"İzlenen ürün: {page_context['product_name']}"
    if page_context.get('sku'):
        context_block += f" (SKU: {page_context['sku']})"

    return SYSTEM_PROMPT_BASE + context_block
```

**SSE Event Format:**

```python
def sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

# Kullanım:
yield sse_event("tool_start", {"name": "get_price_alerts", "label": "Fiyat alarmları kontrol ediliyor..."})
yield sse_event("tool_done", {"name": "get_price_alerts", "summary": "3 aktif alarm"})
yield sse_event("token", {"content": "Merhaba, "})
yield sse_event("done", {})
```

### 4.2 Yeni: `ai_streaming_routes.py`

```python
@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    async def generate():
        async for event in streaming_service.stream_chat(
            user=current_user,
            conversation_id=request.conversation_id or str(uuid4()),
            message=request.message,
            page_context=request.page_context,
            db=db,
        ):
            yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Nginx buffering kapat
        }
    )
```

**Request Schema:**

```python
class ChatStreamRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    page_context: dict | None = None
    # page_context örnek:
    # {
    #   "page": "price_monitor",
    #   "product_id": "uuid",
    #   "sku": "SNY-XM5",
    #   "product_name": "Sony WH-1000XM5"
    # }
```

### 4.3 Tool Label Mapping

```python
TOOL_LABELS = {
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
```

---

## 5. Frontend Design

### 5.1 Yeni State Yapısı

```typescript
interface ToolStep {
  name: string
  label: string
  status: 'running' | 'done'
  summary?: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolSteps?: ToolStep[]  // YENİ
  isStreaming?: boolean   // YENİ
  created_at?: string
}
```

### 5.2 Streaming Consumer

```typescript
const sendMessage = async () => {
  // ...
  const response = await fetch('/api/ai/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ message: trimmed, conversation_id: conversationId, page_context: pageContext }),
  })

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()

  // Boş assistant mesajı ekle (streaming için)
  const assistantMsgIndex = messages.length
  setMessages(prev => [...prev, { role: 'assistant', content: '', toolSteps: [], isStreaming: true }])

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value)
    const lines = text.split('\n')

    for (const line of lines) {
      if (line.startsWith('event: ')) currentEvent = line.slice(7)
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6))

        if (currentEvent === 'tool_start') {
          // ToolStep ekle (running)
        } else if (currentEvent === 'tool_done') {
          // ToolStep güncelle (done)
        } else if (currentEvent === 'token') {
          // content'e append et
        } else if (currentEvent === 'done') {
          // isStreaming = false
        }
      }
    }
  }
}
```

### 5.3 ToolSteps Component

```tsx
function ToolSteps({ steps }: { steps: ToolStep[] }) {
  return (
    <div className="space-y-1 mb-2">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-text-muted">
          {step.status === 'running' ? (
            <Spinner className="w-3 h-3 animate-spin text-accent-primary" />
          ) : (
            <CheckIcon className="w-3 h-3 text-green-500" />
          )}
          <span>{step.status === 'running' ? step.label : step.summary || step.label.replace('...', '')}</span>
        </div>
      ))}
    </div>
  )
}
```

### 5.4 Page Context Hook

```typescript
// hooks/useChatContext.ts
export function useChatContext(): PageContext | null {
  const location = useLocation()
  const { productId } = useParams()

  if (location.pathname.startsWith('/price-monitor') && productId) {
    return { page: 'price_monitor', product_id: productId, ... }
  }
  if (location.pathname.startsWith('/dashboard')) {
    return { page: 'dashboard' }
  }
  return null
}
```

### 5.5 Sayfa Bazlı Önerilen Promptlar

| Sayfa | Önerilen Promptlar |
|-------|-------------------|
| Price Monitor (ürün) | "Bu üründe rakip var mı?", "Fiyat eşiğimi ayarla", "Son 7 günlük trend nedir?" |
| Price Monitor (liste) | "Hangi ürünlerimde alarm var?", "En çok değişen fiyat hangisi?" |
| Dashboard | "Bugün kaç alarm tetiklendi?", "En riskli ürünüm hangisi?" |
| Category Explorer | "Bu kategorideki ortalama fiyat nedir?" |
| Genel | "Portföyümün durumu nasıl?", "En karlı ürünüm hangisi?" |

### 5.6 Markdown Render

Mevcut `whitespace-pre-wrap` yerine `react-markdown` (zaten projede mevcut olabilir):

```tsx
import ReactMarkdown from 'react-markdown'

// Message render:
<ReactMarkdown className="prose prose-sm max-w-none text-text-primary">
  {msg.content}
</ReactMarkdown>
```

---

## 6. Değişmeyen Şeyler

- `ai_chat_service.py` — mevcut senkron endpoint korunuyor (geriye uyumluluk)
- `registry.py` — tool tanımları değişmez
- Tool implementation dosyaları — değişmez
- DB modelleri — `ChatConversation`, `ChatMessage` değişmez
- Conversation history yönetimi — aynı mantık

---

## 7. Dosya Değişim Özeti

### Yeni Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `backend/app/services/ai_streaming_service.py` | Streaming chat loop (SSE yield) |
| `backend/app/api/ai_streaming_routes.py` | POST /api/ai/chat/stream endpoint |
| `frontend/src/hooks/useChatContext.ts` | Sayfa bağlamı hook |
| `frontend/src/components/chat/ToolSteps.tsx` | Tool adım göstergesi |

### Değiştirilen Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `frontend/src/components/ChatPanel.tsx` | Streaming consumer + ToolSteps + ReactMarkdown + page context |
| `backend/app/api/__init__.py` | ai_streaming_routes register |
| `frontend/src/components/ChatPanel.tsx` | Sayfa bazlı önerilen promptlar |

---

## 8. Bağımlılıklar

### Backend
- **Yeni yok** — FastAPI `StreamingResponse` mevcut, OpenAI streaming mevcut

### Frontend
- `react-markdown` — markdown render için (yoksa `npm install react-markdown`)
- Diğer her şey mevcut

---

## 9. Güvenlik Notları

- SSE endpoint auth middleware korunmalı (mevcut `get_current_user` Depends)
- `X-Accel-Buffering: no` header'ı Nginx için gerekli
- Stream sona ermeden DB commit yapılmamalı (partial write riski)
- Page context field'ları sanitize edilmeli (system prompt injection riski)

---

## 10. Test Edilecekler

- [ ] Normal mesaj: streaming token'ları geliyor mu?
- [ ] Tool calling: tool_start / tool_done event'leri doğru mu?
- [ ] Hata durumu: error event döndürülüyor mu?
- [ ] Page context: sistem prompt'a injection doğru mu?
- [ ] Conversation history: stream sonrası DB'ye kaydedildi mi?
- [ ] Timeout: uzun tool çağrısında stream kopmuyor mu?
- [ ] Geriye uyumluluk: eski `/api/ai/chat` endpoint hâlâ çalışıyor mu?

---

## 11. Gelecek (Bu Planda Değil)

- **AMA-Agent Scraping Hafızası**: Scraping pipeline'a trajectory logger (ayrı track, ~2 hafta)
- **Proaktif Alerts**: Kullanıcı sormadan chatbot bildirim atar
- **Multi-turn Reasoning**: Birden fazla conversation context birleştirme
- **Voice Input**: Tarayıcı Speech API entegrasyonu
