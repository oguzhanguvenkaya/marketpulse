"""
Marketplace Adapter Mimarisi

Modüler adapter pattern — yeni pazaryeri eklemek için:
1. Yeni dizin oluştur (örn: amazon/)
2. BaseMarketplaceAdapter'dan türet
3. MarketplaceRegistry.register() ile kaydet

Kullanım:
    from app.marketplaces import MarketplaceRegistry

    adapter = MarketplaceRegistry.get_adapter("hepsiburada")
    result = await adapter.get_seller_prices("HB00001234")
"""

from app.marketplaces.registry import MarketplaceRegistry
from app.marketplaces.hepsiburada.price_adapter import HepsiburadaPriceAdapter
from app.marketplaces.trendyol.price_adapter import TrendyolPriceAdapter
from app.marketplaces.amazon_tr.price_adapter import AmazonTRPriceAdapter
from app.marketplaces.n11.price_adapter import N11PriceAdapter

# Auto-register adapter'lar
MarketplaceRegistry.register("hepsiburada", HepsiburadaPriceAdapter)
MarketplaceRegistry.register("trendyol", TrendyolPriceAdapter)
MarketplaceRegistry.register("amazon_tr", AmazonTRPriceAdapter)
MarketplaceRegistry.register("n11", N11PriceAdapter)

__all__ = ["MarketplaceRegistry"]
