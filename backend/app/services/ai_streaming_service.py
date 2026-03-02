"""
AI Chat Streaming Service — SSE event'leri yield eden streaming chat loop.
Mevcut ai_chat_service.py'den bagimsiz; tool registry'yi degistirmez.
"""

import hashlib
import json
import logging
import re
import time
from typing import AsyncGenerator, Dict, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.db.models import User

logger = get_logger("ai.chat")

# Her tool icin kullaniciya gosterilecek Turkce etiket
TOOL_LABELS: Dict[str, str] = {
    "get_price_alerts": "Fiyat alarmlari kontrol ediliyor...",
    "compare_seller_prices": "Satici fiyatlari karsilastiriliyor...",
    "get_product_insights": "Urun fiyat gecmisi aliniyor...",
    "calculate_profitability": "Karlilik hesaplaniyor...",
    "search_keyword_analysis": "Keyword analizi yapiliyor...",
    "get_portfolio_summary": "Portfolio ozeti hazirlaniyor...",
    "search_products_by_name": "Urunler arasinda araniyor...",
    "add_sku_to_monitor": "SKU izleme listesine ekleniyor...",
    "add_competitor": "Rakip ekleniyor...",
    "set_price_alert": "Fiyat alarmi ayarlaniyor...",
    "start_keyword_search": "Keyword aramasi baslatiliyor...",
    "get_category_analysis": "Kategori analizi yapiliyor...",
    "get_product_descriptions": "Urun aciklamalari getiriliyor...",
    "analyze_product_descriptions": "Urun aciklamalari analiz ediliyor...",
    "export_data": "Dosya hazirlaniyor...",
}

# Veri degistiren (mutasyon yapan) action tool'lari
_ACTION_TOOLS = frozenset({
    "add_sku_to_monitor",
    "add_competitor",
    "set_price_alert",
    "start_keyword_search",
})

# Kullanicinin onay verdigi kabul edilen kisa explicit yanit pattern'lari
_CONFIRMATION_PATTERNS = re.compile(
    r"^\s*(evet|onayliyorum|onay|devam\s*et|uygula|tamam|ok|yes|onayla)\s*[.!]?\s*$",
    re.IGNORECASE,
)

BASE_SYSTEM_PROMPT = """Sen MarketPulse AI asistanisin. Turk e-ticaret pazaryerlerinde (Hepsiburada, Trendyol)
urun fiyat takibi, rakip analizi ve karlilik hesaplama konularinda yardimci oluyorsun.

Kurallar:
- Turkce yanit ver
- Fiyatlari TL cinsinden goster, binlik ayirac olarak nokta kullan (ornek: 1.299,90 ₺)
- Verilere dayali oneriler sun
- Kullanicinin kendi verisini kullan (tool'lar ile eris)
- Emin olmadigin konularda tool kullan, tahmin yapma
- Kisa ve oz yanitlar ver
- Markdown kullan: **bold**, listeler, tablo

Zengin Markdown Formatlama Kurallari:
- Birden fazla urun karsilastirirken MUTLAKA markdown tablosu kullan (| Sutun | ... | formatinda)
- Urun adi ve urun_url mevcut ise: [Urun Adi](urun_url) formatinda tiklanabilir link olustur
- ONEMLI: Tablo icine gorsel (![img](...)) KOYMA — gorseller tabloyu bozar. Gorselleri sadece tablo disinda, metin icinde kullan.
- Satici adi ve satici_url mevcut ise: [Satici Adi](satici_url) formatinda link olustur
- Fiyat sutunlarinda TL sembolunu kullan: 1.299,90 ₺
- Tablo sutun sirasini buna gore olustur: Sira | Urun | Fiyat | Satici | Puan
- gorsel veya URL alani None veya bos ise link ya da img ekleme
- Urun adlarini tabloda 60 karakterle kisalt

Tool kullanim kurallari:
- Her farkli kategori, urun veya veri kaynagi icin AYRI bir tool cagrisi yap
- Ayni parametrelerle ayni tool'u TEKRAR cagirma — zaten sonuc aldin
- Birden fazla kategori sorulursa her biri icin FARKLI category_name ile cagir
- Ornek: "sivi cila ve hizli cila" icin get_category_analysis'i 2 kez cagir: biri "Sivi Cila", digeri "Hizli Cila"
- Marka veya satici bazli analiz istendiginde get_category_analysis'in brand veya seller parametresini kullan
- get_product_insights icin product_id UUID olmali — SKU veya urun adi DEGIL. Once urun arayip ID bul.
- Kategori tarama verisinde urun aramak icin get_product_descriptions veya get_category_analysis kullan
- search_products_by_name SADECE izleme listesindeki (monitored) urunleri arar — kategori urunlerini aramak icin get_product_descriptions kullan

Urun karsilastirma kurallari:
- Bir urunden birden fazla varyant (boyut, hacim, adet) varsa, kullaniciya ONCE hangi varyantin karsilastirilacagini SOR
- Ornek: "WetCoat 500ml, 1000ml ve 4000ml secenekleri var. Hangisini karsilastirmak istersiniz?" diye sor
- Kullanici belirtmediyse ve karsilastirilan diger urunun boyutu belliyse, en yakin boyutu sec ve bunu belirt
- Karsilastirma yaparken mutlaka fiyat, hacim ve ml basi fiyat bilgisini de goster

Aksiyon onay kurallari:
- Veri DEGISTIREN tool'lari (add_sku_to_monitor, add_competitor, set_price_alert, start_keyword_search) cagirmadan ONCE kullaniciya ne yapacagini acikla ve onay iste
- Ornek: "HB12345 SKU'sunu Hepsiburada'da izleme listesine eklemek istiyorsunuz. Fiyat esigi 100 TL. Onayliyor musunuz?"
- Kullanici acik onay verene kadar (evet, tamam, onayla gibi) tool'u CAGIRMA
- Export islemi (export_data) icin onay gerekmez
"""


