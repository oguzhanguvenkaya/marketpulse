"""Kârlılık hesaplama API endpoint'leri."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.models import MonitoredProduct, SellerSnapshot, User
from app.core.auth import get_current_user
from app.services.profitability_service import (
    calculate_profitability,
    simulate_price_range,
    get_available_categories,
    get_commission_rate,
)

router = APIRouter(
    prefix="/api/profitability",
    tags=["Profitability"],
    dependencies=[Depends(get_current_user)],
)


class ProfitCalcRequest(BaseModel):
    sale_price: float
    unit_cost: float
    shipping_cost: float = 0.0
    platform: str = "hepsiburada"
    category: Optional[str] = None
    commission_rate: Optional[float] = None


class SimulationRequest(BaseModel):
    unit_cost: float
    shipping_cost: float = 0.0
    platform: str = "hepsiburada"
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    steps: int = 10


@router.post("/calculate")
async def calc_profit(req: ProfitCalcRequest):
    """Tek fiyat noktası için kârlılık hesapla."""
    if req.sale_price <= 0:
        raise HTTPException(status_code=400, detail="Satis fiyati sifirdan buyuk olmali")
    if req.unit_cost < 0:
        raise HTTPException(status_code=400, detail="Maliyet negatif olamaz")

    result = calculate_profitability(
        sale_price=req.sale_price,
        unit_cost=req.unit_cost,
        shipping_cost=req.shipping_cost,
        platform=req.platform,
        category=req.category,
        commission_rate_override=req.commission_rate,
    )
    return result


@router.post("/simulate")
async def simulate_profits(req: SimulationRequest):
    """Fiyat aralığında kârlılık simülasyonu."""
    if req.unit_cost < 0:
        raise HTTPException(status_code=400, detail="Maliyet negatif olamaz")

    results = simulate_price_range(
        unit_cost=req.unit_cost,
        shipping_cost=req.shipping_cost,
        platform=req.platform,
        category=req.category,
        min_price=req.min_price,
        max_price=req.max_price,
        steps=req.steps,
    )
    return {"simulations": results}


@router.get("/categories")
async def list_categories(
    platform: str = Query("hepsiburada", description="Platform"),
):
    """Komisyon kategorilerini listele."""
    categories = get_available_categories(platform)
    return {"platform": platform, "categories": categories}


@router.get("/commission-rate")
async def get_rate(
    platform: str = Query("hepsiburada"),
    category: Optional[str] = Query(None),
):
    """Belirli bir platform/kategori için komisyon oranı."""
    rate = get_commission_rate(platform, category)
    return {"platform": platform, "category": category, "rate": float(rate)}


@router.get("/product/{product_id}")
async def product_profitability(
    product_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Belirli bir ürünün kârlılık analizi — mevcut satıcı fiyatlarıyla."""
    import uuid as uuid_mod
    from sqlalchemy import func

    product = db.query(MonitoredProduct).filter(
        MonitoredProduct.id == uuid_mod.UUID(product_id),
        MonitoredProduct.user_id == user.id,
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Urun bulunamadi")

    if not product.unit_cost:
        raise HTTPException(
            status_code=400,
            detail="Bu urun icin maliyet bilgisi girilmemis. Lutfen once urun maliyetini girin."
        )

    # En son snapshot'ı bul
    latest_date = db.query(func.max(SellerSnapshot.snapshot_date)).filter(
        SellerSnapshot.monitored_product_id == product.id,
    ).scalar()

    if not latest_date:
        return {
            "product_id": str(product.id),
            "product_name": product.product_name,
            "message": "Henuz fiyat verisi yok",
            "sellers": [],
        }

    from datetime import timedelta
    snapshots = db.query(SellerSnapshot).filter(
        SellerSnapshot.monitored_product_id == product.id,
        SellerSnapshot.snapshot_date >= latest_date - timedelta(minutes=30),
    ).order_by(SellerSnapshot.buybox_order.asc().nullslast()).all()

    # Deduplicate by merchant_id
    seen = {}
    for s in snapshots:
        if s.merchant_id not in seen or s.snapshot_date > seen[s.merchant_id].snapshot_date:
            seen[s.merchant_id] = s

    seller_profits = []
    for s in sorted(seen.values(), key=lambda x: x.buybox_order or 999):
        if s.price:
            profit = calculate_profitability(
                sale_price=float(s.price),
                unit_cost=float(product.unit_cost),
                shipping_cost=float(product.shipping_cost or 0),
                platform=product.platform,
            )
            seller_profits.append({
                "merchant_id": s.merchant_id,
                "merchant_name": s.merchant_name,
                "price": float(s.price),
                "buybox_order": s.buybox_order,
                "net_profit": profit["net_profit"],
                "profit_margin": profit["profit_margin"],
                "is_profitable": profit["is_profitable"],
                "commission_rate": profit["commission_rate"],
                "breakdown": profit["breakdown"],
            })

    return {
        "product_id": str(product.id),
        "product_name": product.product_name,
        "sku": product.sku,
        "platform": product.platform,
        "unit_cost": float(product.unit_cost),
        "shipping_cost": float(product.shipping_cost or 0),
        "sellers": seller_profits,
    }
