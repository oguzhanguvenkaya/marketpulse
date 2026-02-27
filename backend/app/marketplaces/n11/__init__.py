from app.marketplaces.registry import MarketplaceRegistry
from .price_adapter import N11PriceAdapter

MarketplaceRegistry.register("n11", N11PriceAdapter)
