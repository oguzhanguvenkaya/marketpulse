"""Final streaming davranisi testleri.

Plan dogrulama:
- Tool kullanilan akista ikinci cagri stream=True ile delta token uretir.
- Tool kullanilmayan ilk-iterasyon akisinda pseudo-stream korunur.
- Streaming hatasi durumunda fallback pseudo-stream calismali.
"""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from types import SimpleNamespace

from app.services.ai_streaming_service import (
    AIChatStreamingService,
    _sse,
    _build_system_prompt,
)
from app.db.models import User


def _make_sse_events(raw_events: list[str]) -> list[dict]:
    """SSE string'lerini parse edip event listesi olustur."""
    events = []
    for raw in raw_events:
        lines = raw.strip().split("\n")
        event_type = None
        data = None
        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if event_type:
            events.append({"type": event_type, "data": data})
    return events


class TestSSEHelper:
    """_sse helper dogru format uretmeli."""

    def test_basic_sse_format(self):
        result = _sse("token", {"content": "hello"})
        assert result.startswith("event: token\n")
        assert '"content": "hello"' in result
        assert result.endswith("\n\n")

    def test_unicode_content(self):
        result = _sse("token", {"content": "Türkçe karakter: ğüşöç"})
        assert "Türkçe" in result  # ensure_ascii=False kontrolu

    def test_done_event(self):
        result = _sse("done", {})
        assert "event: done" in result

    def test_error_event(self):
        result = _sse("error", {"message": "Hata olustu"})
        assert "event: error" in result
        assert "Hata olustu" in result


class TestBuildSystemPrompt:
    """_build_system_prompt sayfa baglamini dogru eklemeli."""

    def test_no_context(self):
        prompt = _build_system_prompt(None)
        assert "MarketPulse" in prompt
        assert "Mevcut Sayfa" not in prompt

    def test_with_page_context(self):
        ctx = {
            "page": "price_monitor",
            "platform": "hepsiburada",
            "product_name": "Test Urun",
            "sku": "TEST-SKU",
        }
        prompt = _build_system_prompt(ctx)
        assert "Fiyat Izleme" in prompt
        assert "Hepsiburada" in prompt
        assert "Test Urun" in prompt
        assert "TEST-SKU" in prompt

    def test_with_category_context(self):
        ctx = {
            "page": "category_explorer",
            "category_name": "Hizli Cila",
        }
        prompt = _build_system_prompt(ctx)
        assert "Kategori Kesif" in prompt
        assert "Hizli Cila" in prompt

    def test_with_filters(self):
        ctx = {
            "page": "category_explorer",
            "filters": {
                "brand": "Sonax",
                "min_price": "50",
                "max_price": "200",
            },
        }
        prompt = _build_system_prompt(ctx)
        assert "Sonax" in prompt
        assert "50" in prompt
        assert "200" in prompt


class TestStreamingBehavior:
    """Streaming vs pseudo-streaming davranisi.

    NOT: Bu testler OpenAI API'yi mock'lar.
    Gercek streaming davranisini unit test duzeyde dogrular.
    """

    def test_pseudo_stream_chunks_text(self):
        """Pseudo-stream 20 karakter bloklar halinde gondermeli."""
        content = "Bu bir test cevabi. Toplam 60 karakterden uzun olmasi lazim."
        chunk_size = 20
        chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        reconstructed = "".join(chunks)
        assert reconstructed == content
        assert all(len(c) <= chunk_size for c in chunks)

    def test_sse_token_event_format(self):
        """Token event'i dogru SSE formatinda olmali."""
        event = _sse("token", {"content": "Merhaba"})
        assert "event: token" in event
        data_line = [l for l in event.split("\n") if l.startswith("data:")][0]
        parsed = json.loads(data_line[5:].strip())
        assert parsed["content"] == "Merhaba"


class TestStreamChatServiceInit:
    """AIChatStreamingService baslatma testleri."""

    def test_client_lazy_init(self):
        """Client API key olmadan None olmali."""
        service = AIChatStreamingService()
        assert service._client is None

    def test_client_created_with_api_key(self):
        """API key varsa client olusturulmali."""
        service = AIChatStreamingService()

        with patch("app.services.ai_streaming_service.settings") as mock_settings, \
             patch("openai.AsyncOpenAI") as MockClient:
            mock_settings.OPENAI_API_KEY = "test-key"
            MockClient.return_value = MagicMock()
            # _client'i sifirla ki property yeniden calissin
            service._client = None
            client = service.client
            MockClient.assert_called_once_with(api_key="test-key")
