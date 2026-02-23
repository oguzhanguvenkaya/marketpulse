import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, text
from typing import List, Optional, Dict, Any
from time import perf_counter

from app.db.database import get_db, SessionLocal
from app.db.models import MonitoredProduct, SellerSnapshot, PriceMonitorTask
from app.core.config import settings
from app.core.logger import api_logger as logger, log_endpoint_metric
from app.core.security import require_mutating_api_key

from app.api._shared import (
    MonitoredProductInput,
    BulkProductsRequest,
    MonitoredProductResponse,
    SellerSnapshotResponse,
    ProductWithSellersResponse,
    FetchTaskResponse,
    _to_float,
    _calculate_price_alerts,
    _resolve_product_url,
    _is_valid_http_url,
    _require_scraper_api_or_503,
    _require_queue_or_503,
    _run_read_query_with_retry,
    _get_price_monitor_service,
    _get_trendyol_price_monitor_service,
    extract_sku_from_url,
)

router = APIRouter(dependencies=[Depends(require_mutating_api_key)])


@router.post("/price-monitor/products")
async def add_monitored_products(
    request: BulkProductsRequest,
    db: Session = Depends(get_db)
):
    """JSON formatında SKU listesi yükle - platform: hepsiburada veya trendyol"""
    added = 0
    updated = 0
    errors = []
    platform = request.platform.lower()

    for item in request.products:
        try:
            sku = item.sku
            if sku:
                if sku.startswith('SKU: '):
                    sku = sku.replace('SKU: ', '')
            else:
                sku = extract_sku_from_url(item.productUrl, platform) if item.productUrl else None

            if not sku:
                errors.append({"url": item.productUrl, "error": "SKU bulunamadı"})
                continue

            resolved_product_url = _resolve_product_url(platform, sku, item.productUrl)

            existing = db.query(MonitoredProduct).filter(
                MonitoredProduct.sku == sku,
                MonitoredProduct.platform == platform
            ).first()

            if existing:
                if resolved_product_url:
                    existing.product_url = resolved_product_url
                if item.productName:
                    existing.product_name = item.productName
                if item.barcode:
                    existing.barcode = item.barcode
                if item.brand:
                    existing.brand = item.brand
                if item.price is not None:
                    existing.threshold_price = item.price
                    if item.campaignPrice is not None:
                        existing.alert_campaign_price = item.campaignPrice
                    else:
                        existing.alert_campaign_price = round(item.price * 0.9, 2)
                elif item.campaignPrice is not None:
                    existing.alert_campaign_price = item.campaignPrice
                if item.sellerStockCode:
                    existing.seller_stock_code = item.sellerStockCode
                existing.is_active = True
                updated += 1
            else:
                campaign_price = item.campaignPrice if item.campaignPrice is not None else (
                    round(item.price * 0.9, 2) if item.price else None
                )
                product = MonitoredProduct(
                    platform=platform,
                    sku=sku,
                    barcode=item.barcode,
                    product_url=resolved_product_url,
                    product_name=item.productName,
                    brand=item.brand,
                    threshold_price=item.price,
                    alert_campaign_price=campaign_price,
                    seller_stock_code=item.sellerStockCode,
                    is_active=True
                )
                db.add(product)
                added += 1
        except Exception as e:
            logger.warning(f"Import error for SKU {item.sku}: {e}")
            logger.error(f"Bulk import item failed (sku={item.sku or item.productUrl}): {type(e).__name__}: {e}")
            errors.append({"sku": item.sku or item.productUrl, "error": "Urun eklenirken hata olustu"})

    db.commit()

    return {
        "added": added,
        "updated": updated,
        "errors": errors,
        "total": len(request.products),
        "platform": platform
    }


