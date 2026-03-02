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

        PriceMonitorService.fetch_listings() + parse_listings() kullanır.
        """
        try:
            fetch_result = await self.service.fetch_listings(sku)

            if not fetch_result.get("success"):
                return PriceResult(sku=sku, platform=self.platform, is_active=False)

            sellers_data = self.service.parse_listings(fetch_result["data"])

            if not sellers_data:
                return PriceResult(sku=sku, platform=self.platform, is_active=False)

            sellers = []
            for s in sellers_data:
                sellers.append(SellerPrice(
                    merchant_id=str(s.get("merchant_id", "")),
                    merchant_name=s.get("merchant_name", ""),
                    price=Decimal(str(s.get("price", 0))),
                    original_price=Decimal(str(s["original_price"])) if s.get("original_price") else None,
                    minimum_price=Decimal(str(s["minimum_price"])) if s.get("minimum_price") else None,
                    discount_rate=s.get("discount_rate"),
                    stock_quantity=s.get("stock_quantity"),
                    buybox_order=s.get("buybox_order"),
                    free_shipping=s.get("free_shipping", False),
                    fast_shipping=s.get("fast_shipping", False),
                    is_fulfilled=s.get("is_fulfilled_by_hb", False),
                    merchant_rating=s.get("merchant_rating"),
                    merchant_rating_count=s.get("merchant_rating_count"),
                    merchant_logo=s.get("merchant_logo"),
                    merchant_url_postfix=s.get("merchant_url_postfix"),
                    merchant_city=s.get("merchant_city"),
                    campaigns=s.get("campaigns"),
                    campaign_price=Decimal(str(s["campaign_price"])) if s.get("campaign_price") else None,
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