def _is_explicit_confirmation(message: str) -> bool:
    """
    Kullanicinin mesajinin acik bir onay olup olmadigini kontrol et.
    Sadece kisa/explicit yanitlar kabul edilir.
    Ilk istekteki 'ekle/ayarla' gibi imperative metinler onay SAYILMAZ.
    """
    return bool(_CONFIRMATION_PATTERNS.match(message.strip()))


def _build_system_prompt(page_context: Optional[dict]) -> str:
    """
    Base prompt + zengin sayfa baglamini birlestir.

    Yeni desteklenen field'lar:
      platform, category_name, session_id, merchant_id, seller_name, keyword, filters
    """
    if not page_context:
        return BASE_SYSTEM_PROMPT

    page_labels = {
        "price_monitor": "Fiyat Izleme",
        "dashboard": "Dashboard",
        "category_explorer": "Kategori Kesif",
        "competitors": "Rakip Takibi",
        "sellers": "Saticilar",
        "seller_detail": "Satici Detay",
        "keyword_search": "Keyword Arama",
    }

    platform_labels = {
        "hepsiburada": "Hepsiburada",
        "trendyol": "Trendyol",
        "web": "Web",
    }

    lines = ["\n[Mevcut Sayfa Baglami]"]

    page = page_context.get("page", "")
    if page:
        lines.append(f"Sayfa: {page_labels.get(page, page)}")

    platform = page_context.get("platform", "")
    if platform:
        lines.append(f"Platform: {platform_labels.get(platform, platform)}")

    # Urun bilgileri
    if page_context.get("product_name"):
        product_line = f"Izlenen urun: {page_context['product_name']}"
        if page_context.get("sku"):
            product_line += f" (SKU: {page_context['sku']})"
        lines.append(product_line)
    if page_context.get("product_id"):
        lines.append(f"Urun ID: {page_context['product_id']}")

    # Kategori
    if page_context.get("category_name"):
        lines.append(f"Aktif kategori: {page_context['category_name']}")

    # Keyword
    if page_context.get("keyword"):
        lines.append(f"Arama keyword: {page_context['keyword']}")

    # Satici bilgileri
    if page_context.get("seller_name"):
        lines.append(f"Satici: {page_context['seller_name']}")
    if page_context.get("merchant_id"):
        lines.append(f"Satici ID: {page_context['merchant_id']}")

    # Scrape session
    if page_context.get("session_id"):
        lines.append(f"Scrape session: {page_context['session_id']}")

    # Aktif filtreler
    filters = page_context.get("filters")
    if isinstance(filters, dict) and filters:
        filter_parts = []
        if filters.get("brand"):
            filter_parts.append(f"marka={filters['brand']}")
        if filters.get("seller"):
            filter_parts.append(f"satici={filters['seller']}")
        if filters.get("min_price") or filters.get("max_price"):
            price_range = f"{filters.get('min_price', '?')}-{filters.get('max_price', '?')} TL"
            filter_parts.append(f"fiyat={price_range}")
        if filter_parts:
            lines.append(f"Aktif filtreler: {', '.join(filter_parts)}")

    return BASE_SYSTEM_PROMPT + "\n".join(lines)


