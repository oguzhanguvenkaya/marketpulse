"""Price Monitor Fetch — endpoint ve servis katmani testleri.

Kapsam:
- POST /price-monitor/fetch (start task)
- GET  /price-monitor/fetch/{task_id} (status polling)
- POST /price-monitor/fetch/{task_id}/stop (stop task)
- POST /price-monitor/fetch-single/{product_id} (single product fetch)
- GET  /price-monitor/last-inactive
- PriceMonitorService.parse_listings
- PriceMonitorService.fetch_product_data (mock HTTP)
- PriceMonitorService.save_product_result
- PriceMonitorService.fetch_all_products (integration)
"""

import uuid
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from app.main import app
from app.core.auth import get_current_user
from app.core.config import settings
from app.db.models import User, MonitoredProduct, SellerSnapshot, PriceMonitorTask
from app.services.price_monitor_service import PriceMonitorService


# ────────────────────────────── fixtures ──────────────────────────────

@pytest.fixture()
def test_user(db_session):
    """Test kullanicisi olustur."""
    user = User(
        id=uuid.uuid4(),
        email=f"pm-test-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Price Monitor Test User",
        plan_tier="pro",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def auth_override(test_user):
    """Supabase JWT auth'u bypass et."""
    async def mock_user():
        return test_user
    app.dependency_overrides[get_current_user] = mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def sample_products(db_session, test_user):
    """3 adet aktif monitored product olustur."""
    products = []
    for i in range(3):
        p = MonitoredProduct(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            sku=f"HB-SKU-{i:03d}",
            product_url=f"https://www.hepsiburada.com/test-product-p-HB-SKU-{i:03d}",
            product_name=f"Test Product {i}",
            brand="TestBrand",
            is_active=True,
        )
        db_session.add(p)
        products.append(p)
    db_session.flush()
    return products


@pytest.fixture()
def inactive_products(db_session, test_user):
    """2 adet inactive monitored product olustur."""
    products = []
    for i in range(2):
        p = MonitoredProduct(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            sku=f"HB-INACTIVE-{i:03d}",
            product_url=f"https://www.hepsiburada.com/inactive-p-HB-INACTIVE-{i:03d}",
            product_name=f"Inactive Product {i}",
            brand="TestBrand",
            is_active=False,
        )
        db_session.add(p)
        products.append(p)
    db_session.flush()
    return products


@pytest.fixture()
def trendyol_products(db_session, test_user):
    """2 adet Trendyol ürünü olustur."""
    products = []
    for i in range(2):
        p = MonitoredProduct(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="trendyol",
            sku=f"TY-SKU-{i:03d}",
            product_url=f"https://www.trendyol.com/test-product-p-{100000 + i}",
            product_name=f"Trendyol Product {i}",
            brand="TYBrand",
            is_active=True,
        )
        db_session.add(p)
        products.append(p)
    db_session.flush()
    return products


@pytest.fixture()
def completed_task_with_inactive(db_session, test_user, inactive_products):
    """Completed task with last_inactive_skus set."""
    task = PriceMonitorTask(
        id=uuid.uuid4(),
        user_id=test_user.id,
        platform="hepsiburada",
        status="completed",
        total_products=5,
        completed_products=3,
        failed_products=2,
        fetch_type="active",
        last_inactive_skus=[p.sku for p in inactive_products],
        completed_at=datetime.utcnow() + timedelta(hours=1),  # Future date to ensure most recent
    )
    db_session.add(task)
    db_session.flush()
    return task


@pytest.fixture()
def price_monitor_service():
    """Fresh PriceMonitorService instance."""
    return PriceMonitorService()


# ────────────────── sample API response data ──────────────────

SAMPLE_LISTINGS_RESPONSE = {
    "statusCode": 200,
    "data": {
        "listings": [
            {
                "listingId": "listing-001",
                "merchantId": "merchant-001",
                "merchantName": "Seller A",
                "merchantLogo": "https://cdn.hepsiburada.com/logo-a.png",
                "merchantUrlPostfix": "/seller-a",
                "merchantCity": "Istanbul",
                "price": {"value": 199.99},
                "originalPrice": {"value": 249.99},
                "minimumPrice": {"value": 189.99},
                "discountRate": 20.0,
                "quantity": 50,
                "buyboxOrder": 0,
                "freeShipping": True,
                "fastShipping": False,
                "isFulfilledByHB": True,
                "ratingSummary": {
                    "lifetimeRating": 4.5,
                    "ratingQuantity": 1200,
                },
                "tagList": [],
            },
            {
                "listingId": "listing-002",
                "merchantId": "merchant-002",
                "merchantName": "Seller B",
                "merchantLogo": "https://cdn.hepsiburada.com/logo-b.png",
                "merchantUrlPostfix": "/seller-b",
                "merchantCity": "Ankara",
                "price": {"value": 209.99},
                "originalPrice": {"value": 249.99},
                "minimumPrice": {"value": 195.00},
                "discountRate": 16.0,
                "quantity": 30,
                "buyboxOrder": 1,
                "freeShipping": False,
                "fastShipping": True,
                "isFulfilledByHB": False,
                "ratingSummary": {
                    "lifetimeRating": 3.8,
                    "ratingQuantity": 450,
                },
                "tagList": [
                    {"tagId": "sepette-10-indirim", "tagName": "10% indirim"},
                ],
            },
        ]
    },
}

SAMPLE_LISTINGS_WITH_CAMPAIGN = {
    "statusCode": 200,
    "data": {
        "listings": [
            {
                "listingId": "listing-003",
                "merchantId": "merchant-003",
                "merchantName": "Campaign Seller",
                "price": {"value": 399.99},
                "originalPrice": {"value": 499.99},
                "minimumPrice": {"value": 350.00},
                "discountRate": 20.0,
                "quantity": 10,
                "buyboxOrder": 0,
                "freeShipping": True,
                "fastShipping": False,
                "isFulfilledByHB": False,
                "ratingSummary": {},
                "tagList": [
                    {"tagId": "sepette-5-indirim", "tagName": "5% indirim"},
                    {"tagId": "500-tl-ye-50-tl-indirim", "tagName": "500 TL'ye 50 TL kupon"},
                ],
            },
        ]
    },
}


# ────────────────── Phase 1: Service Unit Tests ──────────────────


class TestParseListings:
    """PriceMonitorService.parse_listings unit testleri."""

    def test_parse_valid_listings(self, price_monitor_service):
        sellers = price_monitor_service.parse_listings(SAMPLE_LISTINGS_RESPONSE["data"])
        assert len(sellers) == 2

        seller_a = sellers[0]
        assert seller_a["merchant_id"] == "merchant-001"
        assert seller_a["merchant_name"] == "Seller A"
        assert seller_a["price"] == 199.99
        assert seller_a["original_price"] == 249.99
        assert seller_a["minimum_price"] == 189.99
        assert seller_a["buybox_order"] == 0
        assert seller_a["free_shipping"] is True
        assert seller_a["is_fulfilled_by_hb"] is True
        assert seller_a["merchant_rating"] == 4.5
        assert seller_a["merchant_rating_count"] == 1200
        assert seller_a["has_percentage_discount"] is False

        seller_b = sellers[1]
        assert seller_b["merchant_id"] == "merchant-002"
        assert seller_b["price"] == 209.99
        assert seller_b["buybox_order"] == 1
        assert seller_b["has_percentage_discount"] is True

    def test_parse_empty_listings(self, price_monitor_service):
        sellers = price_monitor_service.parse_listings({"listings": []})
        assert sellers == []

    def test_parse_missing_listings_key(self, price_monitor_service):
        sellers = price_monitor_service.parse_listings({})
        assert sellers == []

    def test_parse_campaign_tags_filtering(self, price_monitor_service):
        sellers = price_monitor_service.parse_listings(SAMPLE_LISTINGS_WITH_CAMPAIGN["data"])
        assert len(sellers) == 1
        seller = sellers[0]
        assert seller["has_percentage_discount"] is True
        assert len(seller["campaigns"]) >= 1


class TestCampaignTagDetection:
    """Tag algılama helper metotlarinin unit testleri."""

    def test_has_percentage_discount_true(self, price_monitor_service):
        tags = [{"tagId": "sepette-5-indirim"}]
        assert price_monitor_service._has_percentage_discount(tags) is True

    def test_has_percentage_discount_false_for_coupon(self, price_monitor_service):
        tags = [{"tagId": "500-tl-ye-50-tl-indirim"}]
        assert price_monitor_service._has_percentage_discount(tags) is False

    def test_has_percentage_discount_false_for_bundle(self, price_monitor_service):
        tags = [{"tagId": "2-urune-1-indirim"}]
        assert price_monitor_service._has_percentage_discount(tags) is False

    def test_has_campaign_in_tags(self, price_monitor_service):
        tags = [{"tagId": "ozel-kampanya"}]
        assert price_monitor_service._has_campaign_in_tags(tags) is True

    def test_no_campaign_in_tags(self, price_monitor_service):
        tags = [{"tagId": "yeni-urun"}]
        assert price_monitor_service._has_campaign_in_tags(tags) is False

    def test_empty_tags(self, price_monitor_service):
        assert price_monitor_service._has_percentage_discount([]) is False
        assert price_monitor_service._has_campaign_in_tags([]) is False


class TestSaveProductResult:
    """save_product_result unit testleri."""

    def test_save_successful_result(self, db_session, price_monitor_service, sample_products):
        product = sample_products[0]
        result = {
            "product_id": str(product.id),
            "sku": product.sku,
            "success": True,
            "inactive": False,
            "sellers": [
                {
                    "merchant_id": "m-001",
                    "merchant_name": "Test Seller",
                    "price": 199.99,
                    "original_price": 249.99,
                    "minimum_price": 189.99,
                    "discount_rate": 20.0,
                    "stock_quantity": 10,
                    "buybox_order": 0,
                    "free_shipping": True,
                    "fast_shipping": False,
                    "is_fulfilled_by_hb": True,
                    "campaigns": ["5% indirim"],
                    "campaign_price": 189.99,
                },
            ],
            "error": None,
        }

        success = price_monitor_service.save_product_result(db_session, product, result)
        db_session.flush()

        assert success is True
        assert product.last_fetched_at is not None

        snapshots = db_session.query(SellerSnapshot).filter(
            SellerSnapshot.monitored_product_id == product.id
        ).all()
        assert len(snapshots) == 1
        assert snapshots[0].merchant_name == "Test Seller"
        assert float(snapshots[0].price) == 199.99
        assert float(snapshots[0].campaign_price) == 189.99
        assert snapshots[0].free_shipping is True

    def test_save_inactive_result_marks_product(self, db_session, price_monitor_service, sample_products):
        product = sample_products[0]
        assert product.is_active is True

        result = {
            "product_id": str(product.id),
            "sku": product.sku,
            "success": False,
            "inactive": True,
            "sellers": [],
            "error": "no_data",
        }

        success = price_monitor_service.save_product_result(db_session, product, result)
        assert success is False
        assert product.is_active is False

    def test_save_reactivates_inactive_product(self, db_session, price_monitor_service, inactive_products):
        product = inactive_products[0]
        assert product.is_active is False

        result = {
            "product_id": str(product.id),
            "sku": product.sku,
            "success": True,
            "inactive": False,
            "sellers": [
                {
                    "merchant_id": "m-reactivate",
                    "merchant_name": "Reactivation Seller",
                    "price": 99.99,
                    "buybox_order": 0,
                    "free_shipping": False,
                    "fast_shipping": False,
                    "is_fulfilled_by_hb": False,
                    "campaigns": [],
                },
            ],
            "error": None,
        }

        success = price_monitor_service.save_product_result(db_session, product, result)
        assert success is True
        assert product.is_active is True

    def test_save_failed_result_does_nothing(self, db_session, price_monitor_service, sample_products):
        product = sample_products[0]
        result = {
            "product_id": str(product.id),
            "sku": product.sku,
            "success": False,
            "inactive": False,
            "sellers": [],
            "error": "upstream_error",
        }

        success = price_monitor_service.save_product_result(db_session, product, result)
        assert success is False
        assert product.is_active is True  # unchanged


class TestFetchProductData:
    """fetch_product_data — mock HTTP istekleri."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self, price_monitor_service, sample_products):
        product = sample_products[0]

        with patch.object(price_monitor_service, "fetch_listings", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "success": True,
                "data": SAMPLE_LISTINGS_RESPONSE["data"],
                "error_type": None,
                "status_code": 200,
            }

            result = await price_monitor_service.fetch_product_data(product)

            assert result["success"] is True
            assert len(result["sellers"]) == 2
            assert result["inactive"] is False

    @pytest.mark.asyncio
    async def test_fetch_no_data_marks_inactive(self, price_monitor_service, sample_products):
        product = sample_products[0]

        with patch.object(price_monitor_service, "fetch_listings", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "success": False,
                "data": None,
                "error_type": "no_data",
                "status_code": 404,
            }

            result = await price_monitor_service.fetch_product_data(product)

            assert result["success"] is False
            assert result["inactive"] is True

    @pytest.mark.asyncio
    async def test_fetch_auth_error(self, price_monitor_service, sample_products):
        product = sample_products[0]

        with patch.object(price_monitor_service, "fetch_listings", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "success": False,
                "data": None,
                "error_type": "auth_error",
                "status_code": 401,
            }

            result = await price_monitor_service.fetch_product_data(product)

            assert result["success"] is False
            assert result["inactive"] is False  # auth error should NOT mark inactive

    @pytest.mark.asyncio
    async def test_fetch_upstream_error(self, price_monitor_service, sample_products):
        product = sample_products[0]

        with patch.object(price_monitor_service, "fetch_listings", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "success": False,
                "data": None,
                "error_type": "upstream_error",
                "status_code": 500,
            }

            result = await price_monitor_service.fetch_product_data(product)

            assert result["success"] is False
            assert result["inactive"] is False  # upstream error should NOT mark inactive

    @pytest.mark.asyncio
    async def test_fetch_empty_sellers_marks_inactive(self, price_monitor_service, sample_products):
        product = sample_products[0]

        with patch.object(price_monitor_service, "fetch_listings", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "success": True,
                "data": {"listings": []},
                "error_type": None,
                "status_code": 200,
            }

            result = await price_monitor_service.fetch_product_data(product)

            assert result["success"] is False
            assert result["inactive"] is True

    @pytest.mark.asyncio
    async def test_fetch_with_campaign_api(self, price_monitor_service, sample_products):
        """Yüzde indirimli satıcı için Campaign API çağrılır."""
        product = sample_products[0]

        with patch.object(price_monitor_service, "fetch_listings", new_callable=AsyncMock) as mock_fetch, \
             patch.object(price_monitor_service, "fetch_campaign_price", new_callable=AsyncMock) as mock_campaign:

            mock_fetch.return_value = {
                "success": True,
                "data": SAMPLE_LISTINGS_WITH_CAMPAIGN["data"],
                "error_type": None,
                "status_code": 200,
            }
            mock_campaign.return_value = {
                "discounted_price": 379.99,
                "final_price": 379.99,
                "campaign_text": "%5 indirim",
                "campaigns": [],
            }

            result = await price_monitor_service.fetch_product_data(product)

            assert result["success"] is True
            assert len(result["sellers"]) == 1
            mock_campaign.assert_called_once()

            seller = result["sellers"][0]
            assert seller["campaign_price"] == 379.99
            assert seller["price"] == 379.99


class TestFetchListings:
    """fetch_listings — ScraperAPI HTTP çağrısı mock'u."""

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_auth_error(self):
        svc = PriceMonitorService()
        with patch.object(type(svc), "api_key", new_callable=lambda: property(lambda self: "")):
            result = await svc.fetch_listings("TEST-SKU")
            assert result["success"] is False
            assert result["error_type"] == "auth_error"


# ────────────────── Phase 2: Endpoint Tests ──────────────────


class TestStartFetchEndpoint:
    """POST /price-monitor/fetch endpoint testleri."""

    def test_start_fetch_requires_auth(self, client):
        """Auth olmadan 401 dönmeli."""
        response = client.post("/api/price-monitor/fetch", params={"platform": "hepsiburada"})
        assert response.status_code == 401

    def test_start_fetch_no_scraper_key_returns_503(self, client, auth_override, sample_products):
        """SCRAPER_API_KEY yoksa 503 dönmeli."""
        with patch.object(settings, "SCRAPER_API_KEY", ""):
            response = client.post("/api/price-monitor/fetch", params={"platform": "hepsiburada"})
            assert response.status_code == 503

    def test_start_fetch_success_local_executor(self, client, auth_override, db_session, sample_products):
        """Local executor ile başarılı task başlatma."""
        with patch.object(settings, "SCRAPER_API_KEY", "test-key-123"), \
             patch.object(settings, "PRICE_MONITOR_EXECUTOR", "local"), \
             patch("app.api.price_monitor_routes.settings") as mock_settings, \
             patch("app.api.price_monitor_routes.asyncio") as mock_asyncio:

            mock_settings.SCRAPER_API_KEY = "test-key-123"
            mock_settings.price_monitor_executor.return_value = "local"

            response = client.post(
                "/api/price-monitor/fetch",
                params={"platform": "hepsiburada", "fetch_type": "active"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["platform"] == "hepsiburada"
            assert data["fetch_type"] == "active"
            assert data["status"] == "started"

    def test_start_fetch_creates_task_in_db(self, client, auth_override, db_session, sample_products):
        """Task DB'de oluşturulmalı."""
        with patch.object(settings, "SCRAPER_API_KEY", "test-key-123"), \
             patch("app.api.price_monitor_routes.settings") as mock_settings, \
             patch("app.api.price_monitor_routes.asyncio"):

            mock_settings.SCRAPER_API_KEY = "test-key-123"
            mock_settings.price_monitor_executor.return_value = "local"

            response = client.post(
                "/api/price-monitor/fetch",
                params={"platform": "hepsiburada"},
            )
            task_id = response.json()["task_id"]

            task = db_session.query(PriceMonitorTask).filter(
                PriceMonitorTask.id == task_id
            ).first()
            assert task is not None
            assert task.platform == "hepsiburada"
            assert task.status == "pending"


class TestFetchTaskStatusEndpoint:
    """GET /price-monitor/fetch/{task_id} endpoint testleri."""

    def test_get_status_running_task(self, client, auth_override, db_session, test_user):
        task = PriceMonitorTask(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            status="running",
            total_products=10,
            completed_products=5,
            failed_products=1,
            fetch_type="active",
        )
        db_session.add(task)
        db_session.flush()

        response = client.get(f"/api/price-monitor/fetch/{task.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["total_products"] == 10
        assert data["completed_products"] == 5
        assert data["failed_products"] == 1
        assert data["fetch_type"] == "active"

    def test_get_status_completed_task(self, client, auth_override, db_session, test_user):
        task = PriceMonitorTask(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            status="completed",
            total_products=10,
            completed_products=8,
            failed_products=2,
            fetch_type="active",
            last_inactive_skus=["SKU-A", "SKU-B"],
            completed_at=datetime.utcnow(),
        )
        db_session.add(task)
        db_session.flush()

        response = client.get(f"/api/price-monitor/fetch/{task.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["last_inactive_count"] == 2
        assert data["completed_at"] is not None

    def test_get_status_nonexistent_task(self, client, auth_override):
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/price-monitor/fetch/{fake_id}")
        assert response.status_code == 404


class TestStopFetchEndpoint:
    """POST /price-monitor/fetch/{task_id}/stop endpoint testleri."""

    def test_stop_running_task(self, client, auth_override, db_session, test_user):
        task = PriceMonitorTask(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            status="running",
            total_products=10,
            completed_products=3,
        )
        db_session.add(task)
        db_session.flush()

        response = client.post(f"/api/price-monitor/fetch/{task.id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        db_session.refresh(task)
        assert task.stop_requested is True

    def test_stop_completed_task_returns_400(self, client, auth_override, db_session, test_user):
        task = PriceMonitorTask(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            status="completed",
            completed_at=datetime.utcnow(),
        )
        db_session.add(task)
        db_session.flush()

        response = client.post(f"/api/price-monitor/fetch/{task.id}/stop")
        assert response.status_code == 400

    def test_stop_nonexistent_task_returns_404(self, client, auth_override):
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/price-monitor/fetch/{fake_id}/stop")
        assert response.status_code == 404


class TestFetchSingleProductEndpoint:
    """POST /price-monitor/fetch-single/{product_id} endpoint testleri."""

    def test_fetch_single_requires_auth(self, client, sample_products):
        response = client.post(f"/api/price-monitor/fetch-single/{sample_products[0].id}")
        assert response.status_code == 401

    def test_fetch_single_success(self, client, auth_override, db_session, sample_products):
        product = sample_products[0]

        with patch.object(settings, "SCRAPER_API_KEY", "test-key-123"), \
             patch("app.api.price_monitor_routes._require_scraper_api_or_503"), \
             patch("app.api.price_monitor_routes._get_price_monitor_service") as mock_get_svc:

            mock_svc = AsyncMock()
            mock_svc.fetch_and_save_product = AsyncMock(return_value=True)
            mock_get_svc.return_value = mock_svc

            response = client.post(f"/api/price-monitor/fetch-single/{product.id}")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_fetch_single_nonexistent_product(self, client, auth_override):
        fake_id = str(uuid.uuid4())

        with patch("app.api.price_monitor_routes._require_scraper_api_or_503"):
            response = client.post(f"/api/price-monitor/fetch-single/{fake_id}")
            assert response.status_code == 404

    def test_fetch_single_service_failure(self, client, auth_override, db_session, sample_products):
        product = sample_products[0]

        with patch("app.api.price_monitor_routes._require_scraper_api_or_503"), \
             patch("app.api.price_monitor_routes._get_price_monitor_service") as mock_get_svc:

            mock_svc = AsyncMock()
            mock_svc.fetch_and_save_product = AsyncMock(return_value=False)
            mock_get_svc.return_value = mock_svc

            response = client.post(f"/api/price-monitor/fetch-single/{product.id}")
            assert response.status_code == 500


class TestLastInactiveEndpoint:
    """GET /price-monitor/last-inactive endpoint testleri."""

    def test_last_inactive_response_structure(self, client, auth_override, db_session):
        """last-inactive response'u doğru yapıda olmalı."""
        response = client.get("/api/price-monitor/last-inactive", params={"platform": "hepsiburada"})
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "skus" in data
        assert isinstance(data["skus"], list)
        assert isinstance(data["count"], int)
        assert data["count"] >= 0

    def test_last_inactive_with_completed_task(
        self, client, auth_override, db_session, completed_task_with_inactive, inactive_products
    ):
        response = client.get("/api/price-monitor/last-inactive", params={"platform": "hepsiburada"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["skus"]) == 2
        assert len(data["products"]) == 2
        assert data["task_id"] == str(completed_task_with_inactive.id)


# ────────────────── Phase 3: Integration Tests ──────────────────


def _make_success_result(product):
    """Helper: başarılı fetch sonucu üret."""
    return {
        "product_id": product.id,
        "sku": product.sku,
        "success": True,
        "inactive": False,
        "sellers": [
            {
                "merchant_id": "m-001",
                "merchant_name": "Int Test Seller",
                "price": 99.99,
                "buybox_order": 0,
                "free_shipping": True,
                "fast_shipping": False,
                "is_fulfilled_by_hb": False,
                "campaigns": [],
            },
        ],
        "error": None,
    }


class TestFetchAllProductsIntegration:
    """fetch_all_products — mock HTTP ile full integration testi.

    NOT: Gerçek DB'de başka ürünler olduğu için product_ids ile sınırlıyoruz.
    """

    @pytest.mark.asyncio
    async def test_fetch_all_products_success(self, db_session, sample_products, test_user):
        """Belirtilen aktif ürünler başarıyla çekilmeli."""
        task = PriceMonitorTask(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            status="pending",
            fetch_type="active",
        )
        db_session.add(task)
        db_session.flush()

        product_ids = [str(p.id) for p in sample_products]
        svc = PriceMonitorService()

        async def dynamic_fetch(product):
            return _make_success_result(product)

        with patch.object(svc, "fetch_product_data", side_effect=dynamic_fetch), \
             patch.object(svc, "_check_alerts_for_products", new_callable=AsyncMock):
            await svc.fetch_all_products(db_session, task, product_ids, "hepsiburada", "active")

        db_session.refresh(task)
        assert task.status == "completed"
        assert task.completed_products == 3
        assert task.failed_products == 0
        assert task.completed_at is not None

        total_snapshots = db_session.query(SellerSnapshot).filter(
            SellerSnapshot.monitored_product_id.in_([p.id for p in sample_products])
        ).count()
        assert total_snapshots == 3

    @pytest.mark.asyncio
    async def test_fetch_all_with_inactive_tracking(self, db_session, sample_products, test_user):
        """Inactive ürünler last_inactive_skus'ta kaydedilmeli."""
        task = PriceMonitorTask(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            status="pending",
            fetch_type="active",
        )
        db_session.add(task)
        db_session.flush()

        product_ids = [str(p.id) for p in sample_products]
        svc = PriceMonitorService()

        call_count = 0

        async def mixed_fetch(product):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return {
                    "product_id": product.id,
                    "sku": product.sku,
                    "success": False,
                    "inactive": True,
                    "sellers": [],
                    "error": "no_data",
                }
            return _make_success_result(product)

        with patch.object(svc, "fetch_product_data", side_effect=mixed_fetch), \
             patch.object(svc, "_check_alerts_for_products", new_callable=AsyncMock):
            await svc.fetch_all_products(db_session, task, product_ids, "hepsiburada", "active")

        db_session.refresh(task)
        assert task.status == "completed"
        assert task.completed_products == 2
        assert task.failed_products == 1
        assert len(task.last_inactive_skus) == 1

    @pytest.mark.asyncio
    async def test_fetch_all_empty_product_ids(self, db_session, test_user):
        """Boş product_ids listesi verildiğinde task hemen completed olmalı."""
        task = PriceMonitorTask(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            status="pending",
            fetch_type="active",
        )
        db_session.add(task)
        db_session.flush()

        svc = PriceMonitorService()
        # Non-existent product IDs → no products matched
        fake_ids = [str(uuid.uuid4())]
        await svc.fetch_all_products(db_session, task, fake_ids, "hepsiburada", "active")

        db_session.refresh(task)
        assert task.status == "completed"
        assert task.total_products == 0

    @pytest.mark.asyncio
    async def test_fetch_all_stop_requested(self, db_session, sample_products, test_user):
        """stop_requested=True olduğunda task durmalı."""
        task = PriceMonitorTask(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            status="pending",
            fetch_type="active",
            stop_requested=True,
        )
        db_session.add(task)
        db_session.flush()

        product_ids = [str(p.id) for p in sample_products]
        svc = PriceMonitorService()

        with patch.object(svc, "fetch_product_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = _make_success_result(sample_products[0])
            await svc.fetch_all_products(db_session, task, product_ids, "hepsiburada", "active")

        db_session.refresh(task)
        assert task.status == "stopped"

    def test_inactive_fetch_type_queries_inactive_products(self, db_session, inactive_products, sample_products):
        """fetch_type='inactive' query'si sadece is_active=False olan ürünleri döndürmeli.

        NOT: Tam fetch_all_products çağrısı gerçek DB'deki tüm inactive ürünleri
        çekeceği için burada sadece query mantığını doğruluyoruz.
        """
        # Inactive query
        inactive_results = db_session.query(MonitoredProduct).filter(
            MonitoredProduct.platform == "hepsiburada",
            MonitoredProduct.is_active == False
        ).all()

        inactive_ids = {str(p.id) for p in inactive_results}
        # Test inactive ürünlerimiz sonuçlarda olmalı
        for p in inactive_products:
            assert str(p.id) in inactive_ids

        # Test active ürünlerimiz sonuçlarda OLMAMALI
        for p in sample_products:
            assert str(p.id) not in inactive_ids


class TestFetchAllProductsLastInactive:
    """fetch_type='last_inactive' senaryosu."""

    def test_last_inactive_query_uses_most_recent_task(
        self, db_session, test_user, inactive_products, completed_task_with_inactive
    ):
        """last_inactive fetch — en son completed task'ın SKU'larını hedeflemeli.

        NOT: Tam fetch_all_products çağrısı yerine query mantığını doğruluyoruz
        çünkü gerçek DB'deki task geçmişi test izolasyonunu bozabiliyor.
        """
        # Service'in yapacağı aynı query
        last_task = db_session.query(PriceMonitorTask).filter(
            PriceMonitorTask.platform == "hepsiburada",
            PriceMonitorTask.status == "completed"
        ).order_by(PriceMonitorTask.completed_at.desc()).first()

        assert last_task is not None
        # Fixture'daki task en yeni olmalı (completed_at = now + 1h)
        assert str(last_task.id) == str(completed_task_with_inactive.id)
        assert last_task.last_inactive_skus is not None
        assert len(last_task.last_inactive_skus) == 2

        # Bu SKU'larla eşleşen ürünler bulunmalı
        products = db_session.query(MonitoredProduct).filter(
            MonitoredProduct.sku.in_(last_task.last_inactive_skus),
            MonitoredProduct.platform == "hepsiburada"
        ).all()
        assert len(products) == 2

    @pytest.mark.asyncio
    async def test_last_inactive_fetch_runs(
        self, db_session, test_user, inactive_products, completed_task_with_inactive
    ):
        """last_inactive fetch gerçekten 2 ürünü çekip tamamlamalı."""
        task = PriceMonitorTask(
            id=uuid.uuid4(),
            user_id=test_user.id,
            platform="hepsiburada",
            status="pending",
            fetch_type="last_inactive",
        )
        db_session.add(task)
        db_session.flush()

        svc = PriceMonitorService()

        async def success_fetch(product):
            return _make_success_result(product)

        with patch.object(svc, "fetch_product_data", side_effect=success_fetch), \
             patch.object(svc, "_check_alerts_for_products", new_callable=AsyncMock):
            await svc.fetch_all_products(db_session, task, None, "hepsiburada", "last_inactive")

        db_session.refresh(task)
        assert task.status == "completed"
        assert task.total_products == 2
        assert task.completed_products == 2
