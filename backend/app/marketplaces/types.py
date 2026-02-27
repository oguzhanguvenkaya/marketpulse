"""Marketplace adapter'lar arasında paylaşılan veri modelleri."""

from dataclasses import dataclass, field
from typing import Optional, List, Any
from decimal import Decimal


@dataclass
class SellerPrice:
    """Tek bir satıcının fiyat bilgisi."""
    merchant_id: str
    merchant_name: str
    price: Decimal
    original_price: Optional[Decimal] = None
    minimum_price: Optional[Decimal] = None
    campaign_price: Optional[Decimal] = None
    discount_rate: Optional[float] = None
    stock_quantity: Optional[int] = None
    buybox_order: Optional[int] = None
    free_shipping: bool = False
    fast_shipping: bool = False
    is_fulfilled: bool = False
    merchant_rating: Optional[float] = None
    merchant_rating_count: Optional[int] = None
    merchant_logo: Optional[str] = None
    merchant_url_postfix: Optional[str] = None
    merchant_city: Optional[str] = None
    delivery_info: Optional[str] = None
    campaign_info: Optional[str] = None
    campaigns: Optional[List[Any]] = None


@dataclass
class ProductSearchResult:
    """Arama sonucu ürün."""
    name: str
    url: str
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    image_url: Optional[str] = None
    brand: Optional[str] = None
    seller_name: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    is_sponsored: bool = False


@dataclass
class SearchResult:
    """Arama sonuçları."""
    products: List[ProductSearchResult] = field(default_factory=list)
    total_count: int = 0
    sponsored_count: int = 0
    keyword: str = ""
    platform: str = ""


@dataclass
class CategoryProduct:
    """Kategori ürünü."""
    name: str
    url: str
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    image_url: Optional[str] = None
    brand: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    is_sponsored: bool = False
    position: int = 0
    page_number: int = 1


@dataclass
class CategoryResult:
    """Kategori tarama sonuçları."""
    products: List[CategoryProduct] = field(default_factory=list)
    category_name: Optional[str] = None
    breadcrumbs: Optional[list] = None
    total_products: int = 0
    pages_scraped: int = 0
    filter_data: Optional[dict] = None


@dataclass
class PriceResult:
    """Fiyat izleme sonucu — bir SKU için tüm satıcı fiyatları."""
    sellers: List[SellerPrice] = field(default_factory=list)
    product_name: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True
    sku: str = ""
    platform: str = ""