def _sse(event_type: str, data: dict) -> str:
    """SSE formatinda string uret."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _make_tool_call_key(tool_name: str, arguments_json: str) -> str:
    """
    Tool cagrisi icin tekil anahtar uret.
    Ayni tool + ayni arguman kombinasyonu ayni key'i dondurur.
    JSON key siralama farkliliklarina karsi normalize eder.
    """
    try:
        parsed = json.loads(arguments_json)
        normalized = json.dumps(parsed, sort_keys=True, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        normalized = arguments_json

    raw = f"{tool_name}:{normalized}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _truncate(text: str, max_len: int = 200) -> str:
    """Log icin metni kisalt."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... (+{len(text) - max_len} chars)"


def _trim_orphan_tool_messages(msgs: list) -> list:
    """
    Mesaj listesinin basindaki yetim tool/tool_calls mesajlarini at.

    OpenAI API kurali: 'tool' mesaji mutlaka bir onceki 'assistant'
    mesajinda 'tool_calls' olmasi gerekir. history[-20:] tool zincirini
    ortadan kesebilir; bu fonksiyon temiz bir sinir bulur.

    Ayrica tool_call_id'si olan tool mesajlarinin eslestirilmesi icin
    assistant(tool_calls) mesajindaki id'ler kontrol edilir.
    """
    if not msgs:
        return msgs

    # Bastan ileri dogru tara: ilk temiz mesaji bul
    # Temiz mesaj = "user" veya "assistant" (tool_calls OLMAYAN)
    start = 0
    for i, msg in enumerate(msgs):
        if msg.role == "tool":
            # Yetim tool mesaji — atla
            start = i + 1
            continue
        if msg.role == "assistant" and msg.tool_calls:
            # Bu assistant'in tool sonuclari da kesilmis olabilir
            # Sonraki mesajlarin hepsinin tool olup bu assistant'a
            # ait oldugundan emin olamayiz — guvenli atla
            start = i + 1
            continue
        # user veya sade assistant — temiz sinir
        break

    if start > 0:
        logger.info(
            "[CONTEXT_TRIM] %d yetim mesaj atildi (tool/tool_calls zinciri kesilmisti)",
            start,
        )

    return msgs[start:]


