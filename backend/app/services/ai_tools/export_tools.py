"""Veri disa aktarim AI tool fonksiyonlari."""

import csv
import io
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.logger import get_logger
from app.db.models import (
    MonitoredProduct,
    SellerSnapshot,
    CategorySession,
    CategoryProduct,
    SearchTask,
    SearchSponsoredProduct,
)

logger = get_logger("ai.tools.export")

# Gecici dosya deposu (in-memory, 1 saat TTL)
# Production'da Redis veya S3 kullanilabilir
_export_store: dict = {}
# {file_id: {"data": bytes, "filename": str, "content_type": str, "created_at": datetime}}


async def export_data(
    user_id: str,
    db: Session,
    data_type: str = "",
    format: str = "json",
    platform: str = "",
    category_name: str = "",
    **kwargs,
) -> dict:
    """Kullanicinin verisini belirtilen formatta disa aktar."""

    if not data_type:
        return {
            "hata": (
                "data_type parametresi gerekli. "
                "Secenekler: monitored_products, category_products, "
                "seller_prices, search_results"
            )
        }

    if format not in ("json", "csv", "md", "txt"):
        return {
            "hata": f"Desteklenmeyen format: {format}. Secenekler: json, csv, md, txt"
        }

    # Veriyi cek
    if data_type == "monitored_products":
        data = _get_monitored_products(user_id, db, platform)
    elif data_type == "category_products":
        data = _get_category_products(user_id, db, category_name, platform)
    elif data_type == "seller_prices":
        sku = kwargs.get("sku", "")
        data = _get_seller_prices(user_id, db, sku, platform)
    elif data_type == "search_results":
        keyword = kwargs.get("keyword", "")
        data = _get_search_results(user_id, db, keyword)
    else:
        return {
            "hata": (
                f"Bilinmeyen data_type: {data_type}. "
                "Secenekler: monitored_products, category_products, "
                "seller_prices, search_results"
            )
        }

    if not data["rows"]:
        return {"mesaj": "Disa aktarilacak veri bulunamadi."}

    # Formata donustur
    if format == "json":
        content = json.dumps(data["rows"], ensure_ascii=False, indent=2).encode(
            "utf-8"
        )
        content_type = "application/json"
        ext = "json"
    elif format == "csv":
        content = _to_csv(data["rows"]).encode("utf-8")
        content_type = "text/csv"
        ext = "csv"
    elif format == "md":
        content = _to_markdown(data["rows"], data.get("title", "Export")).encode(
            "utf-8"
        )
        content_type = "text/markdown"
        ext = "md"
    else:  # txt
        content = _to_txt(data["rows"], data.get("title", "Export")).encode("utf-8")
        content_type = "text/plain"
        ext = "txt"

    # Dosyayi gecici olarak depola
    file_id = str(uuid.uuid4())[:8]
    filename = (
        f"{data.get('filename_prefix', 'export')}"
        f"_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.{ext}"
    )

    _export_store[file_id] = {
        "data": content,
        "filename": filename,
        "content_type": content_type,
        "created_at": datetime.utcnow(),
    }

    # Eski dosyalari temizle (1 saatten eski)
    _cleanup_old_exports()

    size_kb = len(content) / 1024
    size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"

    return {
        "basarili": True,
        "dosya_id": file_id,
        "dosya_adi": filename,
        "format": format,
        "boyut": size_str,
        "satir_sayisi": len(data["rows"]),
        "indirme_url": f"/api/ai/exports/{file_id}",
    }


# ---------------------------------------------------------------------------
# Veri cekme fonksiyonlari
# ---------------------------------------------------------------------------


def _get_monitored_products(
    user_id: str, db: Session, platform: str = ""
) -> dict:
    """Kullanicinin izledigi urunleri getir, buybox bilgisi dahil."""
    query = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,  # noqa: E712
    )
    if platform:
        query = query.filter(MonitoredProduct.platform == platform)
    products = query.all()

    # Tek sorguda tum urunler icin en son buybox snapshot'larini cek
    from app.services.ai_tools.price_tools import _get_latest_buybox_map
    product_ids = [p.id for p in products]
    snapshot_map = _get_latest_buybox_map(db, product_ids)

    rows = []
    for p in products:
        latest_buybox = snapshot_map.get(p.id)

        rows.append(
            {
                "sku": p.sku,
                "urun_adi": p.product_name or "",
                "platform": p.platform,
                "mevcut_fiyat": float(latest_buybox.price) if latest_buybox and latest_buybox.price else None,
                "buybox_satici": latest_buybox.merchant_name if latest_buybox else "",
                "esik_fiyat": float(p.threshold_price) if p.threshold_price else None,
                "son_guncelleme": p.last_fetched_at.isoformat() if p.last_fetched_at else None,
            }
        )

    return {
        "rows": rows,
        "title": "Izlenen Urunler",
        "filename_prefix": f"urunler_{platform}" if platform else "urunler",
    }


