"""Hybrid search service testleri.

Plan dogrulama:
- Feature flag HYBRID_SEARCH_ENABLED=false → ILIKE fallback.
- Embedding yoksa ILIKE fallback (sifir regresyon).
- user_id izolasyonu korunuyor.
- Platform filtresi calisiyor.
- Bos query → bos liste.
- OPENAI_API_KEY yoksa → ILIKE fallback.
- Extension yoksa → ILIKE fallback (exception degil).
"""

import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from types import SimpleNamespace

from app.db.models import User, MonitoredProduct


@pytest.fixture()
def test_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Test User",
        plan_tier="free",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def products(db_session, test_user):
    """Uc urun olustur — hybrid search icin."""
    items = []
    for i, (name, brand, platform) in enumerate([
        ("Sonax Hizli Cila 500ml", "Sonax", "hepsiburada"),
        ("Meguiars Gold Class Wax", "Meguiars", "hepsiburada"),
        ("Fra-Ber Nano Cila", "Fra-Ber", "trendyol"),
    ]):
        product = MonitoredProduct(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform=platform,
            sku=f"SKU-{i:03d}",
            product_url=f"https://example.com/{i}",
            product_name=name,
            brand=brand,
            is_active=True,
        )
        db_session.add(product)
        items.append(product)
    db_session.flush()
    return items


class TestFeatureFlag:
    """Feature flag kontrolleri."""

    @pytest.mark.asyncio
    async def test_disabled_flag_uses_ilike(self, db_session, test_user, products):
        """HYBRID_SEARCH_ENABLED=false ise ILIKE fallback calismali."""
        from app.services.hybrid_search_service import hybrid_search_monitored

        with patch("app.services.hybrid_search_service.settings") as mock_settings:
            mock_settings.HYBRID_SEARCH_ENABLED = False

            results = await hybrid_search_monitored(
                db=db_session, user_id=str(test_user.id), query="Sonax"
            )
            # ILIKE ile "Sonax" product_name'de gectiginden sonuc bulmali
            assert len(results) >= 1
            assert any("Sonax" in (p.product_name or "") for p in results)

    @pytest.mark.asyncio
    async def test_enabled_flag_no_embeddings_falls_back(
        self, db_session, test_user, products
    ):
        """Embedding yoksa ILIKE fallback calismali."""
        from app.services.hybrid_search_service import hybrid_search_monitored

        with patch("app.services.hybrid_search_service.settings") as mock_settings:
            mock_settings.HYBRID_SEARCH_ENABLED = True

            results = await hybrid_search_monitored(
                db=db_session, user_id=str(test_user.id), query="Sonax"
            )
            # Embedding olmadan ILIKE ile bulmali
            assert len(results) >= 1


class TestILIKEFallback:
    """ILIKE fallback dogru calismali."""

    @pytest.mark.asyncio
    async def test_basic_search(self, db_session, test_user, products):
        from app.services.hybrid_search_service import _ilike_fallback

        results = _ilike_fallback(
            db=db_session,
            user_id=str(test_user.id),
            query="Sonax",
            platform="",
            limit=10,
        )
        assert len(results) == 1
        assert results[0].product_name == "Sonax Hizli Cila 500ml"

    @pytest.mark.asyncio
    async def test_platform_filter(self, db_session, test_user, products):
        from app.services.hybrid_search_service import _ilike_fallback

        results = _ilike_fallback(
            db=db_session,
            user_id=str(test_user.id),
            query="Cila",
            platform="hepsiburada",
            limit=10,
        )
        # "Cila" hepsiburada'da: Sonax Hizli Cila (1 urun)
        assert len(results) == 1
        assert results[0].platform == "hepsiburada"

    @pytest.mark.asyncio
    async def test_user_isolation(self, db_session, products):
        """Farkli user'in urunleri gorulmemeli."""
        from app.services.hybrid_search_service import _ilike_fallback

        fake_user_id = str(uuid.uuid4())
        results = _ilike_fallback(
            db=db_session,
            user_id=fake_user_id,
            query="Sonax",
            platform="",
            limit=10,
        )
        assert len(results) == 0


class TestEmptyQuery:
    """Bos query edge case'leri."""

    @pytest.mark.asyncio
    async def test_empty_string(self, db_session, test_user):
        from app.services.hybrid_search_service import hybrid_search_monitored

        results = await hybrid_search_monitored(
            db=db_session, user_id=str(test_user.id), query=""
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_none_query(self, db_session, test_user):
        from app.services.hybrid_search_service import hybrid_search_monitored

        results = await hybrid_search_monitored(
            db=db_session, user_id=str(test_user.id), query=None
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_whitespace_only(self, db_session, test_user):
        from app.services.hybrid_search_service import hybrid_search_monitored

        results = await hybrid_search_monitored(
            db=db_session, user_id=str(test_user.id), query="   "
        )
        assert results == []


class TestExtensionGuard:
    """Extension veya API hatalarinda graceful fallback."""

    @pytest.mark.asyncio
    async def test_extension_error_falls_back(self, db_session, test_user, products):
        """pgvector extension yoksa ILIKE fallback calismali."""
        from app.services.hybrid_search_service import hybrid_search_monitored

        with patch("app.services.hybrid_search_service.settings") as mock_settings, \
             patch("app.services.hybrid_search_service._check_embeddings_exist") as mock_check:
            mock_settings.HYBRID_SEARCH_ENABLED = True
            mock_check.side_effect = Exception("extension vector does not exist")

            results = await hybrid_search_monitored(
                db=db_session, user_id=str(test_user.id), query="Sonax"
            )
            # Exception olmasina ragmen ILIKE ile sonuc donmeli
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_embedding_api_error_falls_back(
        self, db_session, test_user, products
    ):
        """Embedding API hatasi durumunda ILIKE fallback calismali."""
        from app.services.hybrid_search_service import hybrid_search_monitored

        with patch("app.services.hybrid_search_service.settings") as mock_settings, \
             patch("app.services.hybrid_search_service._check_embeddings_exist", return_value=True), \
             patch("app.services.embedding_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            mock_settings.HYBRID_SEARCH_ENABLED = True

            results = await hybrid_search_monitored(
                db=db_session, user_id=str(test_user.id), query="Sonax"
            )
            assert len(results) >= 1