class AIChatStreamingService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None and settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def stream_chat(
        self,
        user: User,
        conversation_id: str,
        message: str,
        page_context: Optional[dict],
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
        request_start = time.time()

        # --- Log: Request baslangici ---
        logger.info(
            "[CHAT_START] user=%s conv=%s message=%s page=%s",
            user.id,
            conversation_id[:8],
            _truncate(message, 80),
            page_context.get("page", "-") if page_context else "-",
        )

        if not self.client:
            logger.error("[CHAT_ERROR] OpenAI client yapilandirilmamis")
            yield _sse("error", {"message": "AI servisi yapilandirilmamis."})
            return

        from app.services.ai_tools.registry import TOOL_DEFINITIONS, execute_tool
        from app.db.models import ChatConversation, ChatMessage

        # --- Conversation yonet ---
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
            logger.info("[CONV_NEW] conv=%s", conversation_id[:8])

        user_msg = ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        db.add(user_msg)
        db.flush()

        # --- Mesaj gecmisi ---
        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        # Son 20 mesaji al, ama temiz bir sinirdan baslat
        # (tool mesaji tool_calls assistant'siz kalinamaz)
        recent = history[-20:]
        recent = _trim_orphan_tool_messages(recent)

        messages = [{"role": "system", "content": _build_system_prompt(page_context)}]
        for msg in recent:
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

        logger.info(
            "[CONTEXT] history_msgs=%d trimmed=%d context_msgs=%d",
            len(history), len(recent), len(messages),
        )

        # Kullanicinin bu mesaji explicit bir onay mi?
        user_confirmed = _is_explicit_confirmation(message)
        if user_confirmed:
            logger.info("[CONFIRM] Kullanici onay verdi: %s", message.strip())

        # --- Tool calling + streaming loop ---
        final_content = ""
        max_iterations = 5
        total_tools_called = 0
        # Duplicate tool call tespiti: ayni (tool_name, args) → cached result
        executed_tool_cache: Dict[str, str] = {}

        try:
            for iteration in range(max_iterations):
                # Tool-calling phase: non-streaming
                llm_start = time.time()
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=2000,
                )
                llm_elapsed = time.time() - llm_start

                choice = response.choices[0]
                usage = response.usage

                # --- Log: LLM yaniti ---
                logger.info(
                    "[LLM_RESPONSE] iter=%d finish=%s tools=%d "
                    "tokens(prompt=%d completion=%d total=%d) %.1fs",
                    iteration,
                    choice.finish_reason,
                    len(choice.message.tool_calls or []),
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                    usage.total_tokens if usage else 0,
                    llm_elapsed,
                )

                if choice.finish_reason == "tool_calls":
                    # --- Log: Model tool secimi ---
                    tool_names = [tc.function.name for tc in choice.message.tool_calls]
                    logger.info(
                        "[TOOL_DECISION] iter=%d model_chose=%s",
                        iteration, tool_names,
                    )

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
                        tool_key = _make_tool_call_key(tool_name, tc.function.arguments)

                        # --- Log: Her tool cagrisi ---
                        logger.info(
                            "[TOOL_CALL] tool=%s args=%s",
                            tool_name, _truncate(tc.function.arguments, 150),
                        )

                        # --- Duplicate kontrolu: gercek cached sonuc don ---
                        if tool_key in executed_tool_cache:
                            logger.warning(
                                "[TOOL_DUPLICATE] tool=%s — cache'ten donuluyor",
                                tool_name,
                            )
                            cached_result = executed_tool_cache[tool_key]
                            tool_msg = ChatMessage(
                                conversation_id=conversation.id,
                                role="tool",
                                content=cached_result,
                                tool_call_id=tc.id,
                            )
                            db.add(tool_msg)
                            messages.append({
                                "role": "tool",
                                "content": cached_result,
                                "tool_call_id": tc.id,
                            })
                            continue

                        # --- Action tool onay guard ---
                        if tool_name in _ACTION_TOOLS and not user_confirmed:
                            logger.info(
                                "[ACTION_BLOCKED] tool=%s — onay bekleniyor",
                                tool_name,
                            )
                            try:
                                args_parsed = json.loads(tc.function.arguments)
                            except (json.JSONDecodeError, TypeError):
                                args_parsed = {}
                            blocked_result = json.dumps({
                                "hata": "onay_gerekli",
                                "mesaj": f"Bu islem icin onayiniz gerekiyor. Lutfen 'evet' veya 'tamam' ile onaylayin.",
                                "tool": tool_name,
                                "parametreler": args_parsed,
                            }, ensure_ascii=False)
                            tool_msg = ChatMessage(
                                conversation_id=conversation.id,
                                role="tool",
                                content=blocked_result,
                                tool_call_id=tc.id,
                            )
                            db.add(tool_msg)
                            messages.append({
                                "role": "tool",
                                "content": blocked_result,
                                "tool_call_id": tc.id,
                            })
                            continue

                        label = TOOL_LABELS.get(tool_name, f"{tool_name} calisiyor...")

                        # Frontend'e "tool basladi" event'i gonder
                        yield _sse("tool_start", {"name": tool_name, "label": label})

                        args = json.loads(tc.function.arguments)
                        tool_start = time.time()
                        result = await execute_tool(tool_name, args, str(user.id), db)
                        tool_elapsed = time.time() - tool_start
                        result_str = json.dumps(result, ensure_ascii=False, default=str)
                        total_tools_called += 1

                        # --- Log: Tool sonucu ---
                        has_error = isinstance(result, dict) and "hata" in result
                        logger.info(
                            "[TOOL_RESULT] tool=%s ok=%s %.2fs result=%s",
                            tool_name,
                            "ERROR" if has_error else "OK",
                            tool_elapsed,
                            _truncate(result_str, 200),
                        )

                        # Cache'e kaydet
                        executed_tool_cache[tool_key] = result_str

                        # Ozet cikar
                        summary = _extract_summary(result, tool_name)
                        yield _sse("tool_done", {"name": tool_name, "summary": summary})

                        # Export tool icin dosya hazir event'i gonder
                        if tool_name == "export_data" and isinstance(result, dict) and result.get("basarili"):
                            yield _sse("file_ready", {
                                "url": result["indirme_url"],
                                "filename": result["dosya_adi"],
                                "size": result["boyut"],
                                "format": result.get("format", ""),
                            })

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
                    # Final yanit
                    content = choice.message.content or ""

                    if content and iteration > 0:
                        # Tool kullanildi — gercek streaming ile daha iyi UX
                        logger.info(
                            "[STREAMING] Gercek streaming basliyor (iter=%d)",
                            iteration,
                        )
                        try:
                            stream_resp = await self.client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=messages,
                                stream=True,
                                temperature=0.7,
                                max_tokens=2000,
                            )
                            final_content = ""
                            async for chunk in stream_resp:
                                delta = chunk.choices[0].delta
                                if delta.content:
                                    final_content += delta.content
                                    yield _sse("token", {"content": delta.content})
                        except Exception as stream_err:
                            # Streaming hatasi — fallback
                            logger.warning(
                                "[STREAMING_FALLBACK] %s — pseudo-stream'e donuluyor",
                                stream_err,
                            )
                            final_content = content
                            chunk_size = 20
                            for i in range(0, len(content), chunk_size):
                                yield _sse("token", {"content": content[i:i + chunk_size]})
                    elif content:
                        # Ilk iterasyonda direkt yanit — pseudo-stream
                        logger.info("[PSEUDO_STREAM] Direkt yanit (tool kullanilmadi)")
                        final_content = content
                        chunk_size = 20
                        for i in range(0, len(content), chunk_size):
                            yield _sse("token", {"content": content[i:i + chunk_size]})

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

            total_elapsed = time.time() - request_start
            logger.info(
                "[CHAT_DONE] conv=%s tools_called=%d iterations=%d "
                "response_len=%d total=%.1fs",
                conversation_id[:8],
                total_tools_called,
                iteration + 1,
                len(final_content),
                total_elapsed,
            )

            yield _sse("done", {})

        except Exception as e:
            total_elapsed = time.time() - request_start
            logger.error(
                "[CHAT_ERROR] conv=%s error=%s total=%.1fs",
                conversation_id[:8], str(e), total_elapsed,
            )
            db.rollback()
            yield _sse("error", {"message": "Yanit olusturulamadi. Lutfen tekrar deneyin."})


