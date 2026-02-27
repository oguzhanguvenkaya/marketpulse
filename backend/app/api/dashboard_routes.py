"""Dashboard aggregation API endpoint'leri."""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.database import get_db
from app.db.models import (
    User, Subscription, MonitoredProduct, SellerSnapshot,
    SearchTask, AlertLog, ScheduledTask,
)
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_dashboard_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ana dashboard özet verileri."""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)

    # SKU sayıları (platform bazlı)
    sku_counts = (
        db.query(MonitoredProduct.platform, func.count(MonitoredProduct.id))
        .filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.is_active == True,
        )
        .group_by(MonitoredProduct.platform)
        .all()
    )
    total_skus = sum(c for _, c in sku_counts)
    platform_breakdown = {p: c for p, c in sku_counts}

    # SKU limiti
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    sku_limit = sub.sku_limit if sub else 10

    # Son 24 saat alarm sayısı
    recent_alerts_count = (
        db.query(func.count(AlertLog.id))
        .filter(AlertLog.user_id == user.id, AlertLog.created_at >= last_24h)
        .scalar()
        or 0
    )

    # Eşik ihlalleri
    threshold_violations = []
    products_with_threshold = (
        db.query(MonitoredProduct)
        .filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.is_active == True,
            MonitoredProduct.threshold_price.isnot(None),
        )
        .all()
    )

    for product in products_with_threshold[:50]:
        latest = (
            db.query(SellerSnapshot)
            .filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.buybox_order == 1,
            )
            .order_by(desc(SellerSnapshot.snapshot_date))
            .first()
        )

        if latest and latest.price and product.threshold_price:
            if float(latest.price) < float(product.threshold_price):
                threshold_violations.append({
                    "product_id": str(product.id),
                    "product_name": product.product_name,
                    "sku": product.sku,
                    "platform": product.platform,
                    "current_price": float(latest.price),
                    "threshold_price": float(product.threshold_price),
                    "seller": latest.merchant_name,
                })

    # Son tarama
    last_scan = (
        db.query(ScheduledTask)
        .filter(ScheduledTask.user_id == user.id, ScheduledTask.is_active == True)
        .order_by(desc(ScheduledTask.last_run_at))
        .first()
    )

    # Son aramalar
    recent_searches = (
        db.query(SearchTask)
        .filter(SearchTask.user_id == user.id)
        .order_by(desc(SearchTask.created_at))
        .limit(5)
        .all()
    )

    return {
        "sku_overview": {
            "total": total_skus,
            "limit": sku_limit,
            "usage_percent": round(total_skus / max(sku_limit, 1) * 100, 1),
            "by_platform": platform_breakdown,
        },
        "alerts": {
            "today_count": recent_alerts_count,
            "threshold_violations": threshold_violations[:10],
        },
        "plan": {
            "tier": user.plan_tier,
            "sku_limit": sku_limit,
        },
        "last_scan": {
            "at": last_scan.last_run_at.isoformat() if last_scan and last_scan.last_run_at else None,
            "next": last_scan.next_run_at.isoformat() if last_scan else None,
        },
        "recent_searches": [
            {
                "keyword": s.keyword,
                "platform": s.platform,
                "products": s.total_products,
                "date": s.created_at.isoformat(),
            }
            for s in recent_searches
        ],
    }


@router.get("/price-movers")
async def get_price_movers(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Son 7 günde en çok fiyat değişen ürünler."""
    last_7_days = datetime.utcnow() - timedelta(days=7)

    products = (
        db.query(MonitoredProduct)
        .filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.is_active == True,
        )
        .limit(50)
        .all()
    )

    movers = []
    for product in products:
        snapshots = (
            db.query(SellerSnapshot)
            .filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.buybox_order == 1,
                SellerSnapshot.snapshot_date >= last_7_days,
            )
            .order_by(SellerSnapshot.snapshot_date)
            .all()
        )

        if len(snapshots) >= 2:
            old_price = float(snapshots[0].price)
            new_price = float(snapshots[-1].price)
            if old_price > 0:
                change_pct = ((new_price - old_price) / old_price) * 100
                if abs(change_pct) >= 1:
                    movers.append({
                        "product_id": str(product.id),
                        "product_name": product.product_name,
                        "sku": product.sku,
                        "platform": product.platform,
                        "old_price": old_price,
                        "new_price": new_price,
                        "change_percent": round(change_pct, 1),
                        "direction": "up" if change_pct > 0 else "down",
                    })

    movers.sort(key=lambda x: abs(x["change_percent"]), reverse=True)

    return {
        "price_drops": [m for m in movers if m["direction"] == "down"][:10],
        "price_increases": [m for m in movers if m["direction"] == "up"][:10],
    }


@router.get("/profitability-overview")
async def get_profitability_overview(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kârlılık özeti — en çok kâr/zarar eden ürünler."""
    from app.services.profitability_service import calculate_profitability

    products = (
        db.query(MonitoredProduct)
        .filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.is_active == True,
            MonitoredProduct.unit_cost.isnot(None),
        )
        .all()
    )

    results = []
    for product in products[:30]:
        latest = (
            db.query(SellerSnapshot)
            .filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.buybox_order == 1,
            )
            .order_by(desc(SellerSnapshot.snapshot_date))
            .first()
        )

        if latest and latest.price and product.unit_cost:
            try:
                profit_data = calculate_profitability(
                    platform=product.platform,
                    category="diger",
                    sale_price=float(latest.price),
                    unit_cost=float(product.unit_cost),
                    shipping_cost=float(product.shipping_cost or 0),
                )
                results.append({
                    "product_id": str(product.id),
                    "product_name": product.product_name,
                    "sku": product.sku,
                    "sale_price": float(latest.price),
                    "net_profit": profit_data["net_profit"],
                    "margin_percent": profit_data["margin_percent"],
                    "profitable": profit_data["net_profit"] > 0,
                })
            except Exception:
                pass

    results.sort(key=lambda x: x["net_profit"])

    return {
        "total_products_with_cost": len(results),
        "profitable_count": sum(1 for r in results if r["profitable"]),
        "losing_count": sum(1 for r in results if not r["profitable"]),
        "top_profitable": sorted(results, key=lambda x: x["net_profit"], reverse=True)[:5],
        "top_losing": [r for r in results if not r["profitable"]][:5],
    }
