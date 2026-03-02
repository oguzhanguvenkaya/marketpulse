"""
Trendyol fiyat izleme adapter'ı.

Mevcut TrendyolPriceMonitorService'i delegate olarak kullanır.
İleriki aşamalarda logic doğrudan buraya taşınacak.
"""

import logging
import aiohttp
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

        TrendyolPriceMonitorService.fetch_product_page() + parse_merchants_from_json() kullanır.
        """
        product_url = kwargs.get("product_url", "")
        if not product_url:
            logger.warning(f"[TY] product_url verilmedi, SKU={sku}")
            return PriceResult(sku=sku, platform=self.platform, is_active=False)

        try:
            async with aiohttp.ClientSession() as http_session:
                fetch_result = await self.service.fetch_product_page(product_url, http_session)

            html = fetch_result.get("html")
            if not html:
                return PriceResult(sku=sku, platform=self.platform, is_active=False)

            sellers_data = self.service.parse_merchants_from_json(html)

            if not sellers_data:
                return PriceResult(sku=sku, platform=self.platform, is_active=False)

            sellers = []
            for s in sellers_data:
                sellers.append(SellerPrice(
                    merchant_id=str(s.get("merchant_id", "")),
                    merchant_name=s.get("merchant_name", ""),
                    price=Decimal(str(s.get("price", 0))),
                    original_price=Decimal(str(s["original_price"])) if s.get("original_price") else None,
                    discount_rate=s.get("discount_rate"),
                    merchant_rating=s.get("merchant_rating"),
                    delivery_info=s.get("delivery_info"),
                    campaign_info=s.get("campaign_info"),
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
