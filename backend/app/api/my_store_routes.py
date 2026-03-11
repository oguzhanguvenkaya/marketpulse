"""Mağazam (My Store) — CSV import, cross-platform product matching ve detay API'leri."""

import csv
import io
import json
import logging
import re
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.db.database import get_db
from app.db.models import MyStoreProduct, MonitoredProduct, SellerSnapshot, User
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/my-store",
    tags=["My Store"],
    dependencies=[Depends(get_current_user)],
)


# ──────────────────────────────────────────────────────────────
# AUTO_MATCH: DB field → possible CSV header names (lowercase)
# ──────────────────────────────────────────────────────────────
AUTO_MATCH: dict[str, list[str]] = {
    "title": ["baslik", "başlık", "title", "ürün adı", "urun adi", "product_name"],
    "barcode": ["barkod", "barkodu", "barcode", "ean"],
    "brand": ["marka", "brand"],
    "price": ["fiyat", "fiyat9", "price", "satis_fiyati"],
    "stock_code": ["stokkodu", "stok_kodu", "stock_code", "sku_code"],
    "hepsiburada_sku": ["hepsiburada_sku", "hb_sku", "hbsku"],
    "subtitle": ["altbaslik", "alt_baslik", "subtitle"],
    "category": ["kategori", "category"],
    "category_path": ["kategori_1", "category_path"],
    "supplier": ["toptanci", "tedarikçi", "supplier"],
    "image_url": ["resim", "image", "image_url", "gorsel"],
    "image_url_2": ["resim2", "image2"],
    "image_list": ["resimlistesi", "image_list", "images"],
    "web_url": ["url", "web_url", "link"],
    "detail_html": ["detay", "detail", "aciklama", "description"],
    "seo_link": ["seolink", "seo_link"],
    "meta_title": ["metatitle", "meta_title"],
    "meta_description": ["metadescription", "meta_description"],
    "meta_keywords": ["metakey", "meta_keywords"],
}


def _suggest_mapping(csv_headers: list[str]) -> dict[str, str]:
    """CSV header'larını AUTO_MATCH kullanarak DB alanlarıyla otomatik eşle."""
    mapping: dict[str, str] = {}
    for db_field, aliases in AUTO_MATCH.items():
        for header in csv_headers:
            if header.strip().lower().replace(" ", "").replace("_", "") in [
                a.replace(" ", "").replace("_", "") for a in aliases
            ]:
                mapping[db_field] = header.strip()
                break
    return mapping


def _parse_csv_text(text: str) -> tuple[list[dict[str, str]], list[str], str]:
    """CSV text'i parse eder → (rows, headers, delimiter)."""
    first_lines = text.split("\n", 3)[:3]
    sample = "\n".join(first_lines)
    delimiters = {";": sample.count(";"), ",": sample.count(","), "\t": sample.count("\t")}
    delimiter = max(delimiters, key=delimiters.get) if max(delimiters.values()) > 0 else ";"

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    headers = [h.strip() for h in (reader.fieldnames or []) if h]
    rows = []
    for row in reader:
        cleaned = {}
        for k, v in row.items():
            if k is not None:
                cleaned[k.strip()] = v.strip() if v else ""
        rows.append(cleaned)
    return rows, headers, delimiter


def _safe_float(val) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def _fix_barcode(raw: str) -> str:
    """Fix Excel scientific notation barcodes like '8,02749E+12' → '8027490000000'."""
    if not raw:
        return raw
    # Detect scientific notation with comma decimal (Excel Turkish locale)
    if re.match(r"^\d+,\d+E\+\d+$", raw, re.IGNORECASE):
        try:
            num = float(raw.replace(",", "."))
            return str(int(num))
        except (ValueError, OverflowError):
            return raw
    # Detect scientific notation with dot decimal
    if re.match(r"^\d+\.\d+[Ee]\+?\d+$", raw):
        try:
            num = float(raw)
            return str(int(num))
        except (ValueError, OverflowError):
            return raw
    return raw


