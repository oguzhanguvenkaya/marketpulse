"""Tests for HB MORIA JSON parse and Sponsored Brands Display API integration."""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.scraping import ScrapingService


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def scraper():
    return ScrapingService()


@pytest.fixture
def sample_moria_product_organic():
    """A realistic MORIA product dict (organic, no boosting)."""
    return {
        "productId": "HBV00001A2B3C",
        "brand": "TestBrand",
        "customerReviewCount": 245,
        "customerReviewRating": 4.7,
        "boostingFactors": [],
        "variantList": [{
            "name": "TestBrand Premium Pasta Cila 500ml",
            "sku": "HBV00001A2B3C",
            "url": "/testbrand-premium-pasta-cila-500ml-p-HBV00001A2B3C",
            "images": [{"url": "https://productimages.hepsiburada.net/s/123/abc.jpg"}],
            "listing": {
                "merchantName": "Test Mağaza",
                "merchantId": "m-seller-123",
                "priceInfo": {
                    "price": 249.90,
                    "originalPrice": 349.90,
                    "discountRate": 29,
                },
                "campaignPriceInfo": {},
                "campaigns": [{"id": "camp1", "name": "Bahar Kampanyası"}],
                "labels": [],
            },
            "adInfo": None,
            "adShowId": None,
        }],
    }


@pytest.fixture
def sample_moria_product_sponsored():
    """A realistic MORIA product dict (sponsored via boostingFactors)."""
    return {
        "productId": "HBV00004D5E6F",
        "brand": "SponsorBrand",
        "customerReviewCount": 50,
        "customerReviewRating": 4.2,
        "boostingFactors": ["sponsoredProduct"],
        "variantList": [{
            "name": "SponsorBrand Pro Wax 300ml",
            "sku": "HBV00004D5E6F",
            "url": "https://adservice.hepsiburada.com/v2/event/api?redirect=https%3A%2F%2Fwww.hepsiburada.com%2Fsponsorbrand-pro-wax-p-HBV00004D5E6F",
            "images": [{"url": "https://productimages.hepsiburada.net/s/456/def.jpg"}],
            "listing": {
                "merchantName": "Sponsor Satıcı",
                "merchantId": "m-sponsor-456",
                "priceInfo": {
                    "price": 199.90,
                    "originalPrice": 199.90,
                    "discountRate": 0,
                },
                "campaignPriceInfo": {
                    "discountedPrice": 179.90,
                },
                "campaigns": [],
                "labels": ["fast-delivery"],
            },
            "adInfo": "some-ad-info",
            "adShowId": "ad-show-123",
        }],
    }


def _build_moria_html(products_json: str, escaped: bool = True) -> str:
    """Build a minimal HTML page with embedded MORIA products data."""
    if escaped:
        json_str = products_json.replace('"', '\\"')
        state_line = f'"STATE":' + '{"products":[' + json_str[1:-1] + ']}'
        # Actually let's just build the full escaped format
        products_escaped = json.dumps(products_json).strip('"')
        # Simpler: embed escaped products array
        inner = json.dumps({"products": json.loads(products_json)})
        escaped_inner = inner.replace('"', '\\"')
        return f"""<html><head><title>Test Arama</title></head><body>
<script>window.MORIA = {{}};
window.MORIA.VERTICALFILTER = Object.assign({{}}, {{"STATE":{escaped_inner}}});
</script></body></html>"""
    else:
        inner = json.dumps({"products": json.loads(products_json)})
        return f"""<html><head><title>Test Arama</title></head><body>
<script>window.MORIA = {{}};
window.MORIA.VERTICALFILTER = Object.assign({{}}, {{"STATE":{inner}}});
</script></body></html>"""


# ──────────────────────────────────────────────────────────────
# MORIA JSON Parse Tests
# ──────────────────────────────────────────────────────────────

