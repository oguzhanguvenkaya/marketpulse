"""Search scope testleri.

Test edilen:
- system prompt'a scope bilgisi eklenmesi
- page scope prompt icerigi
- global scope prompt icerigi
- auto scope prompt icerigi
- ChatStreamRequest validation
"""

import pytest
from app.services.ai_streaming_service import _build_system_prompt


class TestSearchScopePrompt:
    """_build_system_prompt search_scope parametresi testleri."""

    def test_page_scope_in_prompt(self):
        """page scope prompt'a 'SAYFA' bilgisi eklemeli."""
        ctx = {"page": "category_explorer", "category_name": "Hızlı Cila"}
        prompt = _build_system_prompt(ctx, search_scope="page")
        assert "SAYFA" in prompt
        assert "Hızlı Cila" in prompt

    def test_global_scope_in_prompt(self):
        """global scope prompt'a 'GLOBAL' bilgisi eklemeli."""
        ctx = {"page": "category_explorer"}
        prompt = _build_system_prompt(ctx, search_scope="global")
        assert "GLOBAL" in prompt

    def test_auto_scope_in_prompt(self):
        """auto scope prompt'a 'OTOMATİK' bilgisi eklemeli."""
        ctx = {"page": "category_explorer"}
        prompt = _build_system_prompt(ctx, search_scope="auto")
        assert "OTOMATİK" in prompt

    def test_no_context_no_scope(self):
        """Context yoksa base prompt donmeli."""
        prompt = _build_system_prompt(None)
        assert "MarketPulse AI" in prompt
        # Scope bilgisi olmamali (context yok)
        assert "SAYFA" not in prompt
        assert "GLOBAL" not in prompt


class TestChatStreamRequest:
    """ChatStreamRequest search_scope validation."""

    def test_default_scope(self):
        from app.api.ai_streaming_routes import ChatStreamRequest

        req = ChatStreamRequest(message="test")
        assert req.search_scope == "auto"

    def test_custom_scope(self):
        from app.api.ai_streaming_routes import ChatStreamRequest

        req = ChatStreamRequest(message="test", search_scope="global")
        assert req.search_scope == "global"

    def test_page_scope(self):
        from app.api.ai_streaming_routes import ChatStreamRequest

        req = ChatStreamRequest(message="test", search_scope="page")
        assert req.search_scope == "page"
