"""
Trendyol fiyat izleme adapter'ı.

Mevcut TrendyolPriceMonitorService'i delegate olarak kullanır.
İleriki aşamalarda logic doğrudan buraya taşınacak.
"""

import logging
from decimal import Decimal

from app.marketplaces.base import BaseMarketplaceAdapter
from app.marketplaces.types import PriceResult, SellerPrice, SearchResult

logger = logging.getLogger(__name__)


class TrendyolPriceAdapter(BaseMarketplaceAdapter):
    """Trendyol SSR JSON parsing adapter'ı."""

    platform = "trendyol"

    def __init__(self):
        super().__init__()
        self._service = None

    @property
    def service(self):
        """Lazy-init: mevcut TrendyolPriceMonitorService'e delegate."""
        if self._service is None:
            from app.services.trendyol_price_monitor_service import TrendyolPriceMonitorService
            self._service = TrendyolPriceMonitorService()
        return self._service

    async def get_seller_prices(self, sku: str, **kwargs) -> PriceResult:
        """SKU için satıcı fiyatlarını TY SSR JSON'dan getir.

        Mevcut TrendyolPriceMonitorService'e delegate eder.
        """
        product_url = kwargs.get("product_url", "")
        try:
            sellers_data = await self.service._fetch_product_sellers(sku, product_url=product_url)

            if not sellers_data:
                return PriceResult(sku=sku, platform=self.platform, is_active=False)

            sellers = []
            for s in sellers_data:
                sellers.append(SellerPrice(
                    merchant_id=str(s.get("merchantId", "")),
                    merchant_name=s.get("merchantName", ""),
                    price=Decimal(str(s.get("price", 0))),
                    original_price=Decimal(str(s["originalPrice"])) if s.get("originalPrice") else None,
                    discount_rate=s.get("discountRate"),
                    stock_quantity=s.get("stockQuantity"),
                    merchant_rating=s.get("merchantRating"),
                    delivery_info=s.get("deliveryInfo"),
                    campaign_info=s.get("campaignInfo"),
                ))

            return PriceResult(
                sellers=sellers,
                sku=sku,
                platform=self.platform,
                is_active=True,
            )

        except Exception as e:
            logger.error(f"[TY] Fiyat çekme hatası SKU={sku}: {e}")
            return PriceResult(sku=sku, platform=self.platform, is_active=False)

    async def search_products(self, keyword: str, max_results: int = 50, **kwargs) -> SearchResult:
        """Trendyol ürün araması.

        Mevcut scraping.py'deki TY arama fonksiyonuna delegate eder.
        """
        try:
            from app.services.scraping import scrape_trendyol_search
            results = await scrape_trendyol_search(keyword, max_results=max_results)
            return SearchResult(
                products=results.get("products", []),
                total_count=results.get("total_count", 0),
                keyword=keyword,
                platform=self.platform,
            )
        except Exception as e:
            logger.error(f"[TY] Arama hatası keyword={keyword}: {e}")
            return SearchResult(keyword=keyword, platform=self.platform)