class TestExtractMoriaProducts:

    def test_extract_escaped_json(self, scraper, sample_moria_product_organic):
        """Escaped MORIA JSON (\\\"products\\\") is parsed correctly."""
        products_json = json.dumps([sample_moria_product_organic])
        html = _build_moria_html(products_json, escaped=True)

        result = scraper._extract_moria_products_from_html(html)

        assert result is not None
        assert len(result) == 1
        assert result[0]["productId"] == "HBV00001A2B3C"

    def test_extract_unescaped_json(self, scraper, sample_moria_product_organic):
        """Plain MORIA JSON ("products") is parsed correctly."""
        products_json = json.dumps([sample_moria_product_organic])
        html = _build_moria_html(products_json, escaped=False)

        result = scraper._extract_moria_products_from_html(html)

        assert result is not None
        assert len(result) == 1
        assert result[0]["productId"] == "HBV00001A2B3C"

    def test_extract_empty_page(self, scraper):
        """Empty/loading page returns None (triggers fallback)."""
        html = '<html><head><title>Loading interface...</title></head><body></body></html>'
        result = scraper._extract_moria_products_from_html(html)
        assert result is None

    def test_extract_no_moria_data(self, scraper):
        """HTML without MORIA data returns None."""
        html = '<html><head><title>Hepsiburada</title></head><body><div>No products</div></body></html>'
        result = scraper._extract_moria_products_from_html(html)
        assert result is None

    def test_extract_multiple_products(self, scraper, sample_moria_product_organic, sample_moria_product_sponsored):
        """Multiple products (organic + sponsored) are parsed."""
        products = [sample_moria_product_organic, sample_moria_product_sponsored]
        html = _build_moria_html(json.dumps(products), escaped=False)

        result = scraper._extract_moria_products_from_html(html)

        assert result is not None
        assert len(result) == 2
        assert result[0]["productId"] == "HBV00001A2B3C"
        assert result[1]["productId"] == "HBV00004D5E6F"


# ──────────────────────────────────────────────────────────────
# Product Normalization Tests
# ──────────────────────────────────────────────────────────────

class TestNormalizeMoriaProduct:

    def test_normalize_organic_product(self, scraper, sample_moria_product_organic):
        """Organic product is normalized with correct fields."""
        result = scraper._normalize_moria_product(sample_moria_product_organic, order_index=1)

        assert result['platform'] == 'hepsiburada'
        assert result['external_id'] == 'HBV00001A2B3C'
        assert result['name'] == 'TestBrand Premium Pasta Cila 500ml'
        assert result['brand'] == 'TestBrand'
        assert result['sku'] == 'HBV00001A2B3C'
        assert result['price'] == 249.90
        assert result['original_price'] == 349.90
        assert result['discount_percentage'] == 29
        assert result['seller_name'] == 'Test Mağaza'
        assert result['rating'] == 4.7
        assert result['reviews_count'] == 245
        assert result['is_sponsored'] is False
        assert result['other_sellers'] == []
        assert result['reviews'] == []
        assert result['order_index'] == 1

    def test_normalize_sponsored_product(self, scraper, sample_moria_product_sponsored):
        """Sponsored product detected via boostingFactors."""
        result = scraper._normalize_moria_product(sample_moria_product_sponsored, order_index=3)

        assert result['is_sponsored'] is True
        assert result['external_id'] == 'HBV00004D5E6F'
        assert result['order_index'] == 3

    def test_normalize_campaign_price(self, scraper, sample_moria_product_sponsored):
        """Campaign discounted price is extracted correctly."""
        result = scraper._normalize_moria_product(sample_moria_product_sponsored, order_index=1)

        assert result['price'] == 199.90
        assert result['discounted_price'] == 179.90

    def test_normalize_tracking_url(self, scraper, sample_moria_product_sponsored):
        """adservice tracking URL is resolved to real HB URL."""
        result = scraper._normalize_moria_product(sample_moria_product_sponsored, order_index=1)

        # URL should be resolved from tracking redirect
        assert 'adservice.' not in result['url']
        assert 'hepsiburada.com' in result['url']
        assert result['url'].endswith('-p-HBV00004D5E6F')

    def test_normalize_image_url(self, scraper, sample_moria_product_organic):
        """Image URL is extracted from variant images."""
        result = scraper._normalize_moria_product(sample_moria_product_organic, order_index=1)
        assert result['image_url'] == 'https://productimages.hepsiburada.net/s/123/abc.jpg'


