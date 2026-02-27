"""Marketplace API Entegrasyon Servisi.

HB Merchant API ve TY Partner API ile kullanicinin kendi magazasini baglama.
OAuth flow, token yonetimi ve temel API islemleri.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User

logger = logging.getLogger(__name__)


class MarketplaceConnection:
    """Marketplace baglanti bilgilerini tutan sinif (DB'ye yazilacak)."""

    def __init__(
        self,
        user_id: str,
        platform: str,
        store_name: str = "",
        api_key: str = "",
        api_secret: str = "",
        seller_id: str = "",
        access_token: str = "",
        refresh_token: str = "",
        token_expires_at: Optional[datetime] = None,
        is_active: bool = True,
    ):
        self.user_id = user_id
        self.platform = platform
        self.store_name = store_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.seller_id = seller_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at
        self.is_active = is_active


class MarketplaceAPIService:
    """Marketplace API entegrasyon servisi."""

    # Platform bazli API endpoint'leri
    PLATFORMS = {
        "hepsiburada": {
            "name": "Hepsiburada Merchant API",
            "base_url": "https://mpop-sit.hepsiburada.com",
            "auth_type": "api_key",  # HB uses API key + secret
            "docs_url": "https://developers.hepsiburada.com",
            "required_fields": ["api_key", "api_secret", "seller_id"],
            "endpoints": {
                "listings": "/product/api/products/all-products-of-merchant/{seller_id}",
                "orders": "/orders/merchantid/{seller_id}",
                "promotions": "/promotion/api/promotions",
            },
        },
        "trendyol": {
            "name": "Trendyol Partner API",
            "base_url": "https://api.trendyol.com/sapigw",
            "auth_type": "api_key",  # TY uses API key + secret with Basic Auth
            "docs_url": "https://developers.trendyol.com",
            "required_fields": ["api_key", "api_secret", "seller_id"],
            "endpoints": {
                "products": "/suppliers/{seller_id}/products",
                "orders": "/suppliers/{seller_id}/orders",
                "promotions": "/suppliers/{seller_id}/promotions",
                "questions": "/suppliers/{seller_id}/questions/filter",
            },
        },
        "amazon_tr": {
            "name": "Amazon SP-API",
            "base_url": "https://sellingpartnerapi-eu.amazon.com",
            "auth_type": "oauth",  # Amazon uses OAuth 2.0 + LWA
            "docs_url": "https://developer-docs.amazon.com/sp-api",
            "required_fields": ["refresh_token", "client_id", "client_secret"],
            "endpoints": {
                "catalog": "/catalog/2022-04-01/items",
                "orders": "/orders/v0/orders",
                "pricing": "/products/pricing/v0/price",
            },
        },
        "n11": {
            "name": "N11 Partner API",
            "base_url": "https://api.n11.com/ws",
            "auth_type": "api_key",  # N11 uses API key + secret
            "docs_url": "https://developer.n11.com",
            "required_fields": ["api_key", "api_secret"],
            "endpoints": {
                "products": "/ProductService/",
                "orders": "/OrderService/",
            },
        },
    }

    def get_supported_platforms(self) -> list[dict]:
        """Desteklenen platformlari dondur."""
        return [
            {
                "platform": key,
                "name": info["name"],
                "auth_type": info["auth_type"],
                "required_fields": info["required_fields"],
                "docs_url": info["docs_url"],
            }
            for key, info in self.PLATFORMS.items()
        ]

    async def connect_store(
        self,
        user: User,
        platform: str,
        credentials: dict,
        db: Session,
    ) -> dict:
        """Kullanicinin magazasini bagla."""
        if platform not in self.PLATFORMS:
            return {"error": f"Desteklenmeyen platform: {platform}"}

        platform_info = self.PLATFORMS[platform]

        # Zorunlu alan kontrolu
        for field in platform_info["required_fields"]:
            if not credentials.get(field):
                return {"error": f"Eksik alan: {field}"}

        # Baglanti testi
        test_result = await self._test_connection(platform, credentials)
        if not test_result.get("success"):
            return {
                "error": f"Baglanti testi basarisiz: {test_result.get('message', 'Bilinmeyen hata')}",
                "details": test_result,
            }

        # TODO: MarketplaceConnection modeli DB'ye eklenecek (Faz 3.5)
        # Simdilik basarili baglanti donuyoruz
        return {
            "success": True,
            "platform": platform,
            "store_name": test_result.get("store_name", credentials.get("seller_id", "")),
            "message": f"{platform_info['name']} baglantisi basarili",
        }

    async def _test_connection(self, platform: str, credentials: dict) -> dict:
        """Platform API baglanti testi."""
        import aiohttp

        platform_info = self.PLATFORMS[platform]
        base_url = platform_info["base_url"]

        try:
            if platform == "hepsiburada":
                return await self._test_hb_connection(base_url, credentials)
            elif platform == "trendyol":
                return await self._test_ty_connection(base_url, credentials)
            elif platform == "amazon_tr":
                return {"success": True, "message": "Amazon SP-API OAuth akisi gerekli (henuz implemente edilmedi)", "store_name": "Amazon TR"}
            elif platform == "n11":
                return await self._test_n11_connection(base_url, credentials)
            else:
                return {"success": False, "message": "Bilinmeyen platform"}
        except Exception as e:
            logger.error(f"Baglanti testi hatasi ({platform}): {e}")
            return {"success": False, "message": str(e)}

    async def _test_hb_connection(self, base_url: str, credentials: dict) -> dict:
        """Hepsiburada API baglanti testi."""
        import aiohttp
        import base64

        api_key = credentials["api_key"]
        api_secret = credentials["api_secret"]
        seller_id = credentials["seller_id"]

        auth_str = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "application/json",
        }

        url = f"{base_url}/product/api/products/all-products-of-merchant/{seller_id}"
        params = {"page": 0, "size": 1}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "store_name": f"HB-{seller_id}",
                        "product_count": data.get("totalElements", 0),
                    }
                elif resp.status == 401:
                    return {"success": False, "message": "Yetkisiz — API key/secret kontrol edin"}
                else:
                    body = await resp.text()
                    return {"success": False, "message": f"HTTP {resp.status}: {body[:200]}"}

    async def _test_ty_connection(self, base_url: str, credentials: dict) -> dict:
        """Trendyol API baglanti testi."""
        import aiohttp
        import base64

        api_key = credentials["api_key"]
        api_secret = credentials["api_secret"]
        seller_id = credentials["seller_id"]

        auth_str = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "application/json",
            "User-Agent": f"{seller_id} - SelfIntegration",
        }

        url = f"{base_url}/suppliers/{seller_id}/products"
        params = {"page": 0, "size": 1}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "store_name": f"TY-{seller_id}",
                        "product_count": data.get("totalElements", 0),
                    }
                elif resp.status == 401:
                    return {"success": False, "message": "Yetkisiz — API key/secret kontrol edin"}
                else:
                    body = await resp.text()
                    return {"success": False, "message": f"HTTP {resp.status}: {body[:200]}"}

    async def _test_n11_connection(self, base_url: str, credentials: dict) -> dict:
        """N11 API baglanti testi."""
        import aiohttp

        api_key = credentials["api_key"]
        api_secret = credentials["api_secret"]

        # N11 SOAP API test
        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                          xmlns:sch="http://www.n11.com/ws/schemas">
            <soapenv:Header>
                <sch:Authentication>
                    <appKey>{api_key}</appKey>
                    <appSecret>{api_secret}</appSecret>
                </sch:Authentication>
            </soapenv:Header>
            <soapenv:Body>
                <sch:GetProductListRequest>
                    <pagingData>
                        <currentPage>0</currentPage>
                        <pageSize>1</pageSize>
                    </pagingData>
                </sch:GetProductListRequest>
            </soapenv:Body>
        </soapenv:Envelope>"""

        headers = {"Content-Type": "text/xml; charset=utf-8"}
        url = f"{base_url}/ProductService/"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=soap_body, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return {"success": True, "store_name": "N11 Store"}
                else:
                    return {"success": False, "message": f"HTTP {resp.status}"}

    async def get_store_products(
        self, platform: str, credentials: dict, page: int = 0, size: int = 50
    ) -> dict:
        """Magazadaki urunleri listele."""
        # Bu method ileride tam implemente edilecek
        return {
            "platform": platform,
            "page": page,
            "size": size,
            "products": [],
            "message": "Urun listesi entegrasyonu Faz 3.5'te tamamlanacak",
        }

    async def get_store_orders(
        self, platform: str, credentials: dict, days: int = 7
    ) -> dict:
        """Magazadaki siparisleri listele."""
        return {
            "platform": platform,
            "days": days,
            "orders": [],
            "message": "Siparis entegrasyonu Faz 3.5'te tamamlanacak",
        }


marketplace_api_service = MarketplaceAPIService()
