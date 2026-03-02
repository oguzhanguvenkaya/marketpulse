"""Kârlılık hesaplama AI tool fonksiyonları."""

import logging
from app.core.logger import get_logger

logger = get_logger("ai.tools.profitability")


async def calculate_profitability(
    platform: str = "hepsiburada",
    category: str = "diger",
    sale_price: float = 0,
    unit_cost: float = 0,
    shipping_cost: float = 0,
    **kwargs,
) -> dict:
    """Net kâr hesapla."""
    from app.services.profitability_service import calculate_profitability as calc

    try:
        result = calc(
            platform=platform,
            category=category,
            sale_price=sale_price,
            unit_cost=unit_cost,
            shipping_cost=shipping_cost,
        )
        return {
            "platform": platform,
            "kategori": category,
            "satis_fiyati": sale_price,
            "birim_maliyet": unit_cost,
            "kargo_bedeli": shipping_cost,
            "komisyon_orani": result.get("commission_rate", 0),
            "komisyon_tutari": result.get("commission_amount", 0),
            "net_kar": result.get("net_profit", 0),
            "kar_marji_yuzde": result.get("margin_percent", 0),
            "karli_mi": result.get("net_profit", 0) > 0,
        }
    except Exception as e:
        return {"hata": f"Kârlılık hesaplanamadı: {str(e)}"}