def _extract_summary(result: dict, tool_name: str) -> str:
    """Tool sonucundan kisa ozet cikar."""
    if isinstance(result, dict):
        if "hata" in result:
            return f"Hata: {result['hata'][:60]}"
        if tool_name == "get_price_alerts":
            total = result.get("toplam_izlenen", 0)
            count = result.get("esik_ihlali_sayisi", 0)
            return f"{total} izlenen, {count} ihlal"
        if tool_name == "get_portfolio_summary":
            count = result.get("toplam_urun", 0)
            return f"{count} urun izleniyor"
        if tool_name == "compare_seller_prices":
            sellers = result.get("saticilar", [])
            return f"{len(sellers)} satici karsilastirildi"
        if tool_name == "get_product_insights":
            urun = result.get("urun", "")
            fiyat = result.get("guncel_fiyat", "")
            return f"{urun}: {fiyat} TL" if fiyat else f"{urun} verisi alindi"
        if tool_name == "search_keyword_analysis":
            keyword = result.get("keyword", "")
            total = result.get("toplam_arama", 0)
            return f"'{keyword}' icin {total} arama bulundu"
        if tool_name == "calculate_profitability":
            margin = result.get("kar_marji_yuzde", "")
            return f"Kar marji: %{margin}" if margin else "Hesaplama tamamlandi"
        if tool_name == "get_category_analysis":
            count = result.get("toplam_urun", 0)
            cat = result.get("kategori", "")
            return f"{cat}: {count} urun analiz edildi" if count else "Kategori verisi bulunamadi"
        if tool_name == "get_product_descriptions":
            count = result.get("bulunan", 0)
            return f"{count} urun aciklamasi getirildi" if count else "Aciklama bulunamadi"
        if tool_name == "analyze_product_descriptions":
            count = result.get("analiz_edilen_urun", 0)
            common = result.get("ortak_kelimeler", [])
            return f"{count} urun analiz edildi, {len(common)} ortak kelime" if count else "Analiz yapilamadi"
        if tool_name == "search_products_by_name":
            count = result.get("bulunan", 0)
            return f"{count} urun bulundu" if count else "Urun bulunamadi"
        if tool_name == "export_data":
            if result.get("basarili"):
                return f"{result.get('dosya_adi', 'dosya')} hazir ({result.get('boyut', '')})"
            return "Dosya olusturulamadi"
    return "Tamamlandi"


ai_streaming_service = AIChatStreamingService()
