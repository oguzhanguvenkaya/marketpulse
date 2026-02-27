"""N11 Marketplace Adapter — SSR JSON ve HTML parsing destekli."""

import logging
import re
import json
from decimal import Decimal
from typing import Optional

from app.marketplaces.base import BaseMarketplaceAdapter
from app.marketplaces.types import PriceResult, SearchResult, SellerPrice, ProductSearchResult

logger = logging.getLogger(__name__)


class N11PriceAdapter(BaseMarketplaceAdapter):
    """N11 fiyat ve arama adapter'ı.

    Fiyat çekme: SSR JSON (__NEXT_DATA__) veya API endpoint
    Arama: N11 arama sonuçları parsing
    """

    platform = "n11"

    async def get_seller_prices(self, sku: str, **kwargs) -> PriceResult:
        """N11 ürün sayfasından satıcı fiyatlarını çek."""
        import aiohttp

        product_url = kwargs.get("product_url", f"https://www.n11.com/urun/{sku}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(product_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.warning(f"N11 {sku}: HTTP {resp.status}")
                        return PriceResult(sku=sku, platform=self.platform, is_active=False)
                    html = await resp.text()
        except Exception as e:
            logger.error(f"N11 fetch hatası ({sku}): {e}")
            return PriceResult(sku=sku, platform=self.platform, is_active=False)

        return self._parse_product_page(html, sku, product_url)

    def _parse_product_page(self, html: str, sku: str, product_url: str) -> PriceResult:
        """HTML'den ürün bilgilerini çıkar — __NEXT_DATA__ veya JSON-LD."""
        sellers = []
        product_name = None
        image_url = None

        # __NEXT_DATA__ SSR JSON dene
        next_data = self._extract_next_data(html)
        if next_data:
            props = next_data.get("props", {}).get("pageProps", {})
            product_data = props.get("product", {})

            if product_data:
                product_name = product_data.get("title")
                image_url = product_data.get("images", [{}])[0].get("url") if product_data.get("images") else None

                # Ana satıcı
                seller = product_data.get("seller", {})
                price = product_data.get("price", {})
                if price:
                    try:
                        sellers.append(SellerPrice(
                            merchant_id=str(seller.get("id", "n11_main")),
                            merchant_name=seller.get("name", "N11 Satıcı"),
                            price=Decimal(str(price.get("sellingPrice", price.get("value", 0)))),
                            original_price=Decimal(str(price.get("listPrice", 0))) if price.get("listPrice") else None,
                            buybox_order=1,
                            merchant_rating=seller.get("rating"),
                        ))
                    except (ValueError, TypeError, KeyError):
                        pass

                # Diğer satıcılar
                other_sellers = product_data.get("otherSellers", [])
                for i, os_data in enumerate(other_sellers, 2):
                    try:
                        sellers.append(SellerPrice(
                            merchant_id=str(os_data.get("id", f"n11_{i}")),
                            merchant_name=os_data.get("name", f"Satıcı {i}"),
                            price=Decimal(str(os_data.get("price", os_data.get("sellingPrice", 0)))),
                            buybox_order=i,
                            merchant_rating=os_data.get("rating"),
                        ))
                    except (ValueError, TypeError):
                        continue

        # JSON-LD fallback
        if not sellers:
            json_ld = self._extract_json_ld(html)
            if json_ld:
                product_name = product_name or json_ld.get("name")
                offers = json_ld.get("offers", {})
                if isinstance(offers, dict) and offers.get("price"):
                    try:
                        sellers.append(SellerPrice(
                            merchant_id="n11_main",
                            merchant_name=offers.get("seller", {}).get("name", "N11 Satıcı") if isinstance(offers.get("seller"), dict) else "N11 Satıcı",
                            price=Decimal(str(offers["price"])),
                            buybox_order=1,
                        ))
                    except (ValueError, TypeError):
                        pass

        # HTML regex fallback
        if not sellers:
            price_match = re.search(r'"price":\s*"?([0-9.,]+)"?', html)
            if price_match:
                price_str = price_match.group(1).replace(".", "").replace(",", ".")
                try:
                    sellers.append(SellerPrice(
                        merchant_id="n11_main",
                        merchant_name="N11 Satıcı",
                        price=Decimal(price_str),
                        buybox_order=1,
                    ))
                except (ValueError, TypeError):
                    pass

        if not product_name:
            title_match = re.search(r'<h1[^>]*class="[^"]*proName[^"]*"[^>]*>([^<]+)', html)
            if title_match:
                product_name = title_match.group(1).strip()

        return PriceResult(
            sellers=sellers,
            product_name=product_name,
            product_url=product_url,
            image_url=image_url,
            is_active=len(sellers) > 0,
            sku=sku,
            platform=self.platform,
        )

    def _extract_next_data(self, html: str) -> Optional[dict]:
        """__NEXT_DATA__ SSR JSON'ı çıkar."""
        try:
            match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except Exception:
            pass
        return None

    def _extract_json_ld(self, html: str) -> Optional[dict]:
        """JSON-LD structured data'yı çıkar."""
        try:
            pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                data = json.loads(match)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    return data
        except Exception:
            pass
        return None

    async def search_products(self, keyword: str, max_results: int = 50, **kwargs) -> SearchResult:
        """N11'de ürün ara."""
        import aiohttp
        from urllib.parse import quote_plus

        url = f"https://www.n11.com/arama?q={quote_plus(keyword)}"
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
            logger.error(f"N11 arama hatası ({keyword}): {e}")
            return SearchResult(keyword=keyword, platform=self.platform)

        return self._parse_search_results(html, keyword, max_results)

    def _parse_search_results(self, html: str, keyword: str, max_results: int) -> SearchResult:
        """Arama sonuçlarını parse et."""
        products = []

        # __NEXT_DATA__ dene
        next_data = self._extract_next_data(html)
        if next_data:
            props = next_data.get("props", {}).get("pageProps", {})
            search_results = props.get("products", props.get("searchResults", []))

            for item in search_results[:max_results]:
                if isinstance(item, dict):
                    products.append(ProductSearchResult(
                        name=item.get("title", item.get("name", "")),
                        url=item.get("url", ""),
                        price=Decimal(str(item.get("price", 0))) if item.get("price") else None,
                        original_price=Decimal(str(item.get("listPrice", 0))) if item.get("listPrice") else None,
                        image_url=item.get("imageUrl", item.get("image")),
                        brand=item.get("brand"),
                        seller_name=item.get("sellerName"),
                        rating=item.get("rating"),
                        is_sponsored=item.get("isSponsored", False),
                    ))

        return SearchResult(
            products=products,
            total_count=len(products),
            keyword=keyword,
            platform=self.platform,
        )
