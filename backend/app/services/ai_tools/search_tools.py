"""Arama ve portföy AI tool fonksiyonları."""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.logger import get_logger
from app.db.models import MonitoredProduct, SearchTask, SellerSnapshot

logger = get_logger("ai.tools.search")


async def search_keyword_analysis(user_id: str, db: Session, keyword: str = "", **kwargs) -> dict:
    """Keyword arama sonuçlarını analiz et."""
    tasks = db.query(SearchTask).filter(
        SearchTask.user_id == user_id,
        SearchTask.keyword.ilike(f"%{keyword}%"),
        SearchTask.status == "completed",
    ).order_by(desc(SearchTask.created_at)).limit(5).all()

    if not tasks:
        return {"mesaj": f"'{keyword}' ile ilgili arama sonucu bulunamadı"}

    return {
        "keyword": keyword,
        "toplam_arama": len(tasks),
        "aramalar": [
            {
                "tarih": t.created_at.isoformat(),
                "platform": t.platform,
                "bulunan_urun": t.total_products,
            }
            for t in tasks
        ],
    }


async def get_portfolio_summary(user_id: str, db: Session, **kwargs) -> dict:
    """Kullanıcının portföy özetini döndür."""
    # Platform bazlı ürün sayıları
    platform_counts = db.query(
        MonitoredProduct.platform,
        func.count(MonitoredProduct.id).label("count"),
    ).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,
    ).group_by(MonitoredProduct.platform).all()

    total = sum(c for _, c in platform_counts)

    # Threshold tanımlı ürün sayısı
    with_threshold = db.query(func.count(MonitoredProduct.id)).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,
        MonitoredProduct.threshold_price.isnot(None),
    ).scalar() or 0

    # Maliyet girilmiş ürün sayısı
    with_cost = db.query(func.count(MonitoredProduct.id)).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,
        MonitoredProduct.unit_cost.isnot(None),
    ).scalar() or 0

    # Son tarama
    latest_fetch = db.query(func.max(MonitoredProduct.last_fetched_at)).filter(
        MonitoredProduct.user_id == user_id,
    ).scalar()

    # Benzersiz satici sayisi (son snapshot'lardan)
    from sqlalchemy import distinct, select
    product_ids_select = select(MonitoredProduct.id).where(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,
    )

    unique_sellers = db.query(
        func.count(distinct(SellerSnapshot.merchant_id))
    ).filter(
        SellerSnapshot.monitored_product_id.in_(product_ids_select)
    ).scalar() or 0

    return {
        "toplam_urun": total,
        "platform_dagilimi": {p: c for p, c in platform_counts},
        "toplam_benzersiz_satici": unique_sellers,
        "esik_tanimli": with_threshold,
        "maliyet_girilmis": with_cost,
        "son_tarama": latest_fetch.isoformat() if latest_fetch else None,
    }


async def search_products_by_name(
    user_id: str, db: Session, product_name: str = "", platform: str = "", **kwargs
) -> dict:
    """Izlenen urunler arasinda ada gore hybrid arama yap.

    pg_trgm (fuzzy) + tsvector (keyword) + pgvector (semantic) ile arar.
    Embedding yoksa ILIKE fallback aktif.
    """
    if not product_name:
        return {"hata": "product_name parametresi gerekli."}

    from app.services.hybrid_search_service import hybrid_search_monitored

    products = await hybrid_search_monitored(
        db=db, user_id=user_id, query=product_name, platform=platform, limit=10,
    )

    if not products:
        return {"mesaj": f"'{product_name}' ile eslesen izlenen urun bulunamadi."}

    # Tek sorguda tum urunler icin en son buybox snapshot'larini cek
    from app.services.ai_tools.price_tools import _get_latest_buybox_map
    product_ids = [p.id for p in products]
    snapshot_map = _get_latest_buybox_map(db, product_ids)

    results = []
    for p in products:
        latest = snapshot_map.get(p.id)

        results.append({
            "sku": p.sku,
            "urun_adi": p.product_name,
            "platform": p.platform,
            "urun_id": str(p.id),
            "mevcut_fiyat": float(latest.price) if latest and latest.price else None,
            "buybox_satici": latest.merchant_name if latest else None,
            "gorsel": p.image_url,
            "urun_url": p.product_url,
        })

    return {
        "bulunan": len(results),
        "urunler": results,
    }
