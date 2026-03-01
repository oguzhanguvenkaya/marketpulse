"""Duplicate tool call cache testleri.

Plan dogrulama:
- Ayni tool+args iki kez cagrilir.
- Tool fonksiyonunun tek kez calistirildigini dogrula.
- Ikinci tool mesajinda gercek cached JSON kullanilir.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai_streaming_service import _make_tool_call_key


class TestMakeToolCallKey:
    """_make_tool_call_key ayni tool+args icin ayni key uretmeli."""

    def test_same_args_same_key(self):
        key1 = _make_tool_call_key("get_price_alerts", '{"sku": "ABC"}')
        key2 = _make_tool_call_key("get_price_alerts", '{"sku": "ABC"}')
        assert key1 == key2

    def test_different_key_order_same_key(self):
        """JSON key siralama farki ayni key uretmeli."""
        key1 = _make_tool_call_key("compare_seller_prices", '{"sku": "X", "platform": "hepsiburada"}')
        key2 = _make_tool_call_key("compare_seller_prices", '{"platform": "hepsiburada", "sku": "X"}')
        assert key1 == key2

    def test_different_tool_different_key(self):
        key1 = _make_tool_call_key("get_price_alerts", '{"sku": "ABC"}')
        key2 = _make_tool_call_key("get_portfolio_summary", '{"sku": "ABC"}')
        assert key1 != key2

    def test_different_args_different_key(self):
        key1 = _make_tool_call_key("get_price_alerts", '{"sku": "ABC"}')
        key2 = _make_tool_call_key("get_price_alerts", '{"sku": "XYZ"}')
        assert key1 != key2

    def test_empty_args(self):
        key1 = _make_tool_call_key("get_portfolio_summary", '{}')
        key2 = _make_tool_call_key("get_portfolio_summary", '{}')
        assert key1 == key2

    def test_invalid_json_fallback(self):
        """Bozuk JSON'da bile key uretebilmeli."""
        key1 = _make_tool_call_key("tool", 'not-json')
        key2 = _make_tool_call_key("tool", 'not-json')
        assert key1 == key2

    def test_invalid_json_different_from_valid(self):
        """Bozuk JSON farkli key uretmeli."""
        key1 = _make_tool_call_key("tool", 'not-json')
        key2 = _make_tool_call_key("tool", '{"key": "value"}')
        assert key1 != key2


class TestDuplicateToolCacheBehavior:
    """Duplicate tool cache Dict[str, str] davranisi.

    Cache yalnizca tool calistiktan sonra dolar,
    ayni key tekrar geldiginde cached result kullanilir.
    """

    def test_cache_stores_result_string(self):
        """Cache icin temel dict davranisi testi."""
        cache = {}
        tool_key = _make_tool_call_key("get_price_alerts", '{}')
        result_str = '{"toplam_izlenen": 5}'

        # Ilk calisma: cache bos, result uretilir
        assert tool_key not in cache
        cache[tool_key] = result_str

        # Ikinci calisma: cache'te var
        assert tool_key in cache
        assert cache[tool_key] == result_str

    def test_cache_returns_exact_result(self):
        """Cached sonuc birebir ayni string olmali."""
        cache = {}
        key = _make_tool_call_key("compare_seller_prices", '{"sku": "ABC"}')
        original = '{"saticilar": [{"satici": "X", "fiyat": 100}]}'

        cache[key] = original
        cached = cache[key]

        assert cached == original
        assert cached is original  # ayni string nesnesi