# ──────────────────────────────────────────────────────────────
# Sponsored Products from MORIA Tests
# ──────────────────────────────────────────────────────────────

class TestBuildSponsoredProductsFromMoria:

    def test_sponsored_products_extracted(self, scraper, sample_moria_product_organic, sample_moria_product_sponsored):
        """Only sponsored products are included in the list."""
        organic = scraper._normalize_moria_product(sample_moria_product_organic, 1)
        sponsored = scraper._normalize_moria_product(sample_moria_product_sponsored, 2)

        result = scraper._build_sponsored_products_from_moria([organic, sponsored])

        assert len(result) == 1
        assert result[0]['product_name'] == 'SponsorBrand Pro Wax 300ml'
        assert result[0]['is_sponsored'] is True
        assert result[0]['order_index'] == 2

    def test_sponsored_product_schema(self, scraper, sample_moria_product_sponsored):
        """Sponsored product has all required frontend fields."""
        sponsored = scraper._normalize_moria_product(sample_moria_product_sponsored, 1)
        result = scraper._build_sponsored_products_from_moria([sponsored])

        sp = result[0]
        # Fields required by SearchSponsoredProduct DB model + frontend
        assert 'order_index' in sp
        assert 'product_url' in sp
        assert 'product_name' in sp
        assert 'price' in sp
        assert 'discounted_price' in sp
        assert 'image_url' in sp
        assert 'seller_name' in sp


# ──────────────────────────────────────────────────────────────
# Sponsored Brands Display API Tests
# ──────────────────────────────────────────────────────────────

