"""Amazon TR Marketplace Adapter — JSON-LD ve Product Advertising API destekli."""

import logging
import re
import json
from decimal import Decimal
from typing import Optional

from app.marketplaces.base import BaseMarketplaceAdapter
from app.marketplaces.types import PriceResult, SearchResult, SellerPrice, ProductSearchResult

logger = logging.getLogger(__name__)


class AmazonTRPriceAdapter(BaseMarketplaceAdapter):
    """Amazon TR fiyat ve arama adapter'ı.

    Fiyat çekme: JSON-LD parsing (fallback: HTML scraping)
    Arama: Amazon arama sonuçları parsing
    """

    platform = "amazon_tr"

    async def get_seller_prices(self, sku: str, **kwargs) -> PriceResult:
        """Amazon TR ürün sayfasından satıcı fiyatlarını çek.

        Amazon'da tek satıcı (fulfilled by Amazon veya 3P) görünür,
        diğer satıcılar "Other Sellers" linkinde.
        """
        import aiohttp

        product_url = f"https://www.amazon.com.tr/dp/{sku}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(product_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.warning(f"Amazon TR {sku}: HTTP {resp.status}")
                        return PriceResult(sku=sku, platform=self.platform, is_active=False)

                    html = await resp.text()
        except Exception as e:
            logger.error(f"Amazon TR fetch hatası ({sku}): {e}")
            return PriceResult(sku=sku, platform=self.platform, is_active=False)

        return self._parse_product_page(html, sku)

    def _parse_product_page(self, html: str, sku: str) -> PriceResult:
        """HTML'den ürün bilgilerini çıkar."""
        sellers = []

        # JSON-LD'den temel bilgileri çek
        json_ld = self._extract_json_ld(html)
        product_name = None
        image_url = None

        if json_ld:
            product_name = json_ld.get("name")
            image_url = json_ld.get("image")
            offers = json_ld.get("offers", {})
            if isinstance(offers, dict):
                price_str = offers.get("price")
                seller_name = offers.get("seller", {}).get("name", "Amazon.com.tr") if isinstance(offers.get("seller"), dict) else "Amazon.com.tr"
                if price_str:
                    try:
                        sellers.append(SellerPrice(
                            merchant_id="amazon_tr_main",
                            merchant_name=seller_name,
                            price=Decimal(str(price_str)),
                            buybox_order=1,
                            free_shipping=True,
                        ))
                    except (ValueError, TypeError):
                        pass

        # HTML fallback — fiyat regex
        if not sellers:
            price_match = re.search(r'class="a-price-whole">([0-9.,]+)', html)
            if price_match:
                price_str = price_match.group(1).replace(".", "").replace(",", ".")
                try:
                    sellers.append(SellerPrice(
                        merchant_id="amazon_tr_main",
                        merchant_name="Amazon.com.tr",
                        price=Decimal(price_str),
                        buybox_order=1,
                    ))
                except (ValueError, TypeError):
                    pass

        # Ürün adı fallback
        if not product_name:
            title_match = re.search(r'id="productTitle"[^>]*>\s*([^<]+)', html)
            if title_match:
                product_name = title_match.group(1).strip()

        return PriceResult(
            sellers=sellers,
            product_name=product_name,
            product_url=f"https://www.amazon.com.tr/dp/{sku}",
            image_url=image_url,
            is_active=len(sellers) > 0,
            sku=sku,
            platform=self.platform,
        )

    def _extract_json_ld(self, html: str) -> Optional[dict]:
        """Sayfadaki JSON-LD structured data'yı çıkar."""
        try:
            pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                data = json.loads(match)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    return data
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            return item
        except Exception:
            pass
        return None

    async def search_products(self, keyword: str, max_results: int = 50, **kwargs) -> SearchResult:
        """Amazon TR'de ürün ara."""
        import aiohttp
        from urllib.parse import quote_plus

        url = f"https://www.amazon.com.tr/s?k={quote_plus(keyword)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return SearchResult(keyword=keyword, platform=self.platform)
                    html = await resp.text()
        except Exception as e:
            logger.error(f"Amazon TR arama hatası ({keyword}): {e}")
            return SearchResult(keyword=keyword, platform=self.platform)

        return self._parse_search_results(html, keyword, max_results)

    def _parse_search_results(self, html: str, keyword: str, max_results: int) -> SearchResult:
        """Arama sonuçlarını parse et."""
        products = []

        # data-asin ile ürün kartlarını bul
        asin_pattern = r'data-asin="([A-Z0-9]{10})"'
        asins = re.findall(asin_pattern, html)

        # Temel bilgileri çıkar (simplified parsing)
        title_pattern = r'class="a-size-base-plus[^"]*"[^>]*>\s*([^<]+)'
        titles = re.findall(title_pattern, html)

        for i, asin in enumerate(asins[:max_results]):
            name = titles[i].strip() if i < len(titles) else f"Amazon Ürün {asin}"
            products.append(ProductSearchResult(
                name=name,
                url=f"https://www.amazon.com.tr/dp/{asin}",
                is_sponsored="AdHolder" in html,
            ))

        return SearchResult(
            products=products,
            total_count=len(products),
            keyword=keyword,
            platform=self.platform,
        )
