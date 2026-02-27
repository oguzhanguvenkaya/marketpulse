"""AI Agent aksiyon tool'ları — yazma/değiştirme işlemleri (onay gerektirir)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import MonitoredProduct, CompetitorSeller, SearchTask

logger = logging.getLogger(__name__)


async def add_sku_to_monitor(
    user_id: str,
    db: Session,
    sku: str = "",
    platform: str = "hepsiburada",
    threshold_price: float | None = None,
    **kwargs,
) -> dict:
    """SKU'yu izleme listesine ekle."""
    if not sku:
        return {"hata": "SKU belirtilmedi"}

    # Duplicate kontrolü
    existing = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.platform == platform,
        MonitoredProduct.sku == sku,
    ).first()

    if existing:
        return {
            "durum": "zaten_var",
            "mesaj": f"'{sku}' zaten izleniyor (platform: {platform})",
            "urun_id": str(existing.id),
        }

    product = MonitoredProduct(
        id=uuid.uuid4(),
        user_id=user_id,
        platform=platform,
        sku=sku,
        product_url=f"https://www.{platform}.com/{sku}" if platform == "hepsiburada" else f"https://www.{platform}.com/{sku}",
        threshold_price=threshold_price,
        is_active=True,
    )
    db.add(product)
    db.commit()

    return {
        "durum": "eklendi",
        "mesaj": f"'{sku}' izleme listesine eklendi",
        "urun_id": str(product.id),
        "platform": platform,
        "esik_fiyat": threshold_price,
    }


async def add_competitor(
    user_id: str,
    db: Session,
    seller_id: str = "",
    seller_name: str = "",
    platform: str = "hepsiburada",
    **kwargs,
) -> dict:
    """Rakip satıcı ekle."""
    if not seller_id or not seller_name:
        return {"hata": "seller_id ve seller_name gerekli"}

    existing = db.query(CompetitorSeller).filter(
        CompetitorSeller.user_id == user_id,
        CompetitorSeller.platform == platform,
        CompetitorSeller.seller_id == seller_id,
    ).first()

    if existing:
        return {
            "durum": "zaten_var",
            "mesaj": f"'{seller_name}' zaten rakip listesinde",
        }

    competitor = CompetitorSeller(
        user_id=user_id,
        platform=platform,
        seller_id=seller_id,
        seller_name=seller_name,
    )
    db.add(competitor)
    db.commit()

    return {
        "durum": "eklendi",
        "mesaj": f"'{seller_name}' rakip olarak eklendi",
        "rakip_id": str(competitor.id),
    }


async def set_price_alert(
    user_id: str,
    db: Session,
    sku: str = "",
    threshold_price: float = 0,
    platform: str = "hepsiburada",
    **kwargs,
) -> dict:
    """Ürün için fiyat eşiği ayarla."""
    if not sku:
        return {"hata": "SKU belirtilmedi"}

    product = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.sku == sku,
        MonitoredProduct.platform == platform,
    ).first()

    if not product:
        return {"hata": f"'{sku}' izleme listesinde bulunamadı"}

    old_threshold = float(product.threshold_price) if product.threshold_price else None
    product.threshold_price = threshold_price
    db.commit()

    return {
        "durum": "guncellendi",
        "mesaj": f"'{sku}' fiyat eşiği {threshold_price} TL olarak ayarlandı",
        "onceki_esik": old_threshold,
        "yeni_esik": threshold_price,
    }


async def start_keyword_search(
    user_id: str,
    db: Session,
    keyword: str = "",
    platform: str = "hepsiburada",
    **kwargs,
) -> dict:
    """Keyword araması başlat."""
    if not keyword:
        return {"hata": "Keyword belirtilmedi"}

    task = SearchTask(
        user_id=user_id,
        keyword=keyword,
        platform=platform,
        status="pending",
    )
    db.add(task)
    db.commit()

    return {
        "durum": "baslatildi",
        "mesaj": f"'{keyword}' araması başlatıldı ({platform})",
        "task_id": str(task.id),
    }
