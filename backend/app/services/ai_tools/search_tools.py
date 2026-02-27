"""Arama ve portföy AI tool fonksiyonları."""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.models import MonitoredProduct, SearchTask, SellerSnapshot

logger = logging.getLogger(__name__)


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

    return {
        "toplam_urun": total,
        "platform_dagilimi": {p: c for p, c in platform_counts},
        "esik_tanimli": with_threshold,
        "maliyet_girilmis": with_cost,
        "son_tarama": latest_fetch.isoformat() if latest_fetch else None,
    }
