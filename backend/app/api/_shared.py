import asyncio
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, text
from sqlalchemy.exc import OperationalError
from typing import List, Optional, Dict, Any, Callable
from pydantic import BaseModel, Field
from uuid import UUID
from urllib.parse import quote_plus
from time import perf_counter
from app.db.database import get_db, SessionLocal
from app.db.models import Product, ProductSnapshot, ProductSeller, ProductReview, SearchTask, SponsoredBrandAd, SearchSponsoredProduct, MonitoredProduct, SellerSnapshot, PriceMonitorTask
from app.core.config import settings
from app.core.logger import api_logger as logger, log_endpoint_metric


def _get_scraping_service():
    from app.services.scraping import ScrapingService
    return ScrapingService()

def _get_proxy_status():
    from app.services.scraping import get_proxy_status
    return get_proxy_status()

def _get_llm_service():
    from app.services.llm_service import LLMService
    return LLMService()

def _get_price_monitor_service():
    from app.services.price_monitor_service import price_monitor_service
    return price_monitor_service

def _get_trendyol_price_monitor_service():
    from app.services.trendyol_price_monitor_service import trendyol_price_monitor_service
    return trendyol_price_monitor_service


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    platform: str = Field(default="hepsiburada", pattern=r"^(hepsiburada|trendyol)$")

class AnalysisRequest(BaseModel):
    product_ids: List[str]
    question: Optional[str] = None

class SearchTaskResponse(BaseModel):
    id: str
    keyword: str
    platform: str
    status: str
    total_products: int
    created_at: str

    class Config:
        from_attributes = True

class CouponResponse(BaseModel):
    amount: Optional[int] = None
    min_order: Optional[int] = None

class CampaignResponse(BaseModel):
    name: str
    url: Optional[str] = None

class SellerResponse(BaseModel):
    seller_name: str
    seller_rating: Optional[float] = None
    price: Optional[float] = None
    is_authorized: bool = False

class ReviewResponse(BaseModel):
    author: Optional[str] = None
    rating: Optional[int] = None
    review_text: Optional[str] = None
    review_date: Optional[str] = None
    seller_name: Optional[str] = None

class ProductResponse(BaseModel):
    id: str
    platform: str
    external_id: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    name: str
    url: str
    brand: Optional[str] = None
    seller_name: Optional[str] = None
    seller_rating: Optional[float] = None
    category_path: Optional[str] = None
    category_hierarchy: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    origin_country: Optional[str] = None
    latest_price: Optional[float] = None
    discounted_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    latest_rating: Optional[float] = None
    reviews_count: Optional[int] = None
    stock_count: Optional[int] = None
    in_stock: Optional[bool] = None
    is_sponsored: Optional[bool] = None
    coupons: Optional[List[Dict[str, Any]]] = None
    campaigns: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True

class ProductDetailResponse(ProductResponse):
    other_sellers: List[SellerResponse] = []
    reviews: List[ReviewResponse] = []

class SnapshotResponse(BaseModel):
    id: int
    price: Optional[float] = None
    discounted_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    stock_count: Optional[int] = None
    in_stock: bool = True
    is_sponsored: bool = False
    coupons: Optional[List[Dict[str, Any]]] = None
    campaigns: Optional[List[Dict[str, Any]]] = None
    snapshot_date: str

    class Config:
        from_attributes = True


class MonitoredProductInput(BaseModel):
    productUrl: Optional[str] = None
    productName: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None  # threshold_price olarak kaydedilecek (original_price için alert)
    campaignPrice: Optional[float] = None  # alert_campaign_price olarak kaydedilecek (campaign_price için alert)
    sellerStockCode: Optional[str] = None

class BulkProductsRequest(BaseModel):
    products: List[MonitoredProductInput]
    platform: str = "hepsiburada"  # hepsiburada veya trendyol

class MonitoredProductResponse(BaseModel):
    id: str
    platform: str = "hepsiburada"
    sku: str
    barcode: Optional[str] = None
    product_url: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    seller_stock_code: Optional[str] = None
    threshold_price: Optional[float] = None
    alert_campaign_price: Optional[float] = None
    image_url: Optional[str] = None
    is_active: bool = True
    last_fetched_at: Optional[str] = None
    seller_count: int = 0
    has_price_alert: bool = False  # original_price eşik altı satıcı var mı
    price_alert_count: int = 0  # original_price eşik altı satıcı sayısı
    has_campaign_alert: bool = False  # campaign_price eşik altı satıcı var mı
    campaign_alert_count: int = 0  # campaign_price eşik altı satıcı sayısı

    class Config:
        from_attributes = True

