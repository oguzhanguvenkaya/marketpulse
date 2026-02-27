from app.marketplaces.registry import MarketplaceRegistry
from .price_adapter import AmazonTRPriceAdapter

MarketplaceRegistry.register("amazon_tr", AmazonTRPriceAdapter)
