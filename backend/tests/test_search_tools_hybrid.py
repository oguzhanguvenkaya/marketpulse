"""search_products_by_name hybrid entegrasyon testleri.

Plan dogrulama:
- Return formati degismemis (geriye uyumluluk).
- Embedding olmadan mevcut ILIKE davranisi korunuyor.
"""

import uuid
import pytest
from decimal import Decimal
from datetime import datetime

from app.db.models import User, MonitoredProduct, SellerSnapshot


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
def products_with_snapshots(db_session, test_user):
    """Urunler + buybox snapshot'lari."""
    products = []
    for i, (name, brand) in enumerate([
        ("Sonax Hizli Cila 500ml", "Sonax"),
        ("Meguiars Gold Class Wax", "Meguiars"),
        ("Fra-Ber Nano Cila", "Fra-Ber"),
    ]):
        product = MonitoredProduct(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            sku=f"SKU-{i:03d}",
            product_url=f"https://example.com/{i}",
            product_name=name,
            brand=brand,
            image_url=f"https://img.example.com/{i}.jpg",
            is_active=True,
        )
        db_session.add(product)
        db_session.flush()

        snapshot = SellerSnapshot(
            monitored_product_id=product.id,
            merchant_id=f"merchant-{i}",
            merchant_name=f"Satici {i}",
            price=Decimal(f"{100 + i * 50}.00"),
            buybox_order=1,
            snapshot_date=datetime.utcnow(),
        )
        db_session.add(snapshot)
        products.append(product)

    db_session.flush()
    return products


class TestSearchProductsByNameReturnFormat:
    """Return formati geriye uyumlu olmali."""

    @pytest.mark.asyncio
    async def test_returns_expected_keys(
        self, db_session, test_user, products_with_snapshots
    ):
        """Yanit 'bulunan' ve 'urunler' anahtarlarini icermeli."""
        from app.services.ai_tools.search_tools import search_products_by_name

        result = await search_products_by_name(
            user_id=str(test_user.id),
            db=db_session,
            product_name="Cila",
        )
        assert "bulunan" in result
        assert "urunler" in result
        assert isinstance(result["urunler"], list)
        assert result["bulunan"] > 0

    @pytest.mark.asyncio
    async def test_product_item_has_all_fields(
        self, db_session, test_user, products_with_snapshots
    ):
        """Her urun ogesi tum gereken alanlara sahip olmali."""
        from app.services.ai_tools.search_tools import search_products_by_name

        result = await search_products_by_name(
            user_id=str(test_user.id),
            db=db_session,
            product_name="Sonax",
        )
        assert result["bulunan"] >= 1

        item = result["urunler"][0]
        expected_keys = {
            "sku", "urun_adi", "platform", "urun_id",
            "mevcut_fiyat", "buybox_satici", "gorsel", "urun_url",
        }
        assert expected_keys.issubset(item.keys())
        assert item["sku"] == "SKU-000"
        assert item["urun_adi"] == "Sonax Hizli Cila 500ml"
        assert item["platform"] == "hepsiburada"
        assert item["mevcut_fiyat"] == 100.0

    @pytest.mark.asyncio
    async def test_no_match_returns_mesaj(self, db_session, test_user):
        """Eslesme yoksa 'mesaj' anahtari donmeli."""
        from app.services.ai_tools.search_tools import search_products_by_name

        result = await search_products_by_name(
            user_id=str(test_user.id),
            db=db_session,
            product_name="VarOlmayanUrun12345",
        )
        assert "mesaj" in result

    @pytest.mark.asyncio
    async def test_empty_product_name_returns_hata(self, db_session, test_user):
        """Bos product_name icin hata donmeli."""
        from app.services.ai_tools.search_tools import search_products_by_name

        result = await search_products_by_name(
            user_id=str(test_user.id),
            db=db_session,
            product_name="",
        )
        assert "hata" in result


class TestSearchWithPlatformFilter:
    """Platform filtresi calismali."""

    @pytest.mark.asyncio
    async def test_platform_filter(
        self, db_session, test_user, products_with_snapshots
    ):
        """Platform filtresi sonuclari daraltmali."""
        from app.services.ai_tools.search_tools import search_products_by_name

        # Tum urunler hepsiburada — platform filtresi ile bulmali
        result = await search_products_by_name(
            user_id=str(test_user.id),
            db=db_session,
            product_name="Cila",
            platform="hepsiburada",
        )
        assert result.get("bulunan", 0) >= 1
        for item in result.get("urunler", []):
            assert item["platform"] == "hepsiburada"

    @pytest.mark.asyncio
    async def test_wrong_platform_no_results(
        self, db_session, test_user, products_with_snapshots
    ):
        """Yanlis platform bos sonuc donmeli."""
        from app.services.ai_tools.search_tools import search_products_by_name

        result = await search_products_by_name(
            user_id=str(test_user.id),
            db=db_session,
            product_name="Sonax",
            platform="trendyol",  # Sonax hepsiburada'da
        )
        assert "mesaj" in result or result.get("bulunan", 0) == 0
