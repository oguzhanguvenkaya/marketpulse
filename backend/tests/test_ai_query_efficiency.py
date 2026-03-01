"""N+1 query regresyon testleri.

Plan dogrulama:
- _get_latest_buybox_map batch subquery ile calismali.
- get_price_alerts, search_products_by_name, _get_monitored_products
  fonksiyonlarinda sorgu sayisi urun adedinden bagimsiz olmali.
"""

import uuid
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from app.db.models import User, MonitoredProduct, SellerSnapshot
from app.services.ai_tools.price_tools import _get_latest_buybox_map


@pytest.fixture()
def test_user(db_session):
    """Test icin kullanici olustur."""
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
    """N adet urun ve her biri icin buybox snapshot olustur."""
    products = []
    for i in range(10):
        product = MonitoredProduct(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            sku=f"SKU-{i:03d}",
            product_url=f"https://hepsiburada.com/SKU-{i:03d}",
            product_name=f"Test Urun {i}",
            threshold_price=Decimal("100.00"),
            is_active=True,
        )
        db_session.add(product)
        db_session.flush()

        # Her urun icin 3 satici snapshot
        for j in range(3):
            snapshot = SellerSnapshot(
                monitored_product_id=product.id,
                merchant_id=f"merchant-{j}",
                merchant_name=f"Satici {j}",
                price=Decimal(f"{90 + j * 10}.00"),
                buybox_order=j + 1,
                snapshot_date=datetime.utcnow(),
            )
            db_session.add(snapshot)

        products.append(product)

    db_session.flush()
    return products


class TestGetLatestBuyboxMap:
    """_get_latest_buybox_map batch query testi."""

    def test_returns_correct_map(self, db_session, products_with_snapshots):
        """Her urun icin dogru buybox (order=1) snapshot donmeli."""
        product_ids = [p.id for p in products_with_snapshots]
        result = _get_latest_buybox_map(db_session, product_ids)

        assert len(result) == 10
        for pid in product_ids:
            assert pid in result
            snapshot = result[pid]
            assert snapshot.buybox_order == 1

    def test_empty_product_ids(self, db_session):
        """Bos product_ids icin bos dict donmeli."""
        result = _get_latest_buybox_map(db_session, [])
        assert result == {}

    def test_nonexistent_product_ids(self, db_session):
        """Olmayan product_ids icin bos dict donmeli."""
        fake_ids = [uuid.uuid4(), uuid.uuid4()]
        result = _get_latest_buybox_map(db_session, fake_ids)
        assert result == {}

    def test_returns_latest_snapshot(self, db_session, test_user):
        """Birden fazla tarih varsa en son snapshot donmeli."""
        product = MonitoredProduct(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            sku="LATEST-TEST",
            product_url="https://hepsiburada.com/LATEST-TEST",
            is_active=True,
        )
        db_session.add(product)
        db_session.flush()

        # Eski snapshot
        old = SellerSnapshot(
            monitored_product_id=product.id,
            merchant_id="m1",
            merchant_name="Eski Satici",
            price=Decimal("100.00"),
            buybox_order=1,
            snapshot_date=datetime.utcnow() - timedelta(days=2),
        )
        db_session.add(old)

        # Yeni snapshot
        new = SellerSnapshot(
            monitored_product_id=product.id,
            merchant_id="m2",
            merchant_name="Yeni Satici",
            price=Decimal("95.00"),
            buybox_order=1,
            snapshot_date=datetime.utcnow(),
        )
        db_session.add(new)
        db_session.flush()

        result = _get_latest_buybox_map(db_session, [product.id])
        assert product.id in result
        assert result[product.id].merchant_name == "Yeni Satici"


class TestQueryEfficiency:
    """Sorgu sayisi urun adedine lineer artmamali."""

    def test_get_price_alerts_query_count(self, db_session, test_user, products_with_snapshots):
        """get_price_alerts sabit sayida sorgu calismali."""
        import asyncio
        from app.services.ai_tools.price_tools import get_price_alerts

        # Sorgu sayisini say
        query_count = 0
        original_execute = db_session.execute.__func__ if hasattr(db_session.execute, '__func__') else None

        queries = []
        from sqlalchemy import event

        @event.listens_for(db_session.get_bind(), "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)

        result = asyncio.get_event_loop().run_until_complete(
            get_price_alerts(str(test_user.id), db_session)
        )

        # 10 urun icin sorgu sayisi 10'dan fazla olmamali
        # (Eski N+1 pattern: 1 + N = 11 sorgu, yeni pattern: ~3-4 sorgu)
        assert len(queries) < 10, f"Beklenenden fazla sorgu: {len(queries)}"

    def test_search_products_by_name_query_count(self, db_session, test_user, products_with_snapshots):
        """search_products_by_name sabit sayida sorgu calismali."""
        import asyncio
        from app.services.ai_tools.search_tools import search_products_by_name

        queries = []
        from sqlalchemy import event

        @event.listens_for(db_session.get_bind(), "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)

        result = asyncio.get_event_loop().run_until_complete(
            search_products_by_name(str(test_user.id), db_session, product_name="Test")
        )

        assert len(queries) < 10, f"Beklenenden fazla sorgu: {len(queries)}"