@router.get("/price-monitor/products")
async def get_monitored_products(
    db: Session = Depends(get_db),
    active_only: bool = False,
    platform: Optional[str] = None,
    brand: Optional[str] = None,
    price_alert_only: bool = False,
    campaign_alert_only: bool = False,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """İzlenen ürün listesini getir - platform, marka, price/campaign alert ve arama filtresi ile"""
    start_time = perf_counter()
    # --- 1. Build product query with all SQL-level filters ---
    base_query = db.query(MonitoredProduct)
    if platform:
        base_query = base_query.filter(MonitoredProduct.platform == platform.lower())
    if brand:
        base_query = base_query.filter(MonitoredProduct.brand == brand)
    if search:
        search_lower = f"%{search.lower()}%"
        base_query = base_query.filter(
            or_(
                MonitoredProduct.sku.ilike(search_lower),
                MonitoredProduct.barcode.ilike(search_lower),
                MonitoredProduct.product_name.ilike(search_lower),
                MonitoredProduct.seller_stock_code.ilike(search_lower),
            )
        )

    query = base_query
    if active_only:
        query = query.filter(MonitoredProduct.is_active == True)

    query = query.order_by(desc(MonitoredProduct.created_at))

    # When alert filters are active we need to check all products (can't paginate before filtering)
    needs_alert_filter = price_alert_only or campaign_alert_only

    if not needs_alert_filter:
        # --- Single round-trip: products + counts + snapshots via CTE + LATERAL JOIN ---
        combined_rows = _run_read_query_with_retry(
            db,
            lambda: db.execute(
                text("""
                    WITH paged AS (
                        SELECT id, platform, sku, barcode, product_url, product_name, brand,
                               seller_stock_code, threshold_price, alert_campaign_price,
                               image_url, is_active, last_fetched_at,
                               COUNT(*) OVER() AS _total,
                               SUM(CASE WHEN is_active THEN 1 ELSE 0 END) OVER() AS _active
                        FROM monitored_products
                        WHERE TRUE
                          {platform_clause}
                          {brand_clause}
                          {active_clause}
                          {search_clause}
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                    )
                    SELECT p.id, p.platform, p.sku, p.barcode, p.product_url, p.product_name,
                           p.brand, p.seller_stock_code, p.threshold_price, p.alert_campaign_price,
                           p.image_url, p.is_active, p.last_fetched_at, p._total, p._active,
                           s.merchant_id, s.price AS s_price, s.original_price AS s_original, s.campaign_price AS s_campaign
                    FROM paged p
                    LEFT JOIN LATERAL (
                        SELECT DISTINCT ON (merchant_id) merchant_id, price, original_price, campaign_price
                        FROM seller_snapshots ss
                        WHERE ss.monitored_product_id = p.id
                        ORDER BY merchant_id, snapshot_date DESC
                    ) s ON true
                """.format(
                    platform_clause="AND platform = :platform" if platform else "",
                    brand_clause="AND brand = :brand" if brand else "",
                    active_clause="AND is_active = true" if active_only else "",
                    search_clause="AND (sku ILIKE :search OR barcode ILIKE :search OR product_name ILIKE :search OR seller_stock_code ILIKE :search)" if search else "",
                )),
                {
                    **({"platform": platform.lower()} if platform else {}),
                    **({"brand": brand} if brand else {}),
                    **({"search": f"%{search.lower()}%"} if search else {}),
                    "limit": limit,
                    "offset": offset,
                },
            ).fetchall(),
            "price-monitor/products",
        )

        if not combined_rows:
            response = {"products": [], "total": 0, "active_count": 0, "inactive_count": 0, "limit": limit, "offset": offset}
            log_endpoint_metric(
                logger,
                "price-monitor/products",
                latency_ms=(perf_counter() - start_time) * 1000,
                platform=platform or "all",
                total=0,
                limit=limit,
                offset=offset,
            )
            return response

        total_count = combined_rows[0][13]
        active_count = combined_rows[0][14] or 0
        inactive_count = total_count - active_count

        # Group rows by product (each product may have multiple seller rows from LEFT JOIN)
        from collections import OrderedDict
        product_map: Dict[str, dict] = OrderedDict()
        for r in combined_rows:
            pid = str(r[0])
            if pid not in product_map:
                product_map[pid] = {
                    "id": pid, "platform": r[1], "sku": r[2], "barcode": r[3],
                    "product_url": r[4], "product_name": r[5], "brand": r[6],
                    "seller_stock_code": r[7],
                    "threshold_price": float(r[8]) if r[8] else None,
                    "alert_campaign_price": float(r[9]) if r[9] else None,
                    "image_url": r[10], "is_active": r[11],
                    "last_fetched_at": r[12].isoformat() if r[12] else None,
                    "_snapshots": [],
                }
            if r[15] is not None:  # merchant_id from LEFT JOIN
                product_map[pid]["_snapshots"].append({
                    "price": r[16], "original_price": r[17], "campaign_price": r[18],
                })

        result = []
        for p in product_map.values():
            snaps = p.pop("_snapshots")
            p["seller_count"] = len(snaps)
            threshold = p["threshold_price"]
            campaign_threshold = p["alert_campaign_price"]
            price_alert_count = 0
            campaign_alert_count = 0
            for snap in snaps:
                s_price = _to_float(snap["price"])
                s_original = _to_float(snap["original_price"])
                s_campaign = _to_float(snap["campaign_price"])
                list_price = s_original if s_original is not None else s_price
                if p["platform"] == "trendyol":
                    if threshold is not None and list_price is not None and list_price < threshold:
                        price_alert_count += 1
                    if campaign_threshold is not None and s_original is not None and s_price is not None and s_price < campaign_threshold:
                        campaign_alert_count += 1
                else:
                    if threshold is not None and list_price is not None and list_price < threshold:
                        price_alert_count += 1
                    if campaign_threshold is not None and s_campaign is not None and s_campaign < campaign_threshold:
                        campaign_alert_count += 1
            p["has_price_alert"] = price_alert_count > 0
            p["price_alert_count"] = price_alert_count
            p["has_campaign_alert"] = campaign_alert_count > 0
            p["campaign_alert_count"] = campaign_alert_count
            result.append(p)
    else:
        # Alert filter path: need all products (can't paginate before checking alerts)
        products = _run_read_query_with_retry(db, query.all, "price-monitor/products")
        if not products:
            response = {"products": [], "total": 0, "active_count": 0, "inactive_count": 0, "limit": limit, "offset": offset}
            log_endpoint_metric(
                logger,
                "price-monitor/products",
                latency_ms=(perf_counter() - start_time) * 1000,
                platform=platform or "all",
                total=0,
                limit=limit,
                offset=offset,
            )
            return response
        product_ids = [p.id for p in products]
        snap_rows = _run_read_query_with_retry(
            db,
            lambda: db.execute(
                text("""
                    SELECT DISTINCT ON (monitored_product_id, merchant_id)
                           monitored_product_id, merchant_id, price, original_price, campaign_price
                    FROM seller_snapshots
                    WHERE monitored_product_id = ANY(:product_ids)
                    ORDER BY monitored_product_id, merchant_id, snapshot_date DESC
                """),
                {"product_ids": product_ids},
            ).fetchall(),
            "price-monitor/products",
        )
        snapshot_map: Dict[str, list] = {}
        for row in snap_rows:
            pid = str(row[0])
            snapshot_map.setdefault(pid, []).append({
                "price": row[2], "original_price": row[3], "campaign_price": row[4],
            })
        result = []
        for product in products:
            pid = str(product.id)
            snaps = snapshot_map.get(pid, [])
            threshold = float(product.threshold_price) if product.threshold_price else None
            campaign_threshold = float(product.alert_campaign_price) if product.alert_campaign_price else None
            price_alert_count = 0
            campaign_alert_count = 0
            for snap in snaps:
                s_price = _to_float(snap["price"])
                s_original = _to_float(snap["original_price"])
                s_campaign = _to_float(snap["campaign_price"])
                list_price = s_original if s_original is not None else s_price
                if product.platform == "trendyol":
                    if threshold is not None and list_price is not None and list_price < threshold:
                        price_alert_count += 1
                    if campaign_threshold is not None and s_original is not None and s_price is not None and s_price < campaign_threshold:
                        campaign_alert_count += 1
                else:
                    if threshold is not None and list_price is not None and list_price < threshold:
                        price_alert_count += 1
                    if campaign_threshold is not None and s_campaign is not None and s_campaign < campaign_threshold:
                        campaign_alert_count += 1
            has_price_alert = price_alert_count > 0
            has_campaign_alert = campaign_alert_count > 0
            if price_alert_only and not has_price_alert:
                continue
            if campaign_alert_only and not has_campaign_alert:
                continue
            result.append({
                "id": pid, "platform": product.platform, "sku": product.sku,
                "barcode": product.barcode, "product_url": product.product_url,
                "product_name": product.product_name, "brand": product.brand,
                "seller_stock_code": product.seller_stock_code,
                "threshold_price": float(product.threshold_price) if product.threshold_price else None,
                "alert_campaign_price": float(product.alert_campaign_price) if product.alert_campaign_price else None,
                "image_url": product.image_url, "is_active": product.is_active,
                "last_fetched_at": product.last_fetched_at.isoformat() if product.last_fetched_at else None,
                "seller_count": len(snaps),
                "has_price_alert": has_price_alert, "price_alert_count": price_alert_count,
                "has_campaign_alert": has_campaign_alert, "campaign_alert_count": campaign_alert_count,
            })
        total_count = len(result)
        active_count = sum(1 for item in result if item["is_active"])
        inactive_count = total_count - active_count
        result = result[offset:offset + limit]

    response = {
        "products": result,
        "total": total_count,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "limit": limit,
        "offset": offset
    }
    log_endpoint_metric(
        logger,
        "price-monitor/products",
        latency_ms=(perf_counter() - start_time) * 1000,
        platform=platform or "all",
        total=total_count,
        limit=limit,
        offset=offset,
    )
    return response


@router.get("/price-monitor/export")
async def export_price_monitor_data(
    platform: str = Query(..., description="Platform: hepsiburada veya trendyol"),
    active_filter: str = Query("all", description="Filtre: all, active, inactive"),
    db: Session = Depends(get_db)
):
    """SKU bazlı gruplandırılmış JSON olarak indir"""
    from fastapi.responses import StreamingResponse
    import json

    query = db.query(MonitoredProduct).filter(
        MonitoredProduct.platform == platform.lower()
    )

    if active_filter == "active":
        query = query.filter(MonitoredProduct.is_active == True)
    elif active_filter == "inactive":
        query = query.filter(MonitoredProduct.is_active == False)

    products = query.all()

    export_data = []

    for product in products:
        snapshots = db.query(SellerSnapshot).filter(
            SellerSnapshot.monitored_product_id == product.id
        ).order_by(desc(SellerSnapshot.snapshot_date)).all()

        sellers = []
        min_price_seller = None
        min_price_value = None
        seen_merchants = set()

        for s in snapshots:
            if s.merchant_id not in seen_merchants:
                seen_merchants.add(s.merchant_id)

                if platform.lower() == "hepsiburada":
                    merchant_url = f"https://www.hepsiburada.com/magaza/{s.merchant_url_postfix}" if s.merchant_url_postfix else ""
                elif platform.lower() == "trendyol":
                    merchant_url = f"https://www.trendyol.com{s.merchant_url_postfix}" if s.merchant_url_postfix else ""
                else:
                    merchant_url = ""

                seller_data = {
                    "merchant_name": s.merchant_name,
                    "merchant_id": s.merchant_id,
                    "merchant_url": merchant_url,
                    "merchant_rating": float(s.merchant_rating) if s.merchant_rating else None,
                    "merchant_city": s.merchant_city or "",
                    "price": float(s.price) if s.price else None,
                    "original_price": float(s.original_price) if s.original_price else None,
                    "minimum_price": float(s.minimum_price) if s.minimum_price else None,
                    "discount_rate": float(s.discount_rate) if s.discount_rate else None,
                    "stock_quantity": s.stock_quantity,
                    "buybox_order": s.buybox_order,
                    "free_shipping": s.free_shipping,
                    "fast_shipping": s.fast_shipping,
                    "delivery_info": s.delivery_info or "",
                    "campaign_info": s.campaign_info or "",
                    "snapshot_date": s.snapshot_date.isoformat() if s.snapshot_date else ""
                }
                sellers.append(seller_data)

                seller_price = seller_data["price"]
                if seller_price is not None and (min_price_value is None or seller_price < min_price_value):
                    min_price_value = seller_price
                    min_price_seller = {
                        "merchant_name": s.merchant_name,
                        "merchant_url": merchant_url,
                        "price": seller_price,
                        "buybox_order": s.buybox_order
                    }

        product_data = {
            "platform": product.platform,
            "sku": product.sku,
            "barcode": product.barcode or "",
            "product_name": product.product_name or "",
            "product_url": product.product_url or "",
            "is_active": product.is_active,
            "min_price": min_price_seller["price"] if min_price_seller else None,
            "min_price_seller": min_price_seller,
            "seller_count": len(sellers),
            "sellers": sellers
        }
        export_data.append(product_data)

    output = json.dumps(export_data, ensure_ascii=False, indent=2)
    filename = f"price_monitor_{platform}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    return StreamingResponse(
            iter([output]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@router.get("/price-monitor/brands")
async def get_monitored_product_brands(
    db: Session = Depends(get_db),
    platform: Optional[str] = None
):
    """Platform için marka listesini getir"""
    from sqlalchemy import distinct
    query = db.query(distinct(MonitoredProduct.brand)).filter(MonitoredProduct.brand.isnot(None))
    if platform:
        query = query.filter(MonitoredProduct.platform == platform.lower())
    brands = [b[0] for b in query.all() if b[0]]
    return {"brands": sorted(brands)}


@router.get("/price-monitor/products/{product_id}")
async def get_monitored_product_detail(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Tek bir ürün ve satıcılarını getir"""
    product = db.query(MonitoredProduct).filter(MonitoredProduct.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    threshold = float(product.threshold_price) if product.threshold_price else None
    campaign_threshold = float(product.alert_campaign_price) if product.alert_campaign_price else None

    latest_snapshots = db.query(SellerSnapshot).filter(
        SellerSnapshot.monitored_product_id == product.id
    ).order_by(desc(SellerSnapshot.snapshot_date)).all()

    seen_merchants = set()
    unique_sellers = []
    price_alert_count = 0
    campaign_alert_count = 0

    for s in latest_snapshots:
        if s.merchant_id not in seen_merchants:
            seen_merchants.add(s.merchant_id)
            if product.platform == "hepsiburada":
                merchant_url = f"https://www.hepsiburada.com/magaza/{s.merchant_url_postfix}" if s.merchant_url_postfix else None
            elif product.platform == "trendyol":
                merchant_url = f"https://www.trendyol.com{s.merchant_url_postfix}" if s.merchant_url_postfix else None
            else:
                merchant_url = None

            alerts = _calculate_price_alerts(product.platform, s, threshold, campaign_threshold)
            list_price = alerts["list_price"]
            selling_price = alerts["selling_price"]
            has_price_alert = alerts["has_price_alert"]
            has_campaign_alert = alerts["has_campaign_alert"]

            if has_price_alert:
                price_alert_count += 1
            if has_campaign_alert:
                campaign_alert_count += 1

            unique_sellers.append({
                "merchant_id": s.merchant_id,
                "merchant_name": s.merchant_name,
                "merchant_logo": s.merchant_logo,
                "merchant_url_postfix": s.merchant_url_postfix,
                "merchant_url": merchant_url,
                "merchant_rating": float(s.merchant_rating) if s.merchant_rating else None,
                "merchant_rating_count": s.merchant_rating_count,
                "merchant_city": s.merchant_city,
                "price": selling_price,  # Güncel satış fiyatı (kampanyalı olabilir)
                "list_price": list_price,  # Liste fiyatı (threshold ile karşılaştırılır)
                "original_price": alerts["original_price"],  # Raw original_price
                "minimum_price": float(s.minimum_price) if s.minimum_price else None,
                "discount_rate": s.discount_rate,
                "stock_quantity": s.stock_quantity,
                "buybox_order": s.buybox_order,
                "free_shipping": s.free_shipping,
                "fast_shipping": s.fast_shipping,
                "is_fulfilled_by_hb": s.is_fulfilled_by_hb,
                "campaigns": s.campaigns if s.campaigns else [],
                "campaign_price": alerts["campaign_price"],
                "snapshot_date": s.snapshot_date.isoformat(),
                "price_alert": has_price_alert,
                "campaign_alert": has_campaign_alert
            })

    return {
        "product": {
            "id": str(product.id),
            "platform": product.platform,
            "sku": product.sku,
            "barcode": product.barcode,
            "product_url": product.product_url,
            "product_name": product.product_name,
            "brand": product.brand,
            "seller_stock_code": product.seller_stock_code,
            "threshold_price": threshold,
            "alert_campaign_price": campaign_threshold,
            "image_url": product.image_url,
            "is_active": product.is_active,
            "last_fetched_at": product.last_fetched_at.isoformat() if product.last_fetched_at else None,
            "seller_count": len(unique_sellers),
            "has_price_alert": price_alert_count > 0,
            "price_alert_count": price_alert_count,
            "has_campaign_alert": campaign_alert_count > 0,
            "campaign_alert_count": campaign_alert_count
        },
        "sellers": unique_sellers
    }


@router.delete("/price-monitor/products/{product_id}")
async def delete_monitored_product(
    product_id: str,
    db: Session = Depends(get_db)
):
    """İzlenen ürünü sil"""
    product = db.query(MonitoredProduct).filter(MonitoredProduct.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    db.delete(product)
    db.commit()

    return {"success": True, "message": "Ürün silindi"}


@router.delete("/price-monitor/products/bulk/all")
async def delete_all_monitored_products(
    platform: str = Query(..., description="Platform: hepsiburada veya trendyol"),
    db: Session = Depends(get_db)
):
    """Belirli platformdaki tüm izlenen ürünleri sil"""
    products = db.query(MonitoredProduct).filter(MonitoredProduct.platform == platform).all()
    count = len(products)

    if count == 0:
        return {"success": True, "deleted_count": 0, "message": "Silinecek ürün bulunamadı"}

    for product in products:
        db.delete(product)
    db.commit()

    return {"success": True, "deleted_count": count, "message": f"{count} ürün silindi"}


@router.delete("/price-monitor/products/bulk/inactive")
async def delete_inactive_monitored_products(
    platform: str = Query(..., description="Platform: hepsiburada veya trendyol"),
    db: Session = Depends(get_db)
):
    """Belirli platformdaki inaktif ürünleri sil"""
    products = db.query(MonitoredProduct).filter(
        MonitoredProduct.platform == platform,
        MonitoredProduct.is_active == False
    ).all()
    count = len(products)

    if count == 0:
        return {"success": True, "deleted_count": 0, "message": "Silinecek inaktif ürün bulunamadı"}

    for product in products:
        db.delete(product)
    db.commit()

    return {"success": True, "deleted_count": count, "message": f"{count} inaktif ürün silindi"}


async def run_fetch_task(task_id: str, platform: str, product_ids: List[str] = None, fetch_type: str = "active"):
    """Arka planda satıcı fiyatlarını çek"""
    db = SessionLocal()
    try:
        task = db.query(PriceMonitorTask).filter(PriceMonitorTask.id == task_id).first()
        try:
            _require_scraper_api_or_503()
        except HTTPException as exc:
            if task:
                task.status = "failed"
                task.error_message = str(exc.detail)
                task.completed_at = datetime.utcnow()
                db.commit()
            return
        if task:
            if platform == "trendyol":
                await _get_trendyol_price_monitor_service().fetch_all_products(db, task, product_ids, platform, fetch_type)
            else:
                await _get_price_monitor_service().fetch_all_products(db, task, product_ids, platform, fetch_type)
    finally:
        db.close()


@router.post("/price-monitor/fetch")
async def start_fetch_task(
    platform: str = Query("hepsiburada", description="Platform: hepsiburada veya trendyol"),
    fetch_type: str = Query("active", description="Fetch type: active, last_inactive, inactive"),
    db: Session = Depends(get_db),
    product_ids: Optional[List[str]] = None
):
    """Belirli platform için satıcı fiyatlarını çekmeye başla

    fetch_type:
    - active: Aktif ürünleri çek (varsayılan)
    - last_inactive: Son fetch'te inactive olan ürünleri tekrar dene
    - inactive: Tüm inactive ürünleri çek
    """
    _require_scraper_api_or_503()
    executor = settings.price_monitor_executor()
    if executor != "local":
        _require_queue_or_503()

    task = PriceMonitorTask(platform=platform, status="pending", fetch_type=fetch_type)
    db.add(task)
    db.commit()
    db.refresh(task)

    if executor == "local":
        asyncio.create_task(run_fetch_task(str(task.id), platform, product_ids, fetch_type))
    else:
        try:
            from app.tasks import send_price_monitor_task
            send_price_monitor_task(str(task.id), platform, fetch_type, product_ids)
        except Exception as exc:
            task.status = "failed"
            task.error_message = f"Celery enqueue failed: {exc}"
            task.completed_at = datetime.utcnow()
            db.commit()
            raise HTTPException(status_code=503, detail="Fetch queue unavailable. Check Redis/Celery worker.")

    return {
        "task_id": str(task.id),
        "platform": platform,
        "fetch_type": fetch_type,
        "executor": executor,
        "status": "started",
        "message": f"{platform.capitalize()} için {fetch_type} ürünler çekme işlemi başlatıldı"
    }


@router.post("/price-monitor/fetch/{task_id}/stop")
async def stop_fetch_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Fiyat çekme görevini durdur"""
    task = db.query(PriceMonitorTask).filter(PriceMonitorTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")

    if task.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Görev zaten tamamlanmış veya durdurulmuş")

    task.stop_requested = True
    db.commit()

    return {
        "success": True,
        "message": "Durdurma isteği gönderildi, mevcut ürün tamamlandıktan sonra duracak"
    }


@router.get("/price-monitor/fetch/{task_id}")
async def get_fetch_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Fiyat çekme görevinin durumunu getir"""
    task = db.query(PriceMonitorTask).filter(PriceMonitorTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")

    return {
        "id": str(task.id),
        "status": task.status,
        "total_products": task.total_products,
        "completed_products": task.completed_products,
        "failed_products": task.failed_products,
        "fetch_type": task.fetch_type,
        "executor": settings.price_monitor_executor(),
        "last_inactive_count": len(task.last_inactive_skus) if task.last_inactive_skus else 0,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    }


@router.get("/price-monitor/last-inactive")
async def get_last_inactive_skus(
    platform: str = Query("hepsiburada"),
    db: Session = Depends(get_db)
):
    """Son tamamlanan fetch görevinde inactive olan SKU'ları getir"""
    start_time = perf_counter()

    def _query_last_inactive() -> Dict[str, Any]:
        last_task = db.query(PriceMonitorTask).filter(
            PriceMonitorTask.platform == platform,
            PriceMonitorTask.status == "completed"
        ).order_by(PriceMonitorTask.completed_at.desc()).first()

        if not last_task:
            return {"skus": [], "count": 0, "task_id": None}

        skus = last_task.last_inactive_skus or []

        products = []
        if skus:
            product_records = db.query(MonitoredProduct).filter(
                MonitoredProduct.sku.in_(skus),
                MonitoredProduct.platform == platform
            ).all()

            products = [
                {
                    "id": str(p.id),
                    "sku": p.sku,
                    "product_name": p.product_name,
                    "brand": p.brand,
                    "is_active": p.is_active
                }
                for p in product_records
            ]

        return {
            "skus": skus,
            "count": len(skus),
            "products": products,
            "task_id": str(last_task.id),
            "completed_at": last_task.completed_at.isoformat() if last_task.completed_at else None
        }

    response = _run_read_query_with_retry(db, _query_last_inactive, "price-monitor/last-inactive")
    log_endpoint_metric(
        logger,
        "price-monitor/last-inactive",
        latency_ms=(perf_counter() - start_time) * 1000,
        platform=platform,
        count=response.get("count", 0),
    )
    return response


@router.post("/price-monitor/fetch-single/{product_id}")
async def fetch_single_product(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Tek bir ürün için satıcı fiyatlarını çek - platform otomatik belirlenir"""
    _require_scraper_api_or_503()

    product = db.query(MonitoredProduct).filter(MonitoredProduct.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    if product.platform == "trendyol":
        success = await _get_trendyol_price_monitor_service().fetch_and_save_product(db, product)
    else:
        success = await _get_price_monitor_service().fetch_and_save_product(db, product)

    if success:
        return {"success": True, "message": f"{product.sku} için satıcı verileri güncellendi", "platform": product.platform}
    else:
        raise HTTPException(status_code=500, detail="Satıcı verileri çekilemedi")
