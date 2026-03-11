"""Category hybrid search testleri.

Test edilen:
- ILIKE fallback calismasi
- Kategori filtresi
- Platform filtresi
- User izolasyonu
- Bos query
- Feature flag disabled → ILIKE fallback
- Embedding yoksa ILIKE fallback
- Extension hatasi → graceful ILIKE fallback
"""

import uuid
import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal

from app.db.models import User, CategorySession, CategoryProduct


@pytest.fixture()
def test_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email=f"cattest-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Category Test User",
        plan_tier="free",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def category_session(db_session, test_user):
    """Bir kategori tarama session'i olustur."""
    session = CategorySession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        platform="hepsiburada",
        category_url="https://hepsiburada.com/hizli-cila",
        category_name="Hızlı Cila",
        total_products=3,
    )
    db_session.add(session)
    db_session.flush()
    return session


@pytest.fixture()
def category_products(db_session, category_session):
    """Kategori urunleri olustur."""
    items = []
    for i, (name, brand, price) in enumerate([
        ("Sonax Hızlı Cila 500ml", "Sonax", Decimal("289.90")),
        ("Fra-Ber Nano Cila 250ml", "Fra-Ber", Decimal("399.90")),
        ("Meguiar's Gold Class Wax", "Meguiar's", Decimal("549.90")),
    ]):
        product = CategoryProduct(
            session_id=category_session.id,
            name=name,
            brand=brand,
            price=price,
            position=i + 1,
            page_number=1,
            description=f"{name} detayli aciklama",
        )
        db_session.add(product)
        items.append(product)
    db_session.flush()
    return items


class TestILIKEFallbackCategory:
    """category_products ILIKE fallback testleri."""

    @pytest.mark.asyncio
    async def test_basic_name_search(self, db_session, test_user, category_products):
        from app.services.hybrid_search_service import _ilike_fallback_category

        results = _ilike_fallback_category(
            db=db_session,
            user_id=str(test_user.id),
            query="Sonax",
            category_name="",
            platform="",
            limit=10,
        )
        assert len(results) == 1
        assert "Sonax" in results[0].name

    @pytest.mark.asyncio
    async def test_category_filter(self, db_session, test_user, category_products):
        from app.services.hybrid_search_service import _ilike_fallback_category

        results = _ilike_fallback_category(
            db=db_session,
            user_id=str(test_user.id),
            query="Cila",
            category_name="Hızlı Cila",
            platform="",
            limit=10,
        )
        # "Cila" iki urunde var: Sonax + Fra-Ber
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_platform_filter(self, db_session, test_user, category_products):
        from app.services.hybrid_search_service import _ilike_fallback_category

        results = _ilike_fallback_category(
            db=db_session,
            user_id=str(test_user.id),
            query="Cila",
            category_name="",
            platform="hepsiburada",
            limit=10,
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_user_isolation(self, db_session, category_products):
        from app.services.hybrid_search_service import _ilike_fallback_category

        fake_user_id = str(uuid.uuid4())
        results = _ilike_fallback_category(
            db=db_session,
            user_id=fake_user_id,
            query="Sonax",
            category_name="",
            platform="",
            limit=10,
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_no_match(self, db_session, test_user, category_products):
        from app.services.hybrid_search_service import _ilike_fallback_category

        results = _ilike_fallback_category(
            db=db_session,
            user_id=str(test_user.id),
            query="bulunamayacakurun",
            category_name="",
            platform="",
            limit=10,
        )
        assert len(results) == 0


class TestHybridSearchCategory:
    """hybrid_search_category fonksiyonu testleri."""

    @pytest.mark.asyncio
    async def test_empty_query(self, db_session, test_user):
        from app.services.hybrid_search_service import hybrid_search_category

        results = await hybrid_search_category(
            db=db_session, user_id=str(test_user.id), query=""
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_disabled_flag_uses_ilike(self, db_session, test_user, category_products):
        """Feature flag kapali ise ILIKE fallback calismali."""
        from app.services.hybrid_search_service import hybrid_search_category

        with patch("app.services.hybrid_search_service.settings") as mock_settings:
            mock_settings.HYBRID_SEARCH_ENABLED = False

            results = await hybrid_search_category(
                db=db_session, user_id=str(test_user.id), query="Sonax"
            )
            assert len(results) >= 1
            assert any("Sonax" in (p.name or "") for p in results)

    @pytest.mark.asyncio
    async def test_no_embeddings_falls_back(self, db_session, test_user, category_products):
        """Embedding yoksa ILIKE fallback."""
        from app.services.hybrid_search_service import hybrid_search_category

        with patch("app.services.hybrid_search_service.settings") as mock_settings:
            mock_settings.HYBRID_SEARCH_ENABLED = True

            results = await hybrid_search_category(
                db=db_session, user_id=str(test_user.id), query="Sonax"
            )
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_extension_error_falls_back(self, db_session, test_user, category_products):
        """Extension hatasi gracefully ILIKE'a donmeli."""
        from app.services.hybrid_search_service import hybrid_search_category

        with patch("app.services.hybrid_search_service.settings") as mock_settings, \
             patch("app.services.hybrid_search_service._check_category_embeddings_exist") as mock_check:
            mock_settings.HYBRID_SEARCH_ENABLED = True
            mock_check.side_effect = Exception("extension vector does not exist")

            results = await hybrid_search_category(
                db=db_session, user_id=str(test_user.id), query="Sonax"
            )
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_embedding_api_error_falls_back(self, db_session, test_user, category_products):
        """Embedding API hatasi → ILIKE fallback."""
        from app.services.hybrid_search_service import hybrid_search_category

        with patch("app.services.hybrid_search_service.settings") as mock_settings, \
             patch("app.services.hybrid_search_service._check_category_embeddings_exist", return_value=True), \
             patch("app.services.embedding_service.generate_embedding", new_callable=AsyncMock, return_value=None):
            mock_settings.HYBRID_SEARCH_ENABLED = True

            results = await hybrid_search_category(
                db=db_session, user_id=str(test_user.id), query="Sonax"
            )
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_category_name_filter(self, db_session, test_user, category_products):
        """category_name filtresi calismali."""
        from app.services.hybrid_search_service import hybrid_search_category

        with patch("app.services.hybrid_search_service.settings") as mock_settings:
            mock_settings.HYBRID_SEARCH_ENABLED = False

            results = await hybrid_search_category(
                db=db_session,
                user_id=str(test_user.id),
                query="Cila",
                category_name="Hızlı Cila",
            )
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_whitespace_query(self, db_session, test_user):
        from app.services.hybrid_search_service import hybrid_search_category

        results = await hybrid_search_category(
            db=db_session, user_id=str(test_user.id), query="   "
        )
        assert results == []