class TestFetchSponsoredBrandsApi:

    @pytest.mark.asyncio
    async def test_success(self, scraper):
        """Display API returns brand ads correctly."""
        pages_response = json.dumps([2, 3])
        display_page1 = json.dumps({
            "merchantName": "AUTO POWER",
            "merchantId": "m-auto-1",
            "merchantRate": 9.6,
            "adRank": 1.5,
            "campaignId": "camp-1",
            "products": [{
                "productId": "P1",
                "name": "K-Auto Ceramics 500ml",
                "brand": "K-Auto",
                "sku": "SKU001",
                "price": 398.89,
                "imageList": ["https://img.hepsiburada.com/p1.jpg"],
                "campaignPriceInfo": {"discountedPrice": 359.00},
                "tags": ["fast-delivery"],
            }],
        })
        display_page2 = json.dumps({
            "merchantName": "Badem10",
            "merchantId": "m-badem-2",
            "merchantRate": 9.5,
            "products": [{
                "productId": "P2",
                "name": "Polishing Pad",
                "brand": "Badem",
                "sku": "SKU002",
                "price": 486.62,
                "imageList": ["https://img.hepsiburada.com/p2.jpg"],
                "campaignPriceInfo": {},
                "tags": [],
            }],
        })

        call_count = 0
        async def mock_fetch(url):
            nonlocal call_count
            call_count += 1
            if 'pages?' in url:
                return pages_response
            if 'page=1' in url:
                return display_page1
            if 'page=2' in url:
                return display_page2
            if 'page=3' in url:
                return display_page2
            return None

        with patch.object(scraper, '_fetch_hb_ads_api', side_effect=mock_fetch):
            with patch('app.services.scraping.settings') as mock_settings:
                mock_settings.SCRAPER_API_KEY = "test-key"
                result = await scraper._fetch_sponsored_brands_api("pasta cila")

        assert len(result) >= 2
        assert result[0]['seller_name'] == 'AUTO POWER'
        assert result[0]['products'][0]['name'] == 'K-Auto Ceramics 500ml'
        assert result[0]['products'][0]['price'] == 398.89
        assert result[0]['products'][0]['discounted_price'] == 359.00
        assert result[0]['merchant_rate'] == 9.6

    @pytest.mark.asyncio
    async def test_api_404_returns_empty(self, scraper):
        """Display API returning None/404 results in empty list."""
        async def mock_fetch(url):
            return None

        with patch.object(scraper, '_fetch_hb_ads_api', side_effect=mock_fetch):
            with patch('app.services.scraping.settings') as mock_settings:
                mock_settings.SCRAPER_API_KEY = "test-key"
                result = await scraper._fetch_sponsored_brands_api("nonexistent")

        assert result == []

    def test_brand_product_normalization_schema(self, scraper):
        """Display API products normalized to frontend BrandProduct interface."""
        raw_data = {
            "merchantName": "TestSeller",
            "merchantId": "m-test",
            "products": [{
                "productId": "P1",
                "name": "Test Product",
                "brand": "TB",
                "sku": "SKU123",
                "price": 100.0,
                "imageList": ["https://img.hepsiburada.com/test.jpg"],
                "campaignPriceInfo": {"discountedPrice": 85.0},
                "tags": [],
            }],
        }

        result = scraper._normalize_display_api_response(raw_data, page_num=1)

        assert len(result) == 1
        brand = result[0]
        assert brand['seller_name'] == 'TestSeller'

        product = brand['products'][0]
        # Frontend BrandProduct required fields (snake_case)
        assert 'url' in product
        assert 'name' in product
        assert 'price' in product
        assert 'discounted_price' in product
        assert 'image_url' in product
        # Values
        assert product['price'] == 100.0
        assert product['discounted_price'] == 85.0
        assert product['image_url'] == 'https://img.hepsiburada.com/test.jpg'


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────

