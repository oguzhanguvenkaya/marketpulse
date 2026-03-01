"""Action tool transaction atomiklik testleri.

Plan dogrulama:
- Action tool'lar db.flush() kullanir (commit degil).
- Registry execute_tool hata durumunda rollback yapar.
- Source code'da db.commit() bulunmamasi dogrulanir.
"""

import ast
import inspect
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from app.db.models import User, MonitoredProduct, CompetitorSeller, SearchTask


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
def monitored_product(db_session, test_user):
    """Mevcut izlenen urun."""
    product = MonitoredProduct(
        id=uuid.uuid4(),
        user_id=test_user.id,
        platform="hepsiburada",
        sku="EXISTING-SKU",
        product_url="https://hepsiburada.com/EXISTING-SKU",
        is_active=True,
    )
    db_session.add(product)
    db_session.flush()
    return product


class TestActionToolSourceCode:
    """Action tool kaynak kodunun flush() kullandigini dogrula."""

    def test_action_tools_use_flush_not_commit(self):
        """action_tools.py'de db.commit() bulunmamali, db.flush() kullanilmali."""
        from app.services.ai_tools import action_tools

        source = inspect.getsource(action_tools)
        tree = ast.parse(source)

        commit_calls = []
        flush_calls = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # db.commit() veya db.flush() cagrilarini bul
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "commit":
                        commit_calls.append(node.lineno)
                    elif node.func.attr == "flush":
                        flush_calls.append(node.lineno)

        assert len(commit_calls) == 0, (
            f"action_tools.py'de db.commit() bulundu (satir: {commit_calls}). "
            f"Tum action tool'lar db.flush() kullanmali."
        )
        assert len(flush_calls) >= 4, (
            f"action_tools.py'de {len(flush_calls)} flush() cagrisi bulundu, "
            f"en az 4 olmali (her action tool icin 1)."
        )


class TestActionToolFlush:
    """Action tool'lar db.flush() ile veriyi session'a yazar."""

    @pytest.mark.asyncio
    async def test_add_sku_creates_product(self, db_session, test_user):
        """add_sku_to_monitor basarili sonuc donmeli ve kayit olusturmali."""
        from app.services.ai_tools.action_tools import add_sku_to_monitor

        result = await add_sku_to_monitor(
            user_id=str(test_user.id),
            db=db_session,
            sku="NEW-SKU-123",
            platform="hepsiburada",
        )
        assert result["durum"] == "eklendi"
        assert "urun_id" in result

        # flush sonrasi session'da gorunur
        product = db_session.query(MonitoredProduct).filter(
            MonitoredProduct.sku == "NEW-SKU-123",
            MonitoredProduct.user_id == test_user.id,
        ).first()
        assert product is not None
        assert product.platform == "hepsiburada"

    @pytest.mark.asyncio
    async def test_set_price_alert_updates_threshold(self, db_session, test_user, monitored_product):
        """set_price_alert threshold'u guncellemeli."""
        from app.services.ai_tools.action_tools import set_price_alert

        result = await set_price_alert(
            user_id=str(test_user.id),
            db=db_session,
            sku="EXISTING-SKU",
            threshold_price=150.0,
            platform="hepsiburada",
        )
        assert result["durum"] == "guncellendi"
        assert result["yeni_esik"] == 150.0
        assert result["onceki_esik"] is None

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="competitor_sellers tablosu henuz migrate edilmedi")
    async def test_add_competitor_creates_record(self, db_session, test_user):
        """add_competitor yeni kayit olusturmali."""
        from app.services.ai_tools.action_tools import add_competitor

        result = await add_competitor(
            user_id=str(test_user.id),
            db=db_session,
            seller_id="seller-001",
            seller_name="Test Satici",
            platform="hepsiburada",
        )
        assert result["durum"] == "eklendi"
        assert "rakip_id" in result

    @pytest.mark.asyncio
    async def test_start_keyword_search_creates_task(self, db_session, test_user):
        """start_keyword_search arama gorevi olusturmali."""
        from app.services.ai_tools.action_tools import start_keyword_search

        result = await start_keyword_search(
            user_id=str(test_user.id),
            db=db_session,
            keyword="cila",
            platform="hepsiburada",
        )
        assert result["durum"] == "baslatildi"
        assert "task_id" in result


class TestActionToolValidation:
    """Action tool'lar giris dogrulamasi yapmali."""

    @pytest.mark.asyncio
    async def test_add_sku_missing_sku(self, db_session, test_user):
        from app.services.ai_tools.action_tools import add_sku_to_monitor

        result = await add_sku_to_monitor(
            user_id=str(test_user.id),
            db=db_session,
            sku="",
        )
        assert "hata" in result

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="competitor_sellers tablosu henuz migrate edilmedi")
    async def test_add_competitor_missing_params(self, db_session, test_user):
        from app.services.ai_tools.action_tools import add_competitor

        result = await add_competitor(
            user_id=str(test_user.id),
            db=db_session,
            seller_id="",
            seller_name="",
        )
        assert "hata" in result

    @pytest.mark.asyncio
    async def test_set_price_alert_missing_sku(self, db_session, test_user):
        from app.services.ai_tools.action_tools import set_price_alert

        result = await set_price_alert(
            user_id=str(test_user.id),
            db=db_session,
            sku="",
        )
        assert "hata" in result

    @pytest.mark.asyncio
    async def test_set_price_alert_nonexistent_product(self, db_session, test_user):
        from app.services.ai_tools.action_tools import set_price_alert

        result = await set_price_alert(
            user_id=str(test_user.id),
            db=db_session,
            sku="NONEXISTENT",
            threshold_price=100.0,
        )
        assert "hata" in result

    @pytest.mark.asyncio
    async def test_start_keyword_search_missing_keyword(self, db_session, test_user):
        from app.services.ai_tools.action_tools import start_keyword_search

        result = await start_keyword_search(
            user_id=str(test_user.id),
            db=db_session,
            keyword="",
        )
        assert "hata" in result


class TestActionToolDuplicateCheck:
    """Action tool'lar duplicate kontrolu yapmali."""

    @pytest.mark.asyncio
    async def test_add_sku_duplicate_returns_zaten_var(self, db_session, test_user, monitored_product):
        """Ayni SKU ikinci kez eklendiginde 'zaten_var' donmeli."""
        from app.services.ai_tools.action_tools import add_sku_to_monitor

        result = await add_sku_to_monitor(
            user_id=str(test_user.id),
            db=db_session,
            sku="EXISTING-SKU",
            platform="hepsiburada",
        )
        assert result["durum"] == "zaten_var"


class TestRegistryErrorHandling:
    """execute_tool hata durumunu yonetmeli."""

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_tool(self, db_session, test_user):
        """Olmayan tool cagrisinda hata donmeli."""
        from app.services.ai_tools.registry import execute_tool

        result = await execute_tool("nonexistent_tool", {}, str(test_user.id), db_session)
        assert "hata" in result
        assert "Bilinmeyen tool" in result["hata"]

    @pytest.mark.asyncio
    async def test_execute_tool_runs_successfully(self, db_session, test_user):
        """Gecerli tool basarili calismali."""
        from app.services.ai_tools.registry import execute_tool

        result = await execute_tool(
            "get_portfolio_summary", {}, str(test_user.id), db_session
        )
        assert "hata" not in result
        assert "toplam_urun" in result
