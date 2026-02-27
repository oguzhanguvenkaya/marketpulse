"""Marketplace adapter registry — platform adına göre adapter döndürür."""

from typing import Dict, Type, List

from app.marketplaces.base import BaseMarketplaceAdapter


class MarketplaceRegistry:
    """Singleton registry — get_adapter("hepsiburada") ile kullanılır."""

    _adapters: Dict[str, Type[BaseMarketplaceAdapter]] = {}
    _instances: Dict[str, BaseMarketplaceAdapter] = {}

    @classmethod
    def register(cls, platform: str, adapter_class: Type[BaseMarketplaceAdapter]):
        """Yeni adapter kaydet."""
        cls._adapters[platform.lower()] = adapter_class

    @classmethod
    def get_adapter(cls, platform: str) -> BaseMarketplaceAdapter:
        """Platform adına göre adapter instance döndür (lazy singleton)."""
        platform = platform.lower()
        if platform not in cls._instances:
            if platform not in cls._adapters:
                raise ValueError(
                    f"Bilinmeyen platform: {platform}. "
                    f"Kayıtlı: {list(cls._adapters.keys())}"
                )
            cls._instances[platform] = cls._adapters[platform]()
        return cls._instances[platform]

    @classmethod
    def list_platforms(cls) -> List[str]:
        """Kayıtlı platform isimlerini döndür."""
        return list(cls._adapters.keys())

    @classmethod
    def has_adapter(cls, platform: str) -> bool:
        """Platform için adapter var mı kontrol et."""
        return platform.lower() in cls._adapters
