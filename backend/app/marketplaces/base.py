"""Tüm marketplace adapter'ların abstract base class'ı."""

from abc import ABC, abstractmethod
from typing import Optional
import os
import yaml

from app.marketplaces.types import PriceResult, SearchResult, CategoryResult


class BaseMarketplaceAdapter(ABC):
    """Marketplace adapter interface.

    Her yeni pazaryeri bu class'tan türetilir ve
    en az get_seller_prices ve search_products implement eder.
    """

    platform: str = ""

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """YAML config dosyasını yükle."""
        config_dir = os.path.join(os.path.dirname(__file__), "config")
        config_file = os.path.join(config_dir, f"{self.platform}.yaml")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    @abstractmethod
    async def get_seller_prices(self, sku: str, **kwargs) -> PriceResult:
        """SKU için satıcı fiyatlarını getir."""
        ...

    @abstractmethod
    async def search_products(self, keyword: str, max_results: int = 50, **kwargs) -> SearchResult:
        """Ürün ara."""
        ...

    async def parse_category(self, url: str, max_pages: int = 1, **kwargs) -> CategoryResult:
        """Kategori sayfasını parse et (opsiyonel — tüm adapter'lar desteklemek zorunda değil)."""
        raise NotImplementedError(f"{self.platform} kategori parsing desteklemiyor")