class TestSearchIntegration:

    @pytest.mark.asyncio
    async def test_moria_parsed_skips_detail_scraping(self, scraper):
        """When MORIA parse succeeds, detail page scraping is NOT called."""
        products_json = json.dumps([{
            "productId": "P1", "brand": "B1",
            "customerReviewCount": 10, "customerReviewRating": 4.0,
            "boostingFactors": [],
            "variantList": [{
                "name": "Product 1", "sku": "SKU1",
                "url": "/product-1-p-SKU1",
                "images": [{"url": "https://img.hb.com/1.jpg"}],
                "listing": {
                    "merchantName": "Seller", "merchantId": "m1",
                    "priceInfo": {"price": 100, "originalPrice": 100, "discountRate": 0},
                    "campaignPriceInfo": {}, "campaigns": [], "labels": [],
                },
            }],
        }])
        html = _build_moria_html(products_json, escaped=False)

        with patch.object(scraper, '_fetch_with_scraperapi_async', new_callable=AsyncMock, return_value=html):
            with patch.object(scraper, '_fetch_sponsored_brands_api', new_callable=AsyncMock, return_value=[]):
                with patch.object(scraper, 'scrape_product_detail_page', new_callable=AsyncMock) as mock_detail:
                    with patch('app.services.scraping.proxy_manager') as mock_pm:
                        mock_provider = MagicMock()
                        mock_provider.name = "scraperapi"
                        mock_pm.get_primary_provider.return_value = mock_provider

                        with patch('app.services.scraping.settings') as mock_settings:
                            mock_settings.SCRAPER_API_KEY = "test-key"
                            mock_settings.DEBUG_SAVE_HTML = False

                            result = await scraper.scrape_hepsiburada_search("test", max_products=50)

        # Detail page scraping should NOT have been called
        mock_detail.assert_not_called()
        # Products should be returned
        assert len(result['products']) == 1
        assert result['products'][0]['name'] == 'Product 1'

    @pytest.mark.asyncio
    async def test_moria_fail_falls_back_to_css(self, scraper):
        """When MORIA parse fails, CSS selector fallback is used."""
        # HTML without MORIA data
        html = '<html><head><title>Pasta Cila</title></head><body><div>No MORIA</div></body></html>'

        with patch.object(scraper, '_fetch_with_scraperapi_async', new_callable=AsyncMock, return_value=html):
            with patch.object(scraper, '_extract_sponsored_brands_from_search', return_value=[]):
                with patch.object(scraper, '_extract_sponsored_products_from_search', return_value=[]):
                    with patch.object(scraper, '_extract_basket_campaign_prices', return_value={}):
                        with patch.object(scraper, '_extract_product_urls_from_soup', return_value=[]):
                            with patch('app.services.scraping.proxy_manager') as mock_pm:
                                mock_provider = MagicMock()
                                mock_provider.name = "scraperapi"
                                mock_pm.get_primary_provider.return_value = mock_provider

                                with patch('app.services.scraping.settings') as mock_settings:
                                    mock_settings.SCRAPER_API_KEY = "test-key"
                                    mock_settings.DEBUG_SAVE_HTML = False

                                    result = await scraper.scrape_hepsiburada_search("test", max_products=50)

        # Should return empty (CSS found nothing) but NOT crash
        assert result['products'] == []
        assert result['sponsored_brands'] == []

    @pytest.mark.asyncio
    async def test_sponsored_brands_fetched_parallel(self, scraper):
        """Brand ads are fetched via Display API when MORIA succeeds."""
        products_json = json.dumps([{
            "productId": "P1", "brand": "B1",
            "customerReviewCount": 5, "customerReviewRating": 3.0,
            "boostingFactors": [],
            "variantList": [{
                "name": "Product 1", "sku": "SKU1",
                "url": "/product-1-p-SKU1",
                "images": [{"url": "https://img.hb.com/1.jpg"}],
                "listing": {
                    "merchantName": "S", "merchantId": "m1",
                    "priceInfo": {"price": 50, "originalPrice": 50, "discountRate": 0},
                    "campaignPriceInfo": {}, "campaigns": [], "labels": [],
                },
            }],
        }])
        html = _build_moria_html(products_json, escaped=False)

        brand_ads = [{'seller_name': 'AUTO POWER', 'seller_id': 'ap1', 'position': 1, 'products': []}]

        with patch.object(scraper, '_fetch_with_scraperapi_async', new_callable=AsyncMock, return_value=html):
            with patch.object(scraper, '_fetch_sponsored_brands_api', new_callable=AsyncMock, return_value=brand_ads) as mock_brands:
                with patch('app.services.scraping.proxy_manager') as mock_pm:
                    mock_provider = MagicMock()
                    mock_provider.name = "scraperapi"
                    mock_pm.get_primary_provider.return_value = mock_provider

                    with patch('app.services.scraping.settings') as mock_settings:
                        mock_settings.SCRAPER_API_KEY = "test-key"
                        mock_settings.DEBUG_SAVE_HTML = False

                        result = await scraper.scrape_hepsiburada_search("test", max_products=50)

        mock_brands.assert_called_once_with("test")
        assert result['sponsored_brands'] == brand_ads


# ──────────────────────────────────────────────────────────────
# Config Test
# ──────────────────────────────────────────────────────────────

class TestSearchRouteConfig:

    def test_config_has_hb_search_max_products(self):
        """HB_SEARCH_MAX_PRODUCTS is defined in settings with default 50."""
        from app.core.config import settings
        assert hasattr(settings, 'HB_SEARCH_MAX_PRODUCTS')
        assert isinstance(settings.HB_SEARCH_MAX_PRODUCTS, int)
        # Default should be 50 unless overridden by env
        assert settings.HB_SEARCH_MAX_PRODUCTS > 0
