"""
Hepsiburada fiyat izleme adapter'ı.

Mevcut PriceMonitorService'i delegate olarak kullanır.
İleriki aşamalarda logic doğrudan buraya taşınacak.
"""

import logging
from typing import Optional
from decimal import Decimal

from app.marketplaces.base import BaseMarketplaceAdapter
from app.marketplaces.types import PriceResult, SellerPrice, SearchResult

logger = logging.getLogger(__name__)


class HepsiburadaPriceAdapter(BaseMarketplaceAdapter):
    """Hepsiburada Listings API + Campaign API adapter'ı."""

    platform = "hepsiburada"

    def __init__(self):
        super().__init__()
        self._service = None

    @property
    def service(self):
        """Lazy-init: mevcut PriceMonitorService'e delegate."""
        if self._service is None:
            from app.services.price_monitor_service import PriceMonitorService
            self._service = PriceMonitorService()
        return self._service

    async def get_seller_prices(self, sku: str, **kwargs) -> PriceResult:
        """SKU için satıcı fiyatlarını Listings API'den getir.

        Mevcut PriceMonitorService._fetch_product_sellers() metoduna delegate eder.
        """
        try:
            sellers_data = await self.service._fetch_product_sellers(sku)

            if not sellers_data:
                return PriceResult(sku=sku, platform=self.platform, is_active=False)

            sellers = []
            for s in sellers_data:
                sellers.append(SellerPrice(
                    merchant_id=str(s.get("merchantId", "")),
                    merchant_name=s.get("merchantName", ""),
                    price=Decimal(str(s.get("price", 0))),
                    original_price=Decimal(str(s["originalPrice"])) if s.get("originalPrice") else None,
                    minimum_price=Decimal(str(s["minimumPrice"])) if s.get("minimumPrice") else None,
                    discount_rate=s.get("discountRate"),
                    stock_quantity=s.get("stockQuantity"),
                    buybox_order=s.get("buyboxOrder"),
                    free_shipping=s.get("freeShipping", False),
                    fast_shipping=s.get("fastShipping", False),
                    is_fulfilled=s.get("isFulfilledByHB", False),
                    merchant_rating=s.get("merchantRating"),
                    merchant_rating_count=s.get("merchantRatingCount"),
                    merchant_logo=s.get("merchantLogo"),
                    merchant_url_postfix=s.get("merchantUrlPostfix"),
                    merchant_city=s.get("merchantCity"),
                    campaigns=s.get("campaigns"),
                    campaign_price=Decimal(str(s["campaignPrice"])) if s.get("campaignPrice") else None,
                ))

            return PriceResult(
                sellers=sellers,
                sku=sku,
                platform=self.platform,
                is_active=True,
            )

        except Exception as e:
            logger.error(f"[HB] Fiyat çekme hatası SKU={sku}: {e}")
            return PriceResult(sku=sku, platform=self.platform, is_active=False)

    async def search_products(self, keyword: str, max_results: int = 50, **kwargs) -> SearchResult:
        """Hepsiburada ürün araması.

        Mevcut scraping.py'deki HB arama fonksiyonuna delegate eder.
        """
        try:
            from app.services.scraping import scrape_hepsiburada_search
            results = await scrape_hepsiburada_search(keyword, max_results=max_results)
            return SearchResult(
                products=results.get("products", []),
                total_count=results.get("total_count", 0),
                keyword=keyword,
                platform=self.platform,
            )
        except Exception as e:
            logger.error(f"[HB] Arama hatası keyword={keyword}: {e}")
            return SearchResult(keyword=keyword, platform=self.platform)

    async def parse_category(self, url: str, max_pages: int = 1, **kwargs):
        """Hepsiburada kategori taraması — mevcut CategoryScraperService'e delegate."""
        from app.services.category_scraper_service import CategoryScraperService
        scraper = CategoryScraperService()
        return await scraper.scrape_category(url, max_pages=max_pages)
