"""
Kârlılık hesaplama servisi.

Net kâr formülü: Satış Fiyatı - Maliyet - Komisyon - Kargo = Net Kâr
Komisyon oranları platform ve kategori bazlı tablolardan gelir.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

logger = logging.getLogger(__name__)

# Hepsiburada komisyon oranları (kategori bazlı, %)
# Kaynak: HB satıcı paneli (2024 güncel)
HB_COMMISSION_RATES = {
    "default": Decimal("12.00"),
    "elektronik": Decimal("8.00"),
    "telefon": Decimal("5.00"),
    "bilgisayar": Decimal("8.00"),
    "ev-yasam": Decimal("15.00"),
    "giyim": Decimal("18.00"),
    "kozmetik": Decimal("15.00"),
    "anne-bebek": Decimal("12.00"),
    "spor": Decimal("15.00"),
    "kitap": Decimal("15.00"),
    "oyuncak": Decimal("15.00"),
    "otomotiv": Decimal("12.00"),
    "pet-shop": Decimal("12.00"),
    "gida": Decimal("10.00"),
    "supermarket": Decimal("10.00"),
    "kirtasiye": Decimal("15.00"),
    "bahce": Decimal("15.00"),
    "mobilya": Decimal("12.00"),
}

# Trendyol komisyon oranları (kategori bazlı, %)
TY_COMMISSION_RATES = {
    "default": Decimal("15.00"),
    "elektronik": Decimal("7.00"),
    "telefon": Decimal("5.00"),
    "bilgisayar": Decimal("7.00"),
    "ev-yasam": Decimal("18.00"),
    "giyim": Decimal("20.00"),
    "kozmetik": Decimal("18.00"),
    "anne-bebek": Decimal("15.00"),
    "spor": Decimal("18.00"),
    "kitap": Decimal("18.00"),
    "oyuncak": Decimal("18.00"),
    "otomotiv": Decimal("12.00"),
    "pet-shop": Decimal("15.00"),
    "gida": Decimal("12.00"),
    "supermarket": Decimal("12.00"),
    "kirtasiye": Decimal("18.00"),
    "bahce": Decimal("18.00"),
    "mobilya": Decimal("15.00"),
}

PLATFORM_RATES = {
    "hepsiburada": HB_COMMISSION_RATES,
    "trendyol": TY_COMMISSION_RATES,
}


def get_commission_rate(platform: str, category: Optional[str] = None) -> Decimal:
    """Platform ve kategori bazlı komisyon oranını döndür."""
    rates = PLATFORM_RATES.get(platform, HB_COMMISSION_RATES)
    if category:
        cat_lower = category.strip().lower()
        # Kategori eşleştirme — alt string arama
        for key, rate in rates.items():
            if key != "default" and key in cat_lower:
                return rate
    return rates["default"]


def calculate_profitability(
    sale_price: float,
    unit_cost: float,
    shipping_cost: float = 0.0,
    platform: str = "hepsiburada",
    category: Optional[str] = None,
    commission_rate_override: Optional[float] = None,
) -> dict:
    """
    Ürün başı net kâr hesapla.

    Returns:
        {
            "sale_price": 100.00,
            "unit_cost": 50.00,
            "commission_rate": 12.00,
            "commission_amount": 12.00,
            "shipping_cost": 15.00,
            "net_profit": 23.00,
            "profit_margin": 23.00,
            "is_profitable": True,
            "breakdown": [
                {"label": "Satis Fiyati", "amount": 100.00, "type": "revenue"},
                {"label": "Komisyon (%12)", "amount": -12.00, "type": "cost"},
                {"label": "Kargo", "amount": -15.00, "type": "cost"},
                {"label": "Urun Maliyeti", "amount": -50.00, "type": "cost"},
                {"label": "Net Kar", "amount": 23.00, "type": "result"},
            ]
        }
    """
    sp = Decimal(str(sale_price))
    uc = Decimal(str(unit_cost))
    sc = Decimal(str(shipping_cost))

    if commission_rate_override is not None:
        cr = Decimal(str(commission_rate_override))
    else:
        cr = get_commission_rate(platform, category)

    commission_amount = (sp * cr / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    net_profit = sp - uc - commission_amount - sc
    profit_margin = (net_profit / sp * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) if sp > 0 else Decimal("0")

    breakdown = [
        {"label": "Satis Fiyati", "amount": float(sp), "type": "revenue"},
        {"label": f"Komisyon (%{cr})", "amount": float(-commission_amount), "type": "cost"},
        {"label": "Kargo", "amount": float(-sc), "type": "cost"},
        {"label": "Urun Maliyeti", "amount": float(-uc), "type": "cost"},
        {"label": "Net Kar", "amount": float(net_profit), "type": "result"},
    ]

    return {
        "sale_price": float(sp),
        "unit_cost": float(uc),
        "commission_rate": float(cr),
        "commission_amount": float(commission_amount),
        "shipping_cost": float(sc),
        "net_profit": float(net_profit),
        "profit_margin": float(profit_margin),
        "is_profitable": net_profit > 0,
        "breakdown": breakdown,
    }


def simulate_price_range(
    unit_cost: float,
    shipping_cost: float = 0.0,
    platform: str = "hepsiburada",
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    steps: int = 10,
) -> list[dict]:
    """
    Fiyat aralığında kârlılık simülasyonu.
    'Bu fiyata satarsam ne kazanırım?' sorusunu cevaplar.
    """
    uc = unit_cost
    cr = float(get_commission_rate(platform, category))

    # Otomatik aralık: maliyetin %80'i ile %300'ü arası
    if min_price is None:
        min_price = max(uc * 0.8, 1.0)
    if max_price is None:
        max_price = uc * 3.0

    if steps < 2:
        steps = 2
    if steps > 50:
        steps = 50

    step_size = (max_price - min_price) / (steps - 1)
    results = []

    for i in range(steps):
        price = min_price + (step_size * i)
        result = calculate_profitability(
            sale_price=round(price, 2),
            unit_cost=uc,
            shipping_cost=shipping_cost,
            platform=platform,
            category=category,
            commission_rate_override=cr,
        )
        results.append({
            "sale_price": result["sale_price"],
            "net_profit": result["net_profit"],
            "profit_margin": result["profit_margin"],
            "is_profitable": result["is_profitable"],
        })

    return results


def get_available_categories(platform: str = "hepsiburada") -> list[dict]:
    """Mevcut komisyon kategorilerini listele."""
    rates = PLATFORM_RATES.get(platform, HB_COMMISSION_RATES)
    return [
        {"key": key, "rate": float(rate)}
        for key, rate in sorted(rates.items())
        if key != "default"
    ]
