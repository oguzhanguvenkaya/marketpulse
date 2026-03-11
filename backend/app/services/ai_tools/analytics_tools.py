"""Analytics AI tool fonksiyonları — anomali tespiti, rekabet analizi, kampanya fiyat önerisi."""

import math
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.core.logger import get_logger
from app.db.models import MonitoredProduct, SellerSnapshot

logger = get_logger("ai.tools.analytics")


async def detect_price_anomalies(
    user_id: str, db: Session, sku: str = "", days: int = 7, **kwargs
) -> dict:
    """Son N gundeki anormal fiyat degisikliklerini tespit et (Z-score > 2)."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,  # noqa: E712
    )
    if sku:
        query = query.filter(MonitoredProduct.sku.ilike(f"%{sku}%"))

    products = query.limit(50).all()
    if not products:
        return {"mesaj": "İzlenen ürün bulunamadı."}

    anomalies = []
    for product in products:
        # Buybox (order=1) snapshot'lari al
        snapshots = (
            db.query(SellerSnapshot)
            .filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.buybox_order == 1,
                SellerSnapshot.snapshot_date >= cutoff,
            )
            .order_by(SellerSnapshot.snapshot_date)
            .all()
        )

        if len(snapshots) < 3:
            continue

        prices = [float(s.price) for s in snapshots if s.price]
        if len(prices) < 3:
            continue

        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std = math.sqrt(variance) if variance > 0 else 0

        if std == 0:
            continue

        # Son fiyatin Z-score'u
        last_price = prices[-1]
        z_score = abs(last_price - mean) / std

        if z_score > 2:
            prev_price = prices[-2] if len(prices) >= 2 else mean
            change_pct = ((last_price - prev_price) / prev_price * 100) if prev_price else 0
            anomalies.append({
                "urun": product.product_name[:80] if product.product_name else product.sku,
                "sku": product.sku,
                "platform": product.platform,
                "son_fiyat": last_price,
                "ortalama": round(mean, 2),
                "standart_sapma": round(std, 2),
                "z_score": round(z_score, 2),
                "degisim_yuzde": round(change_pct, 1),
                "yon": "artis" if last_price > mean else "dusus",
                "veri_sayisi": len(prices),
            })

    anomalies.sort(key=lambda x: x["z_score"], reverse=True)

    return {
        "analiz_suresi_gun": days,
        "incelenen_urun": len(products),
        "anomali_sayisi": len(anomalies),
        "anomaliler": anomalies[:10],
    }


async def get_competitive_intel(
    user_id: str, db: Session, sku: str = "", **kwargs
) -> dict:
    """Rakip satıcılarla karşılaştırmalı analiz — fiyat, pozisyon, stok durumu."""
    query = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,  # noqa: E712
    )
    if sku:
        query = query.filter(MonitoredProduct.sku.ilike(f"%{sku}%"))

    products = query.limit(20).all()
    if not products:
        return {"mesaj": "İzlenen ürün bulunamadı."}

    results = []
    for product in products:
        # En son snapshot'lari al (tum saticilar)
        latest_date_subq = (
            db.query(func.max(SellerSnapshot.snapshot_date))
            .filter(SellerSnapshot.monitored_product_id == product.id)
            .scalar_subquery()
        )

        sellers = (
            db.query(SellerSnapshot)
            .filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.snapshot_date >= latest_date_subq - timedelta(hours=2),
            )
            .order_by(SellerSnapshot.buybox_order)
            .all()
        )

        if not sellers:
            continue

        seller_data = []
        for s in sellers:
            seller_data.append({
                "satici": s.merchant_name,
                "fiyat": float(s.price) if s.price else None,
                "kampanya_fiyat": float(s.campaign_price) if s.campaign_price else None,
                "buybox_sira": s.buybox_order,
                "stok": s.stock_quantity,
                "ucretsiz_kargo": s.free_shipping,
                "hizli_kargo": s.fast_shipping,
            })

        prices = [float(s.price) for s in sellers if s.price]
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        buybox_price = float(sellers[0].price) if sellers and sellers[0].price else None

        results.append({
            "urun": product.product_name[:80] if product.product_name else product.sku,
            "sku": product.sku,
            "platform": product.platform,
            "satici_sayisi": len(sellers),
            "buybox_fiyat": buybox_price,
            "en_dusuk_fiyat": min_price,
            "en_yuksek_fiyat": max_price,
            "fiyat_farki_yuzde": round((max_price - min_price) / min_price * 100, 1) if min_price and max_price and min_price > 0 else 0,
            "saticilar": seller_data[:5],
        })

    return {
        "incelenen_urun": len(results),
        "urunler": results,
    }


async def suggest_campaign_price(
    user_id: str, db: Session, sku: str = "", target_margin: float = 0.15, **kwargs
) -> dict:
    """Hedef kar marjina göre kampanya fiyat önerisi. Komisyon + kargo dahil."""
    query = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,  # noqa: E712
    )
    if sku:
        query = query.filter(MonitoredProduct.sku.ilike(f"%{sku}%"))

    products = query.limit(20).all()
    if not products:
        return {"mesaj": "İzlenen ürün bulunamadı."}

    # Platform komisyon oranlari (tahmini)
    commission_rates = {
        "hepsiburada": 0.12,
        "trendyol": 0.15,
    }

    suggestions = []
    for product in products:
        unit_cost = float(product.unit_cost) if product.unit_cost else None
        shipping_cost = float(product.shipping_cost) if product.shipping_cost else 0

        if not unit_cost:
            continue

        commission_rate = commission_rates.get(product.platform, 0.12)

        # Formul: fiyat = (maliyet + kargo) / (1 - komisyon - hedef_marj)
        denominator = 1 - commission_rate - target_margin
        if denominator <= 0:
            continue

        suggested_price = round((unit_cost + shipping_cost) / denominator, 2)

        # Mevcut buybox fiyatini al
        current_snapshot = (
            db.query(SellerSnapshot)
            .filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.buybox_order == 1,
            )
            .order_by(desc(SellerSnapshot.snapshot_date))
            .first()
        )

        current_price = float(current_snapshot.price) if current_snapshot and current_snapshot.price else None

        net_profit = suggested_price - unit_cost - shipping_cost - (suggested_price * commission_rate)

        suggestions.append({
            "urun": product.product_name[:80] if product.product_name else product.sku,
            "sku": product.sku,
            "platform": product.platform,
            "birim_maliyet": unit_cost,
            "kargo_bedeli": shipping_cost,
            "komisyon_orani": f"%{commission_rate * 100:.0f}",
            "hedef_marj": f"%{target_margin * 100:.0f}",
            "onerilen_fiyat": suggested_price,
            "mevcut_buybox_fiyat": current_price,
            "tahmini_net_kar": round(net_profit, 2),
            "fiyat_farki": round(suggested_price - current_price, 2) if current_price else None,
        })

    return {
        "hedef_kar_marji": f"%{target_margin * 100:.0f}",
        "urun_sayisi": len(suggestions),
        "oneriler": suggestions,
    }