def _get_category_products(
    user_id: str, db: Session, category_name: str = "", platform: str = ""
) -> dict:
    """En son kategori tarama oturumundaki urunleri getir."""
    query = db.query(CategorySession).filter(CategorySession.user_id == user_id)
    if category_name:
        query = query.filter(
            CategorySession.category_name.ilike(f"%{category_name}%")
        )
    if platform:
        query = query.filter(CategorySession.platform == platform)

    session = query.order_by(desc(CategorySession.created_at)).first()
    if not session:
        return {
            "rows": [],
            "title": "Kategori Urunleri",
            "filename_prefix": "kategori",
        }

    products = (
        db.query(CategoryProduct)
        .filter(CategoryProduct.session_id == session.id)
        .order_by(CategoryProduct.position)
        .all()
    )

    rows = []
    for p in products:
        rows.append(
            {
                "sira": p.position,
                "urun_adi": p.name or "",
                "marka": p.brand or "",
                "fiyat": float(p.price) if p.price else None,
                "indirim_yuzde": float(p.discount_percentage) if p.discount_percentage else None,
                "satici": p.seller_name or "",
                "puan": float(p.rating) if p.rating else None,
                "yorum_sayisi": p.review_count,
                "sponsorlu": p.is_sponsored,
                "url": p.url or "",
            }
        )

    cat_name = session.category_name or "kategori"
    return {
        "rows": rows,
        "title": f"{cat_name} Kategorisi Urunleri",
        "filename_prefix": f"kategori_{cat_name.lower().replace(' ', '_')}",
    }


def _get_seller_prices(
    user_id: str, db: Session, sku: str = "", platform: str = ""
) -> dict:
    """Belirli bir SKU icin satici fiyat gecmisini getir."""
    if not sku:
        return {
            "rows": [],
            "title": "Satici Fiyatlari",
            "filename_prefix": "satici_fiyatlari",
        }

    query = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.sku == sku,
    )
    if platform:
        query = query.filter(MonitoredProduct.platform == platform)

    product = query.first()
    if not product:
        return {
            "rows": [],
            "title": "Satici Fiyatlari",
            "filename_prefix": "satici_fiyatlari",
        }

    snapshots = (
        db.query(SellerSnapshot)
        .filter(SellerSnapshot.monitored_product_id == product.id)
        .order_by(desc(SellerSnapshot.snapshot_date))
        .limit(100)
        .all()
    )

    rows = []
    for s in snapshots:
        rows.append(
            {
                "satici": s.merchant_name or "",
                "fiyat": float(s.price) if s.price else None,
                "kampanya_fiyati": float(s.campaign_price) if s.campaign_price else None,
                "buybox_sirasi": s.buybox_order,
                "tarih": s.snapshot_date.isoformat() if s.snapshot_date else None,
            }
        )

    return {
        "rows": rows,
        "title": f"SKU {sku} Satici Fiyatlari",
        "filename_prefix": f"satici_fiyatlari_{sku}",
    }


def _get_search_results(
    user_id: str, db: Session, keyword: str = ""
) -> dict:
    """En son arama gorevinin sponsorlu urun sonuclarini getir."""
    query = db.query(SearchTask).filter(SearchTask.user_id == user_id)
    if keyword:
        query = query.filter(SearchTask.keyword.ilike(f"%{keyword}%"))

    task = query.order_by(desc(SearchTask.created_at)).first()
    if not task:
        return {
            "rows": [],
            "title": "Arama Sonuclari",
            "filename_prefix": "arama",
        }

    products = (
        db.query(SearchSponsoredProduct)
        .filter(SearchSponsoredProduct.search_task_id == task.id)
        .order_by(SearchSponsoredProduct.order_index)
        .all()
    )

    rows = []
    for p in products:
        rows.append(
            {
                "urun_adi": p.product_name or "",
                "fiyat": float(p.price) if p.price else None,
                "indirimli_fiyat": float(p.discounted_price) if p.discounted_price else None,
                "platform": task.platform or "",
                "satici": p.seller_name or "",
                "url": p.product_url or "",
            }
        )

    kw_display = keyword or task.keyword or ""
    return {
        "rows": rows,
        "title": f"'{kw_display}' Arama Sonuclari" if kw_display else "Arama Sonuclari",
        "filename_prefix": (
            f"arama_{kw_display.lower().replace(' ', '_')}" if kw_display else "arama"
        ),
    }


# ---------------------------------------------------------------------------
# Format donusturme fonksiyonlari
# ---------------------------------------------------------------------------


def _to_csv(rows: list) -> str:
    """Satir listesini CSV string'ine donustur."""
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _to_markdown(rows: list, title: str = "") -> str:
    """Satir listesini Markdown tablosuna donustur."""
    if not rows:
        return ""
    lines = []
    if title:
        lines.append(f"# {title}\n")

    headers = list(rows[0].keys())
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in rows:
        vals = [str(row.get(h, "")) for h in headers]
        lines.append("| " + " | ".join(vals) + " |")

    return "\n".join(lines) + "\n"


def _to_txt(rows: list, title: str = "") -> str:
    """Satir listesini duz metin formatina donustur."""
    if not rows:
        return ""
    lines = []
    if title:
        lines.append(f"=== {title} ===\n")

    for i, row in enumerate(rows, 1):
        lines.append(f"--- #{i} ---")
        for k, v in row.items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Depo yardimci fonksiyonlari
# ---------------------------------------------------------------------------


def _cleanup_old_exports() -> None:
    """1 saatten eski dosyalari temizle."""
    cutoff = datetime.utcnow() - timedelta(hours=1)
    expired = [
        fid for fid, info in _export_store.items() if info["created_at"] < cutoff
    ]
    for fid in expired:
        del _export_store[fid]


def get_export_file(file_id: str) -> Optional[dict]:
    """Depolanan dosyayi getir. Bulunamazsa None dondurur."""
    return _export_store.get(file_id)