def _serialize_my_store_product(p: MyStoreProduct, hb_match=None, ty_match=None) -> dict:
    """Unified product list serialization with platform match info."""
    platforms = ["web"]
    platform_summary = {
        "web": {
            "price": float(p.price) if p.price else None,
            "url": p.web_url,
            "image_count": len(p.image_list) if p.image_list else (2 if p.image_url_2 else (1 if p.image_url else 0)),
        }
    }

    if hb_match:
        platforms.append("hepsiburada")
        platform_summary["hepsiburada"] = {
            "product_id": str(hb_match.id),
            "price": float(hb_match.threshold_price) if hb_match.threshold_price else None,
            "seller_count": hb_match.seller_count if hasattr(hb_match, "seller_count") else 0,
            "last_fetched": hb_match.last_fetched_at.isoformat() if hb_match.last_fetched_at else None,
            "is_active": hb_match.is_active,
            "sku": hb_match.sku,
            "product_name": hb_match.product_name,
        }

    if ty_match:
        platforms.append("trendyol")
        platform_summary["trendyol"] = {
            "product_id": str(ty_match.id),
            "price": float(ty_match.threshold_price) if ty_match.threshold_price else None,
            "seller_count": ty_match.seller_count if hasattr(ty_match, "seller_count") else 0,
            "last_fetched": ty_match.last_fetched_at.isoformat() if ty_match.last_fetched_at else None,
            "is_active": ty_match.is_active,
            "sku": ty_match.sku,
            "product_name": ty_match.product_name,
        }

    return {
        "id": p.id,
        "title": p.title,
        "subtitle": p.subtitle,
        "barcode": p.barcode,
        "stock_code": p.stock_code,
        "brand": p.brand,
        "price": float(p.price) if p.price else None,
        "image_url": p.image_url,
        "web_url": p.web_url,
        "hepsiburada_sku": p.hepsiburada_sku,
        "category": p.category,
        "category_path": p.category_path,
        "is_active": p.is_active,
        "platforms": platforms,
        "platform_summary": platform_summary,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _get_seller_count(db: Session, product_id) -> int:
    """MonitoredProduct için en son snapshot'taki satıcı sayısını döndür."""
    latest_date = db.query(func.max(SellerSnapshot.snapshot_date)).filter(
        SellerSnapshot.monitored_product_id == product_id
    ).scalar()
    if not latest_date:
        return 0
    return db.query(func.count(SellerSnapshot.id)).filter(
        SellerSnapshot.monitored_product_id == product_id,
        SellerSnapshot.snapshot_date == latest_date,
    ).scalar() or 0


def _get_latest_seller_price(db: Session, product_id) -> Optional[float]:
    """MonitoredProduct için en son buybox fiyatını döndür."""
    latest_date = db.query(func.max(SellerSnapshot.snapshot_date)).filter(
        SellerSnapshot.monitored_product_id == product_id
    ).scalar()
    if not latest_date:
        return None
    buybox = db.query(SellerSnapshot).filter(
        SellerSnapshot.monitored_product_id == product_id,
        SellerSnapshot.snapshot_date == latest_date,
    ).order_by(SellerSnapshot.buybox_order.asc().nullslast()).first()
    if buybox and buybox.price:
        return float(buybox.price)
    return None


# ──────────────────────────────────────────────────────────────
# CSV Import
# ──────────────────────────────────────────────────────────────


@router.post("/preview-csv")
async def preview_csv(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """CSV dosyasını parse edip header + önizleme + otomatik eşleme döndürür."""
    if not file.filename:
        raise HTTPException(400, "Dosya adı gerekli")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("csv",):
        raise HTTPException(400, "Sadece CSV formatı desteklenir")

    content = await file.read()
    text = content.decode("utf-8-sig")
    rows, headers, delimiter = _parse_csv_text(text)

    if not headers:
        raise HTTPException(400, "CSV dosyasında başlık satırı bulunamadı")

    preview_rows = rows[:5]  # İlk 5 satır önizleme
    suggested_mapping = _suggest_mapping(headers)

    return {
        "headers": headers,
        "preview_rows": preview_rows,
        "row_count": len(rows),
        "delimiter": delimiter,
        "suggested_mapping": suggested_mapping,
    }


def _get_field_from_row(row: dict, mapping: dict[str, str], field: str) -> str:
    """Mapping'e göre row'dan field değerini oku."""
    csv_col = mapping.get(field, "")
    if not csv_col:
        return ""
    return row.get(csv_col, "").strip()


@router.post("/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    mapping: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Web sitesi ürünlerini CSV dosyasından import et. Opsiyonel mapping ile dinamik sütun eşleme."""
    if not file.filename:
        raise HTTPException(400, "Dosya adı gerekli")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("csv",):
        raise HTTPException(400, "Sadece CSV formatı desteklenir")

    content = await file.read()
    text = content.decode("utf-8-sig")
    rows, headers, delimiter = _parse_csv_text(text)

    if not rows:
        raise HTTPException(400, "CSV dosyasında veri bulunamadı")

    # Parse mapping JSON if provided
    col_mapping: dict[str, str] | None = None
    if mapping:
        try:
            col_mapping = json.loads(mapping)
        except json.JSONDecodeError:
            raise HTTPException(400, "Geçersiz mapping formatı")

    added = 0
    updated = 0
    errors = []

    # Track barcodes seen in this CSV batch to handle duplicates
    seen_barcodes: dict[str, "MyStoreProduct"] = {}

    for i, row in enumerate(rows, start=2):
        if col_mapping:
            # Dynamic mapping mode
            title = _get_field_from_row(row, col_mapping, "title")
            barcode_raw = _get_field_from_row(row, col_mapping, "barcode")
            image_list_raw = _get_field_from_row(row, col_mapping, "image_list")

            data_fields = {
                "title": title,
                "subtitle": _get_field_from_row(row, col_mapping, "subtitle"),
                "seo_link": _get_field_from_row(row, col_mapping, "seo_link"),
                "stock_code": _get_field_from_row(row, col_mapping, "stock_code"),
                "meta_keywords": _get_field_from_row(row, col_mapping, "meta_keywords"),
                "meta_title": _get_field_from_row(row, col_mapping, "meta_title"),
                "meta_description": _get_field_from_row(row, col_mapping, "meta_description"),
                "category": _get_field_from_row(row, col_mapping, "category"),
                "brand": _get_field_from_row(row, col_mapping, "brand"),
                "supplier": _get_field_from_row(row, col_mapping, "supplier"),
                "price": _safe_float(_get_field_from_row(row, col_mapping, "price")),
                "detail_html": _get_field_from_row(row, col_mapping, "detail_html"),
                "hepsiburada_sku": _get_field_from_row(row, col_mapping, "hepsiburada_sku"),
                "category_path": _get_field_from_row(row, col_mapping, "category_path"),
                "image_url": _get_field_from_row(row, col_mapping, "image_url"),
                "image_url_2": _get_field_from_row(row, col_mapping, "image_url_2"),
                "web_url": _get_field_from_row(row, col_mapping, "web_url"),
            }
        else:
            # Legacy fixed-column mode (backward compatible)
            title = row.get("Baslik", "").strip()
            barcode_raw = row.get("Barkodu", "").strip()
            image_list_raw = row.get("ResimListesi", "")

            data_fields = {
                "title": title,
                "subtitle": row.get("AltBaslik", ""),
                "seo_link": row.get("SeoLink", ""),
                "stock_code": row.get("StokKodu", ""),
                "meta_keywords": row.get("MetaKey", ""),
                "meta_title": row.get("MetaTitle", ""),
                "meta_description": row.get("MetaDescription", ""),
                "category": row.get("Kategori", ""),
                "brand": row.get("Marka", ""),
                "supplier": row.get("Toptanci", ""),
                "price": _safe_float(row.get("Fiyat9")),
                "detail_html": row.get("Detay", ""),
                "hepsiburada_sku": row.get("Hepsiburada_SKU", ""),
                "category_path": row.get("Kategori_1", ""),
                "image_url": row.get("Resim", ""),
                "image_url_2": row.get("Resim2", ""),
                "web_url": row.get("Url", ""),
            }

        if not title:
            errors.append({"row": i, "error": "Başlık boş"})
            continue

        # Fix Excel scientific notation barcodes
        barcode = _fix_barcode(barcode_raw) if barcode_raw else None

        # Image list: semicolon-separated URLs
        image_list = [url.strip() for url in image_list_raw.split(";") if url.strip()] if image_list_raw else []

        data = {
            **data_fields,
            "barcode": barcode or None,
            "image_list": image_list if image_list else None,
        }

        # Upsert: barcode + user_id
        existing = None
        if barcode:
            if barcode in seen_barcodes:
                existing = seen_barcodes[barcode]
            else:
                existing = db.query(MyStoreProduct).filter(
                    MyStoreProduct.user_id == user.id,
                    MyStoreProduct.barcode == barcode,
                ).first()

        if existing:
            for key, val in data.items():
                if val is not None and val != "":
                    setattr(existing, key, val)
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            product = MyStoreProduct(user_id=user.id, **data)
            db.add(product)
            if barcode:
                seen_barcodes[barcode] = product
            added += 1

    db.commit()

    return {
        "added": added,
        "updated": updated,
        "errors": errors,
        "total": len(rows),
    }


# ──────────────────────────────────────────────────────────────
# Product List (unified with platform matching)
# ──────────────────────────────────────────────────────────────


@router.get("/products")
async def list_products(
    platform_filter: str = Query("all", description="all/web/hepsiburada/trendyol"),
    search: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unified product list with cross-platform matching."""
    q = db.query(MyStoreProduct).filter(MyStoreProduct.user_id == user.id)

    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(
            MyStoreProduct.title.ilike(search_term),
            MyStoreProduct.barcode.ilike(search_term),
            MyStoreProduct.stock_code.ilike(search_term),
            MyStoreProduct.hepsiburada_sku.ilike(search_term),
            MyStoreProduct.brand.ilike(search_term),
        ))

    if brand:
        q = q.filter(MyStoreProduct.brand == brand)

    # Total count before pagination
    total = q.count()

    # Fetch products
    products = q.order_by(MyStoreProduct.title).offset(offset).limit(limit).all()

    # Batch load HB and TY matches
    barcodes = [p.barcode for p in products if p.barcode]
    hb_skus = [p.hepsiburada_sku for p in products if p.hepsiburada_sku]

    hb_matches = {}
    if hb_skus:
        hb_products = db.query(MonitoredProduct).filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.platform == "hepsiburada",
            MonitoredProduct.sku.in_(hb_skus),
        ).all()
        for mp in hb_products:
            hb_matches[mp.sku] = mp

    ty_matches = {}
    if barcodes:
        ty_products = db.query(MonitoredProduct).filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.platform == "trendyol",
            MonitoredProduct.barcode.in_(barcodes),
        ).all()
        for mp in ty_products:
            if mp.barcode:
                ty_matches[mp.barcode] = mp

    # Batch load seller counts + latest prices for matched products
    all_mp_ids = [mp.id for mp in list(hb_matches.values()) + list(ty_matches.values())]
    seller_counts = {}
    seller_prices = {}
    if all_mp_ids:
        for mp_id in all_mp_ids:
            seller_counts[mp_id] = _get_seller_count(db, mp_id)
            seller_prices[mp_id] = _get_latest_seller_price(db, mp_id)

    # Serialize with matches
    result = []
    for p in products:
        hb = hb_matches.get(p.hepsiburada_sku) if p.hepsiburada_sku else None
        ty = ty_matches.get(p.barcode) if p.barcode else None

        # Platform filter
        if platform_filter == "hepsiburada" and not hb:
            continue
        if platform_filter == "trendyol" and not ty:
            continue
        if platform_filter == "web" and (hb or ty):
            continue  # "web only" = sadece web'de olan

        # Attach seller count + price to match objects
        if hb:
            hb.seller_count = seller_counts.get(hb.id, 0)
            hb_price = seller_prices.get(hb.id)
            if hb_price and not hb.threshold_price:
                hb.threshold_price = hb_price
        if ty:
            ty.seller_count = seller_counts.get(ty.id, 0)
            ty_price = seller_prices.get(ty.id)
            if ty_price and not ty.threshold_price:
                ty.threshold_price = ty_price

        result.append(_serialize_my_store_product(p, hb, ty))

    # Stats
    total_web = db.query(func.count(MyStoreProduct.id)).filter(
        MyStoreProduct.user_id == user.id
    ).scalar() or 0

    hb_matched_count = len(hb_matches)
    ty_matched_count = len(ty_matches)

    return {
        "products": result,
        "total": len(result) if platform_filter != "all" else total,
        "limit": limit,
        "offset": offset,
        "stats": {
            "web_count": total_web,
            "hb_matched": hb_matched_count,
            "ty_matched": ty_matched_count,
        },
    }


# ──────────────────────────────────────────────────────────────
# Product Detail (with full platform data)
# ──────────────────────────────────────────────────────────────


def _serialize_seller_snapshot(s: SellerSnapshot) -> dict:
    return {
        "merchant_id": s.merchant_id,
        "merchant_name": s.merchant_name,
        "merchant_logo": s.merchant_logo,
        "merchant_url_postfix": s.merchant_url_postfix,
        "merchant_rating": s.merchant_rating,
        "merchant_rating_count": s.merchant_rating_count,
        "merchant_city": s.merchant_city,
        "price": float(s.price) if s.price else None,
        "original_price": float(s.original_price) if s.original_price else None,
        "minimum_price": float(s.minimum_price) if s.minimum_price else None,
        "discount_rate": s.discount_rate,
        "stock_quantity": s.stock_quantity,
        "buybox_order": s.buybox_order,
        "free_shipping": s.free_shipping,
        "fast_shipping": s.fast_shipping,
        "is_fulfilled_by_hb": s.is_fulfilled_by_hb,
        "campaigns": s.campaigns or [],
        "campaign_price": float(s.campaign_price) if s.campaign_price else None,
        "snapshot_date": s.snapshot_date.isoformat() if s.snapshot_date else None,
    }


def _get_platform_detail(db: Session, mp: MonitoredProduct) -> dict:
    """MonitoredProduct + en son seller snapshots."""
    latest_date = db.query(func.max(SellerSnapshot.snapshot_date)).filter(
        SellerSnapshot.monitored_product_id == mp.id
    ).scalar()

    sellers = []
    if latest_date:
        snapshots = db.query(SellerSnapshot).filter(
            SellerSnapshot.monitored_product_id == mp.id,
            SellerSnapshot.snapshot_date == latest_date,
        ).order_by(SellerSnapshot.buybox_order.asc().nullslast()).all()
        sellers = [_serialize_seller_snapshot(s) for s in snapshots]

    return {
        "product": {
            "id": str(mp.id),
            "sku": mp.sku,
            "barcode": mp.barcode,
            "product_name": mp.product_name,
            "product_url": mp.product_url,
            "brand": mp.brand,
            "image_url": mp.image_url,
            "is_active": mp.is_active,
            "threshold_price": float(mp.threshold_price) if mp.threshold_price else None,
            "alert_campaign_price": float(mp.alert_campaign_price) if mp.alert_campaign_price else None,
            "last_fetched_at": mp.last_fetched_at.isoformat() if mp.last_fetched_at else None,
        },
        "sellers": sellers,
        "seller_count": len(sellers),
    }


@router.get("/products/{product_id}")
async def get_product_detail(
    product_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full product detail with all platform data."""
    product = db.query(MyStoreProduct).filter(
        MyStoreProduct.id == product_id,
        MyStoreProduct.user_id == user.id,
    ).first()
    if not product:
        raise HTTPException(404, "Ürün bulunamadı")

    # Web data
    web_data = {
        "title": product.title,
        "subtitle": product.subtitle,
        "stock_code": product.stock_code,
        "barcode": product.barcode,
        "brand": product.brand,
        "supplier": product.supplier,
        "price": float(product.price) if product.price else None,
        "category": product.category,
        "category_path": product.category_path,
        "detail_html": product.detail_html,
        "image_url": product.image_url,
        "image_url_2": product.image_url_2,
        "image_list": product.image_list or [],
        "web_url": product.web_url,
        "meta_title": product.meta_title,
        "meta_description": product.meta_description,
        "meta_keywords": product.meta_keywords,
        "seo_link": product.seo_link,
    }

    # HB match
    hb_data = None
    if product.hepsiburada_sku:
        hb_mp = db.query(MonitoredProduct).filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.platform == "hepsiburada",
            MonitoredProduct.sku == product.hepsiburada_sku,
        ).first()
        if hb_mp:
            hb_data = _get_platform_detail(db, hb_mp)

    # TY match
    ty_data = None
    if product.barcode:
        ty_mp = db.query(MonitoredProduct).filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.platform == "trendyol",
            MonitoredProduct.barcode == product.barcode,
        ).first()
        if ty_mp:
            ty_data = _get_platform_detail(db, ty_mp)

    return {
        "web": web_data,
        "hepsiburada": hb_data,
        "trendyol": ty_data,
    }


# ──────────────────────────────────────────────────────────────
# Delete & Brands
# ──────────────────────────────────────────────────────────────


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(MyStoreProduct).filter(
        MyStoreProduct.id == product_id,
        MyStoreProduct.user_id == user.id,
    ).first()
    if not product:
        raise HTTPException(404, "Ürün bulunamadı")
    db.delete(product)
    db.commit()
    return {"message": "Ürün silindi"}


@router.delete("/products/bulk/all")
async def delete_all_products(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = db.query(MyStoreProduct).filter(
        MyStoreProduct.user_id == user.id,
    ).delete(synchronize_session="fetch")
    db.commit()
    return {"message": f"{deleted} ürün silindi", "deleted": deleted}


@router.get("/brands")
async def list_brands(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    brands = db.query(MyStoreProduct.brand).filter(
        MyStoreProduct.user_id == user.id,
        MyStoreProduct.brand.isnot(None),
        MyStoreProduct.brand != "",
    ).distinct().order_by(MyStoreProduct.brand).all()
    return {"brands": [b[0] for b in brands]}


@router.get("/stats")
async def get_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(MyStoreProduct.id)).filter(
        MyStoreProduct.user_id == user.id
    ).scalar() or 0

    # HB matched
    hb_matched = db.query(func.count(MyStoreProduct.id)).filter(
        MyStoreProduct.user_id == user.id,
        MyStoreProduct.hepsiburada_sku.isnot(None),
        MyStoreProduct.hepsiburada_sku != "",
        MonitoredProduct.sku == MyStoreProduct.hepsiburada_sku,
        MonitoredProduct.user_id == user.id,
        MonitoredProduct.platform == "hepsiburada",
    ).scalar() or 0

    # TY matched
    ty_matched = db.query(func.count(MyStoreProduct.id)).filter(
        MyStoreProduct.user_id == user.id,
        MyStoreProduct.barcode.isnot(None),
        MyStoreProduct.barcode != "",
        MonitoredProduct.barcode == MyStoreProduct.barcode,
        MonitoredProduct.user_id == user.id,
        MonitoredProduct.platform == "trendyol",
    ).scalar() or 0

    return {
        "total": total,
        "hb_matched": hb_matched,
        "ty_matched": ty_matched,
    }
