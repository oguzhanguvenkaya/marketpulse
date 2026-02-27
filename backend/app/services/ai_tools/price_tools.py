"""Fiyat izleme ile ilgili AI tool fonksiyonları."""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta

from app.db.models import MonitoredProduct, SellerSnapshot, AlertLog

logger = logging.getLogger(__name__)


async def get_price_alerts(user_id: str, db: Session, **kwargs) -> dict:
    """Kullanıcının aktif fiyat alarmlarını ve son threshold ihlallerini döndür."""
    products = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,
        MonitoredProduct.threshold_price.isnot(None),
    ).all()

    alerts = []
    for product in products:
        latest = db.query(SellerSnapshot).filter(
            SellerSnapshot.monitored_product_id == product.id,
            SellerSnapshot.buybox_order == 1,
        ).order_by(desc(SellerSnapshot.snapshot_date)).first()

        if latest and latest.price and product.threshold_price:
            current_price = float(latest.price)
            threshold = float(product.threshold_price)
            if current_price < threshold:
                alerts.append({
                    "urun": product.product_name or product.sku,
                    "sku": product.sku,
                    "platform": product.platform,
                    "guncel_fiyat": current_price,
                    "esik_fiyat": threshold,
                    "fark_tl": round(threshold - current_price, 2),
                    "satici": latest.merchant_name,
                })

    # Son 24 saat alert log
    recent_count = db.query(func.count(AlertLog.id)).filter(
        AlertLog.user_id == user_id,
        AlertLog.created_at >= datetime.utcnow() - timedelta(hours=24),
    ).scalar() or 0

    return {
        "toplam_izlenen": len(products),
        "esik_ihlali_sayisi": len(alerts),
        "son_24_saat_alarm": recent_count,
        "ihlaller": alerts[:10],
    }


async def compare_seller_prices(user_id: str, db: Session, sku: str = "", platform: str = "hepsiburada", **kwargs) -> dict:
    """Belirli bir SKU için tüm satıcı fiyatlarını karşılaştır."""
    product = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.sku == sku,
        MonitoredProduct.platform == platform,
    ).first()

    if not product:
        return {"hata": f"'{sku}' SKU'su '{platform}' platformunda bulunamadı"}

    # En son snapshot'ları al
    latest_date = db.query(func.max(SellerSnapshot.snapshot_date)).filter(
        SellerSnapshot.monitored_product_id == product.id,
    ).scalar()

    if not latest_date:
        return {"hata": "Bu ürün için henüz fiyat verisi yok"}

    snapshots = db.query(SellerSnapshot).filter(
        SellerSnapshot.monitored_product_id == product.id,
        SellerSnapshot.snapshot_date >= latest_date - timedelta(minutes=30),
    ).order_by(SellerSnapshot.buybox_order).all()

    sellers = []
    for s in snapshots:
        sellers.append({
            "satici": s.merchant_name,
            "fiyat": float(s.price),
            "buybox_sirasi": s.buybox_order,
            "ucretsiz_kargo": s.free_shipping,
            "kampanya_fiyati": float(s.campaign_price) if s.campaign_price else None,
        })

    min_price = min(s["fiyat"] for s in sellers) if sellers else 0
    max_price = max(s["fiyat"] for s in sellers) if sellers else 0

    return {
        "urun": product.product_name or product.sku,
        "sku": product.sku,
        "platform": product.platform,
        "satici_sayisi": len(sellers),
        "en_dusuk_fiyat": min_price,
        "en_yuksek_fiyat": max_price,
        "fiyat_farki": round(max_price - min_price, 2),
        "saticilar": sellers,
    }


async def get_product_insights(user_id: str, db: Session, product_id: str = "", **kwargs) -> dict:
    """Ürün fiyat geçmişi ve trendleri."""
    product = db.query(MonitoredProduct).filter(
        MonitoredProduct.id == product_id,
        MonitoredProduct.user_id == user_id,
    ).first()

    if not product:
        return {"hata": "Ürün bulunamadı"}

    last_7_days = datetime.utcnow() - timedelta(days=7)

    # Buybox fiyat geçmişi
    snapshots = db.query(SellerSnapshot).filter(
        SellerSnapshot.monitored_product_id == product.id,
        SellerSnapshot.buybox_order == 1,
        SellerSnapshot.snapshot_date >= last_7_days,
    ).order_by(SellerSnapshot.snapshot_date).all()

    prices = [float(s.price) for s in snapshots if s.price]

    if not prices:
        return {
            "urun": product.product_name or product.sku,
            "veri_yok": True,
            "mesaj": "Son 7 günde fiyat verisi bulunamadı",
        }

    return {
        "urun": product.product_name or product.sku,
        "sku": product.sku,
        "platform": product.platform,
        "son_7_gun": {
            "ortalama_fiyat": round(sum(prices) / len(prices), 2),
            "en_dusuk": min(prices),
            "en_yuksek": max(prices),
            "veri_noktasi": len(prices),
        },
        "guncel_fiyat": prices[-1] if prices else None,
        "fiyat_trendi": "dusus" if len(prices) >= 2 and prices[-1] < prices[0] else "artis" if len(prices) >= 2 and prices[-1] > prices[0] else "sabit",
    }
