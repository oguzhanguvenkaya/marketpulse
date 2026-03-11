"""Reranker service testleri.

Test edilen:
- API key yoksa graceful fallback (orijinal sirayi korur)
- Disabled config ile fallback
- API hatasi durumunda fallback
- Basarili rerank (mock Cohere)
- Bos liste
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from types import SimpleNamespace


class TestRerankerFallback:
    """API key/error durumlarinda graceful fallback."""

    @pytest.mark.asyncio
    async def test_no_api_key_returns_original(self):
        """COHERE_API_KEY bos ise orijinal sira donmeli."""
        from app.services.reranker_service import rerank_products

        items = ["a", "b", "c"]
        with patch("app.services.reranker_service.settings") as mock_settings:
            mock_settings.COHERE_API_KEY = ""
            mock_settings.RERANKER_ENABLED = True
            mock_settings.RERANKER_TOP_N = 10
            mock_settings.RERANKER_MODEL = "rerank-v3.5"

            result = await rerank_products(
                query="test",
                products=items,
                build_doc_fn=lambda x: x,
            )
            assert result == items

    @pytest.mark.asyncio
    async def test_disabled_returns_original(self):
        """RERANKER_ENABLED=false ise orijinal sira donmeli."""
        from app.services.reranker_service import rerank_products

        items = ["a", "b", "c"]
        with patch("app.services.reranker_service.settings") as mock_settings:
            mock_settings.RERANKER_ENABLED = False
            mock_settings.RERANKER_TOP_N = 10

            result = await rerank_products(
                query="test",
                products=items,
                build_doc_fn=lambda x: x,
            )
            assert result == items

    @pytest.mark.asyncio
    async def test_empty_products(self):
        """Bos liste bos donmeli."""
        from app.services.reranker_service import rerank_products

        result = await rerank_products(
            query="test",
            products=[],
            build_doc_fn=lambda x: x,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_api_error_returns_original(self):
        """Cohere API hatasi durumunda orijinal sira donmeli."""
        from app.services.reranker_service import rerank_products

        items = ["a", "b", "c"]

        mock_client = AsyncMock()
        mock_client.rerank.side_effect = Exception("API error")

        # cohere modulu yuklu olmayabilir — fake module ile mock'la
        fake_cohere = MagicMock()
        fake_cohere.AsyncClientV2.return_value = mock_client

        with patch("app.services.reranker_service.settings") as mock_settings, \
             patch.dict("sys.modules", {"cohere": fake_cohere}):
            mock_settings.COHERE_API_KEY = "test-key"
            mock_settings.RERANKER_ENABLED = True
            mock_settings.RERANKER_TOP_N = 10
            mock_settings.RERANKER_MODEL = "rerank-v3.5"

            result = await rerank_products(
                query="test",
                products=items,
                build_doc_fn=lambda x: x,
            )
            assert result == items

    @pytest.mark.asyncio
    async def test_successful_rerank(self):
        """Basarili rerank — sirayi degistirmeli."""
        from app.services.reranker_service import rerank_products

        items = ["a", "b", "c"]

        # Cohere response mock: 2. eleman birinci, 0. ikinci
        mock_response = SimpleNamespace(
            results=[
                SimpleNamespace(index=2, relevance_score=0.9),
                SimpleNamespace(index=0, relevance_score=0.7),
                SimpleNamespace(index=1, relevance_score=0.5),
            ]
        )
        mock_client = AsyncMock()
        mock_client.rerank.return_value = mock_response

        # cohere modulu yuklu olmayabilir — fake module ile mock'la
        fake_cohere = MagicMock()
        fake_cohere.AsyncClientV2.return_value = mock_client

        with patch("app.services.reranker_service.settings") as mock_settings, \
             patch.dict("sys.modules", {"cohere": fake_cohere}):
            mock_settings.COHERE_API_KEY = "test-key"
            mock_settings.RERANKER_ENABLED = True
            mock_settings.RERANKER_TOP_N = 10
            mock_settings.RERANKER_MODEL = "rerank-v3.5"

            result = await rerank_products(
                query="test",
                products=items,
                build_doc_fn=lambda x: x,
            )
            assert result == ["c", "a", "b"]

    @pytest.mark.asyncio
    async def test_top_n_limits_results(self):
        """top_n parametresi sonuc sayisini sinirlamali."""
        from app.services.reranker_service import rerank_products

        items = ["a", "b", "c", "d", "e"]
        with patch("app.services.reranker_service.settings") as mock_settings:
            mock_settings.COHERE_API_KEY = ""
            mock_settings.RERANKER_ENABLED = True
            mock_settings.RERANKER_TOP_N = 10

            result = await rerank_products(
                query="test",
                products=items,
                build_doc_fn=lambda x: x,
                top_n=2,
            )
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_import_error_fallback(self):
        """cohere paketi yuklu degilse graceful fallback."""
        from app.services.reranker_service import rerank_products

        items = ["a", "b", "c"]
        with patch("app.services.reranker_service.settings") as mock_settings, \
             patch.dict("sys.modules", {"cohere": None}):
            mock_settings.COHERE_API_KEY = "test-key"
            mock_settings.RERANKER_ENABLED = True
            mock_settings.RERANKER_TOP_N = 10
            mock_settings.RERANKER_MODEL = "rerank-v3.5"

            result = await rerank_products(
                query="test",
                products=items,
                build_doc_fn=lambda x: x,
            )
            assert result == items