class SellerSnapshotResponse(BaseModel):
    merchant_id: str
    merchant_name: str
    merchant_logo: Optional[str] = None
    merchant_rating: Optional[float] = None
    merchant_rating_count: Optional[int] = None
    merchant_city: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    minimum_price: Optional[float] = None
    discount_rate: Optional[float] = None
    stock_quantity: Optional[int] = None
    buybox_order: Optional[int] = None
    free_shipping: bool = False
    fast_shipping: bool = False
    price_alert: bool = False  # Eşik fiyatın altında mı
    is_fulfilled_by_hb: bool = False
    campaigns: List[str] = []  # Kampanya ve indirim etiketleri
    campaign_price: Optional[float] = None  # Sepete özel/kampanyalı fiyat
    snapshot_date: str

    class Config:
        from_attributes = True

class ProductWithSellersResponse(BaseModel):
    product: MonitoredProductResponse
    sellers: List[SellerSnapshotResponse]

class FetchTaskResponse(BaseModel):
    id: str
    status: str
    total_products: int
    completed_products: int
    failed_products: int
    created_at: str
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _calculate_price_alerts(
    platform: str,
    snapshot: SellerSnapshot,
    threshold: Optional[float],
    campaign_threshold: Optional[float]
) -> Dict[str, Optional[float]]:
    current_price = _to_float(snapshot.price)
    original_price = _to_float(snapshot.original_price)
    campaign_price = _to_float(snapshot.campaign_price)

    if platform == "trendyol":
        list_price = original_price if original_price is not None else current_price
        selling_price = current_price
        has_price_alert = threshold is not None and list_price is not None and list_price < threshold
        has_campaign_alert = (
            campaign_threshold is not None
            and original_price is not None
            and current_price is not None
            and current_price < campaign_threshold
        )
    else:
        list_price = original_price if original_price is not None else current_price
        selling_price = campaign_price if campaign_price is not None else current_price
        has_price_alert = threshold is not None and list_price is not None and list_price < threshold
        has_campaign_alert = campaign_threshold is not None and campaign_price is not None and campaign_price < campaign_threshold

    return {
        "list_price": list_price,
        "selling_price": selling_price,
        "original_price": original_price,
        "campaign_price": campaign_price,
        "has_price_alert": has_price_alert,
        "has_campaign_alert": has_campaign_alert,
    }


def _parse_review_date(value: Any) -> Optional[date]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _is_valid_http_url(url: Optional[str]) -> bool:
    return isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))


def _build_product_search_url(platform: str, sku: Optional[str]) -> Optional[str]:
    if not isinstance(sku, str):
        return None

    normalized = sku.strip()
    if not normalized:
        return None

    encoded = quote_plus(normalized)
    if platform.lower() == "trendyol":
        return f"https://www.trendyol.com/arama?q={encoded}"
    return f"https://www.hepsiburada.com/ara?q={encoded}"


def _resolve_product_url(platform: str, sku: Optional[str], product_url: Optional[str]) -> str:
    if _is_valid_http_url(product_url):
        return product_url.strip()

    return _build_product_search_url(platform, sku) or ""


def _require_scraper_api_or_503() -> str:
    try:
        return settings.require_scraper_api_key()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


def _is_queue_reachable() -> bool:
    client = None
    try:
        from redis import Redis
        client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        return bool(client.ping())
    except Exception:
        return False
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def _require_queue_or_503() -> None:
    if not _is_queue_reachable():
        raise HTTPException(status_code=503, detail="Fetch queue unavailable. Check Redis/Celery worker.")


def _is_retryable_db_operational_error(exc: OperationalError) -> bool:
    text = str(exc).lower()
    retryable_markers = (
        "ssl connection has been closed unexpectedly",
        "server closed the connection unexpectedly",
        "connection not open",
        "could not receive data from server",
    )
    return any(marker in text for marker in retryable_markers)


def _run_read_query_with_retry(
    db: Session,
    operation: Callable[[], Any],
    endpoint_name: str,
) -> Any:
    attempts = 2
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except OperationalError as exc:
            db.rollback()
            if attempt >= attempts or not _is_retryable_db_operational_error(exc):
                raise
            logger.warning(
                f"Retrying read endpoint '{endpoint_name}' after OperationalError (attempt {attempt}/{attempts}): {exc}"
            )
    return operation()


def extract_sku_from_url(url: str, platform: str = "hepsiburada") -> Optional[str]:
    """URL'den SKU çıkar"""
    import re
    if platform == "hepsiburada":
        match = re.search(r'-p[m]?-([A-Z0-9]+)', url, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    elif platform == "trendyol":
        match = re.search(r'-p-(\d+)', url)
        if match:
            return match.group(1)
    return None
