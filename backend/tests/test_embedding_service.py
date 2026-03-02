"""Embedding service testleri.

Plan dogrulama:
- build_search_text_monitored dogru concatenation yapar.
- None alanlari graceful handle eder.
- API key yoksa exception degil None doner.
- generate_embedding mock OpenAI ile 1536-dim vector doner.
- embed_monitored_product search_text degismemisse skip eder.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from types import SimpleNamespace


class TestBuildSearchTextMonitored:
    """build_search_text_monitored testleri."""

    def test_full_product(self):
        from app.services.embedding_service import build_search_text_monitored

        product = SimpleNamespace(
            product_name="Sonax Hizli Cila",
            brand="Sonax",
            sku="HB-12345",
            barcode="8699900000001",
            platform="hepsiburada",
        )
        result = build_search_text_monitored(product)
        assert "Sonax Hizli Cila" in result
        assert "Sonax" in result
        assert "HB-12345" in result
        assert "8699900000001" in result
        assert "hepsiburada" in result
        assert " | " in result

    def test_none_fields(self):
        from app.services.embedding_service import build_search_text_monitored

        product = SimpleNamespace(
            product_name=None,
            brand="Sonax",
            sku=None,
            barcode=None,
            platform="hepsiburada",
        )
        result = build_search_text_monitored(product)
        assert "Sonax" in result
        assert "hepsiburada" in result
        # None alanlar atlanmali
        assert "None" not in result

    def test_all_none(self):
        from app.services.embedding_service import build_search_text_monitored

        product = SimpleNamespace(
            product_name=None, brand=None, sku=None, barcode=None, platform=None
        )
        result = build_search_text_monitored(product)
        assert result == ""

    def test_empty_strings(self):
        from app.services.embedding_service import build_search_text_monitored

        product = SimpleNamespace(
            product_name="", brand="", sku="", barcode="", platform=""
        )
        result = build_search_text_monitored(product)
        assert result == ""


class TestGenerateEmbedding:
    """generate_embedding testleri."""

    @pytest.mark.asyncio
    async def test_returns_embedding_vector(self):
        from app.services.embedding_service import generate_embedding

        mock_embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [SimpleNamespace(embedding=mock_embedding)]

        with patch("app.services.embedding_service._get_client") as mock_client:
            client = AsyncMock()
            client.embeddings.create = AsyncMock(return_value=mock_response)
            mock_client.return_value = client

            result = await generate_embedding("test text")
            assert result is not None
            assert len(result) == 1536
            assert result[0] == 0.1

    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self):
        from app.services.embedding_service import generate_embedding

        result = await generate_embedding("")
        assert result is None

    @pytest.mark.asyncio
    async def test_none_text_returns_none(self):
        from app.services.embedding_service import generate_embedding

        result = await generate_embedding(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        from app.services.embedding_service import generate_embedding

        with patch("app.services.embedding_service._get_client") as mock_client:
            client = AsyncMock()
            client.embeddings.create = AsyncMock(
                side_effect=Exception("API rate limit")
            )
            mock_client.return_value = client

            result = await generate_embedding("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        from app.services.embedding_service import generate_embedding

        with patch("app.services.embedding_service._get_client") as mock_client:
            mock_client.side_effect = RuntimeError("OPENAI_API_KEY is not configured")

            result = await generate_embedding("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_long_text_truncated(self):
        from app.services.embedding_service import generate_embedding

        mock_response = MagicMock()
        mock_response.data = [SimpleNamespace(embedding=[0.1] * 1536)]

        with patch("app.services.embedding_service._get_client") as mock_client:
            client = AsyncMock()
            client.embeddings.create = AsyncMock(return_value=mock_response)
            mock_client.return_value = client

            long_text = "x" * 10000
            await generate_embedding(long_text)

            # Verify input was truncated to 8000
            call_args = client.embeddings.create.call_args
            assert len(call_args.kwargs["input"]) <= 8000


class TestGenerateEmbeddingsBatch:
    """generate_embeddings_batch testleri."""

    @pytest.mark.asyncio
    async def test_batch_with_mixed_texts(self):
        from app.services.embedding_service import generate_embeddings_batch

        mock_response = MagicMock()
        mock_response.data = [
            SimpleNamespace(embedding=[0.1] * 1536),
            SimpleNamespace(embedding=[0.2] * 1536),
        ]

        with patch("app.services.embedding_service._get_client") as mock_client:
            client = AsyncMock()
            client.embeddings.create = AsyncMock(return_value=mock_response)
            mock_client.return_value = client

            # 4 text, 2'si valid, 2'si bos
            texts = ["valid text 1", "", "valid text 2", None]
            results = await generate_embeddings_batch(texts)

            assert len(results) == 4
            assert results[0] is not None
            assert results[1] is None  # Bos text
            assert results[2] is not None
            assert results[3] is None  # None text

    @pytest.mark.asyncio
    async def test_empty_list(self):
        from app.services.embedding_service import generate_embeddings_batch

        results = await generate_embeddings_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_all_empty_texts(self):
        from app.services.embedding_service import generate_embeddings_batch

        results = await generate_embeddings_batch(["", None, ""])
        assert len(results) == 3
        assert all(r is None for r in results)


class TestEmbedMonitoredProduct:
    """embed_monitored_product testleri."""

    @pytest.mark.asyncio
    async def test_skip_when_search_text_unchanged(self):
        """search_text degismemisse API cagrisi yapilmamali."""
        from app.services.embedding_service import embed_monitored_product

        product = SimpleNamespace(
            product_name="Test",
            brand="Brand",
            sku="SKU-1",
            barcode=None,
            platform="hepsiburada",
            search_text="Test | Brand | SKU-1 | hepsiburada",
            embedding=[0.1] * 1536,
        )

        result = await embed_monitored_product(product, MagicMock())
        assert result is False  # Skip — degisiklik yok

    @pytest.mark.asyncio
    async def test_embeds_when_search_text_changed(self):
        """search_text degistiyse yeni embedding uretilmeli."""
        from app.services.embedding_service import embed_monitored_product

        product = SimpleNamespace(
            product_name="Yeni Ad",
            brand="Brand",
            sku="SKU-1",
            barcode=None,
            platform="hepsiburada",
            search_text="Eski Ad | Brand | SKU-1 | hepsiburada",
            embedding=[0.1] * 1536,
        )

        mock_embedding = [0.2] * 1536
        with patch(
            "app.services.embedding_service.generate_embedding",
            new_callable=AsyncMock,
            return_value=mock_embedding,
        ):
            result = await embed_monitored_product(product, MagicMock())
            assert result is True
            assert product.embedding == mock_embedding
            assert "Yeni Ad" in product.search_text

    @pytest.mark.asyncio
    async def test_embeds_when_no_existing_embedding(self):
        """embedding None ise uretilmeli."""
        from app.services.embedding_service import embed_monitored_product

        product = SimpleNamespace(
            product_name="Test",
            brand="Brand",
            sku="SKU-1",
            barcode=None,
            platform="hepsiburada",
            search_text="Test | Brand | SKU-1 | hepsiburada",
            embedding=None,
        )

        mock_embedding = [0.3] * 1536
        with patch(
            "app.services.embedding_service.generate_embedding",
            new_callable=AsyncMock,
            return_value=mock_embedding,
        ):
            result = await embed_monitored_product(product, MagicMock())
            assert result is True
            assert product.embedding == mock_embedding

    @pytest.mark.asyncio
    async def test_empty_product_name_returns_false(self):
        """product_name olmayan urun icin False donmeli."""
        from app.services.embedding_service import embed_monitored_product

        product = SimpleNamespace(
            product_name=None,
            brand=None,
            sku=None,
            barcode=None,
            platform=None,
            search_text=None,
            embedding=None,
        )
        result = await embed_monitored_product(product, MagicMock())
        assert result is False
