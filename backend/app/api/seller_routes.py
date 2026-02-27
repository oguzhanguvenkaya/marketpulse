from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
from time import perf_counter

from app.db.database import get_db
from app.db.models import MonitoredProduct, User
from app.core.config import settings
from app.core.logger import api_logger as logger, log_endpoint_metric
from app.core.auth import get_current_user

from app.api._shared import (
    _to_float,
    _resolve_product_url,
    _is_valid_http_url,
    _run_read_query_with_retry,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _compute_seller_pricing(
    platform: str,
    threshold: Optional[float],
    campaign_threshold: Optional[float],
    current_price: Optional[float],
    original_price: Optional[float],
    campaign_price_value: Optional[float],
) -> Dict[str, Any]:
    if platform == "trendyol":
        list_price = original_price if original_price is not None else current_price
        campaign_price = current_price
        has_price_alert = threshold is not None and list_price is not None and list_price < threshold
        if original_price is not None and current_price is not None:
            has_campaign_alert = campaign_threshold is not None and current_price < campaign_threshold
            campaign_difference = round(original_price - current_price, 2)
        else:
            has_campaign_alert = False
            campaign_difference = None
    else:
        list_price = original_price if original_price is not None else current_price
        campaign_price = campaign_price_value
        has_price_alert = threshold is not None and list_price is not None and list_price < threshold
        has_campaign_alert = (
            campaign_threshold is not None
            and campaign_price_value is not None
            and campaign_price_value < campaign_threshold
        )
        campaign_difference = (
            round(campaign_threshold - campaign_price_value, 2)
            if campaign_threshold is not None and campaign_price_value is not None
            else None
        )

    return {
        "list_price": list_price,
        "campaign_price": campaign_price,
        "has_price_alert": has_price_alert,
        "has_campaign_alert": has_campaign_alert,
        "campaign_difference": campaign_difference,
    }


def _build_seller_products(
    db: Session,
    merchant_id: str,
    platform: str,
    price_alert_only: bool,
    campaign_alert_only: bool,
    user_id: str = None,
) -> Dict[str, Any]:
    rows = db.execute(
        text(
            """
            WITH latest AS (
                SELECT DISTINCT ON (ss.monitored_product_id)
                    ss.monitored_product_id,
                    ss.merchant_name,
                    ss.price,
                    ss.original_price,
                    ss.campaign_price,
                    ss.campaigns,
                    ss.snapshot_date
                FROM seller_snapshots ss
                JOIN monitored_products mp ON mp.id = ss.monitored_product_id
                WHERE mp.platform = :platform
                  AND mp.is_active = true
                  AND ss.merchant_id = :merchant_id
                  AND (mp.user_id = :user_id OR mp.user_id IS NULL)
                ORDER BY ss.monitored_product_id, ss.snapshot_date DESC
            )
            SELECT
                mp.id AS product_id,
                mp.sku,
                mp.barcode,
                mp.product_name,
                mp.product_url,
                mp.brand,
                mp.seller_stock_code,
                mp.image_url,
                mp.threshold_price,
                mp.alert_campaign_price,
                latest.merchant_name,
                latest.price,
                latest.original_price,
                latest.campaign_price,
                latest.campaigns,
                latest.snapshot_date
            FROM latest
            JOIN monitored_products mp ON mp.id = latest.monitored_product_id
            ORDER BY mp.created_at DESC
            """
        ),
        {"platform": platform.lower(), "merchant_id": merchant_id, "user_id": str(user_id) if user_id else None},
    ).mappings().all()

    products = []
    merchant_name = rows[0]["merchant_name"] if rows else ""

    for row in rows:
        threshold = float(row["threshold_price"]) if row["threshold_price"] is not None else None
        campaign_threshold = float(row["alert_campaign_price"]) if row["alert_campaign_price"] is not None else None
        current_price = float(row["price"]) if row["price"] is not None else None
        original_price = float(row["original_price"]) if row["original_price"] is not None else None
        campaign_price_value = float(row["campaign_price"]) if row["campaign_price"] is not None else None

        pricing = _compute_seller_pricing(
            platform=platform.lower(),
            threshold=threshold,
            campaign_threshold=campaign_threshold,
            current_price=current_price,
            original_price=original_price,
            campaign_price_value=campaign_price_value,
        )

        has_price_alert = pricing["has_price_alert"]
        has_campaign_alert = pricing["has_campaign_alert"]
        if price_alert_only and not has_price_alert:
            continue
        if campaign_alert_only and not has_campaign_alert:
            continue

        raw_product_url = row["product_url"]
        resolved_product_url = _resolve_product_url(platform, row["sku"], raw_product_url)
        had_valid_product_url = _is_valid_http_url(raw_product_url)

        seller_url = resolved_product_url
        if platform.lower() == "hepsiburada" and merchant_id and had_valid_product_url and resolved_product_url:
            separator = "&" if "?" in resolved_product_url else "?"
            seller_url = f"{resolved_product_url}{separator}magaza={merchant_id}"

        campaigns = row["campaigns"] if isinstance(row["campaigns"], list) else []
        list_price = pricing["list_price"]
        price_difference = round(threshold - list_price, 2) if threshold is not None and list_price is not None else None

        products.append(
            {
                "product_id": str(row["product_id"]),
                "sku": row["sku"],
                "barcode": row["barcode"],
                "product_name": row["product_name"],
                "product_url": resolved_product_url,
                "seller_url": seller_url,
                "brand": row["brand"],
                "seller_stock_code": row["seller_stock_code"],
                "image_url": row["image_url"],
                "threshold_price": threshold,
                "seller_price": list_price,
                "original_price": original_price,
                "campaign_price": pricing["campaign_price"],
                "alert_campaign_price": campaign_threshold,
                "campaigns": campaigns,
                "price_alert": has_price_alert,
                "campaign_alert": has_campaign_alert,
                "price_difference": price_difference,
                "campaign_difference": pricing["campaign_difference"],
                "snapshot_date": row["snapshot_date"].isoformat() if row["snapshot_date"] else None,
            }
        )

    products.sort(key=lambda item: (not item["price_alert"], not item["campaign_alert"], item["product_name"] or ""))

    return {
        "merchant_name": merchant_name,
        "products": products,
        "price_alert_count": sum(1 for item in products if item["price_alert"]),
        "campaign_alert_count": sum(1 for item in products if item["campaign_alert"]),
    }


@router.get("/sellers")
async def get_sellers(
    platform: str = Query("hepsiburada", description="Platform: hepsiburada veya trendyol"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tüm satıcıları listele - her satıcının ürün sayısı, price alert ve campaign alert sayısı ile"""
    start_time = perf_counter()
    is_trendyol = platform.lower() == "trendyol"

    def _query_sellers() -> Dict[str, Any]:
        rows = db.execute(
            text(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (ss.merchant_id, ss.monitored_product_id)
                        ss.merchant_id,
                        ss.monitored_product_id,
                        ss.merchant_name,
                        ss.merchant_logo,
                        ss.merchant_url_postfix,
                        ss.merchant_rating,
                        ss.price,
                        ss.original_price,
                        ss.campaign_price
                    FROM seller_snapshots ss
                    JOIN monitored_products mp ON mp.id = ss.monitored_product_id
                    WHERE mp.platform = :platform
                      AND mp.is_active = true
                      AND (mp.user_id = :user_id OR mp.user_id IS NULL)
                    ORDER BY ss.merchant_id, ss.monitored_product_id, ss.snapshot_date DESC
                ),
                aggregated AS (
                    SELECT
                        l.merchant_id,
                        MAX(l.merchant_name) AS merchant_name,
                        MAX(l.merchant_logo) AS merchant_logo,
                        MAX(l.merchant_url_postfix) AS merchant_url_postfix,
                        MAX(l.merchant_rating) AS merchant_rating,
                        COUNT(*)::int AS product_count,
                        SUM(
                            CASE
                                WHEN mp.threshold_price IS NOT NULL
                                     AND COALESCE(l.original_price, l.price) IS NOT NULL
                                     AND COALESCE(l.original_price, l.price) < mp.threshold_price
                                THEN 1
                                ELSE 0
                            END
                        )::int AS price_alert_count,
                        SUM(
                            CASE
                                WHEN :is_trendyol
                                    THEN CASE
                                        WHEN mp.alert_campaign_price IS NOT NULL
                                             AND l.original_price IS NOT NULL
                                             AND l.price IS NOT NULL
                                             AND l.price < mp.alert_campaign_price
                                        THEN 1
                                        ELSE 0
                                    END
                                ELSE CASE
                                    WHEN mp.alert_campaign_price IS NOT NULL
                                         AND l.campaign_price IS NOT NULL
                                         AND l.campaign_price < mp.alert_campaign_price
                                    THEN 1
                                    ELSE 0
                                END
                            END
                        )::int AS campaign_alert_count
                    FROM latest l
                    JOIN monitored_products mp ON mp.id = l.monitored_product_id
                    GROUP BY l.merchant_id
                ),
                counted AS (
                    SELECT
                        a.*,
                        COUNT(*) OVER()::int AS total_count
                    FROM aggregated a
                )
                SELECT
                    merchant_id,
                    merchant_name,
                    merchant_logo,
                    merchant_url_postfix,
                    merchant_rating,
                    product_count,
                    price_alert_count,
                    campaign_alert_count,
                    total_count
                FROM counted
                ORDER BY (price_alert_count + campaign_alert_count) DESC, merchant_name ASC
                LIMIT :limit OFFSET :offset
                """
            ),
            {
                "platform": platform.lower(),
                "is_trendyol": is_trendyol,
                "limit": limit,
                "offset": offset,
                "user_id": str(user.id),
            },
        ).mappings().all()

        if not rows:
            total_count = db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT ss.merchant_id)::int
                    FROM seller_snapshots ss
                    JOIN monitored_products mp ON mp.id = ss.monitored_product_id
                    WHERE mp.platform = :platform
                      AND mp.is_active = true
                      AND (mp.user_id = :user_id OR mp.user_id IS NULL)
                    """
                ),
                {"platform": platform.lower(), "user_id": str(user.id)},
            ).scalar() or 0
            return {"sellers": [], "total": int(total_count), "limit": limit, "offset": offset}

        sellers = []
        for row in rows:
            sellers.append(
                {
                    "merchant_id": row["merchant_id"],
                    "merchant_name": row["merchant_name"],
                    "merchant_logo": row["merchant_logo"],
                    "merchant_url_postfix": row["merchant_url_postfix"],
                    "merchant_rating": float(row["merchant_rating"]) if row["merchant_rating"] is not None else None,
                    "product_count": int(row["product_count"] or 0),
                    "price_alert_count": int(row["price_alert_count"] or 0),
                    "campaign_alert_count": int(row["campaign_alert_count"] or 0),
                }
            )

        return {
            "sellers": sellers,
            "total": int(rows[0]["total_count"] or 0),
            "limit": limit,
            "offset": offset,
        }

    response = _run_read_query_with_retry(db, _query_sellers, "sellers")
    log_endpoint_metric(
        logger,
        "sellers",
        latency_ms=(perf_counter() - start_time) * 1000,
        platform=platform,
        total=response.get("total", 0),
        limit=limit,
        offset=offset,
    )
    return response


@router.get("/sellers/{merchant_id}/products")
async def get_seller_products(
    merchant_id: str,
    platform: str = Query("hepsiburada", description="Platform"),
    price_alert_only: bool = Query(False, description="Sadece price alert olan ürünleri göster"),
    campaign_alert_only: bool = Query(False, description="Sadece campaign alert olan ürünleri göster"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Satıcının sattığı ürünleri listele - price alert ve campaign alert filtresi ile"""
    start_time = perf_counter()

    def _query_seller_products() -> Dict[str, Any]:
        payload = _build_seller_products(
            db=db,
            merchant_id=merchant_id,
            platform=platform,
            price_alert_only=price_alert_only,
            campaign_alert_only=campaign_alert_only,
            user_id=user.id,
        )
        total = len(payload["products"])
        paged_products = payload["products"][offset: offset + limit]
        return {
            "products": paged_products,
            "total": total,
            "merchant_name": payload["merchant_name"],
            "price_alert_count": payload["price_alert_count"],
            "campaign_alert_count": payload["campaign_alert_count"],
            "limit": limit,
            "offset": offset,
        }

    response = _run_read_query_with_retry(db, _query_seller_products, "sellers/products")
    log_endpoint_metric(
        logger,
        "sellers/products",
        latency_ms=(perf_counter() - start_time) * 1000,
        platform=platform,
        merchant_id=merchant_id,
        total=response.get("total", 0),
        limit=limit,
        offset=offset,
    )
    return response


@router.get("/sellers/{merchant_id}/export")
async def export_seller_products(
    merchant_id: str,
    platform: str = Query("hepsiburada", description="Platform"),
    price_alert_only: bool = Query(False, description="Sadece price alert olan ürünleri indir"),
    campaign_alert_only: bool = Query(False, description="Sadece campaign alert olan ürünleri indir"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Satıcının ürünlerini CSV olarak indir - campaign alert dahil"""
    from fastapi.responses import StreamingResponse
    import csv
    import io

    payload = _run_read_query_with_retry(
        db,
        lambda: _build_seller_products(
            db=db,
            merchant_id=merchant_id,
            platform=platform,
            price_alert_only=price_alert_only,
            campaign_alert_only=campaign_alert_only,
            user_id=user.id,
        ),
        "sellers/export",
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    writer.writerow([
        'SKU', 'Barcode', 'Product Name', 'Brand', 'Stock Code',
        'Product URL', 'Threshold Price', 'Seller Price',
        'Price Difference', 'Price Alert', 'Campaign Threshold', 'Campaign Price',
        'Campaign Difference', 'Campaign Alert', 'Campaigns', 'Snapshot Date'
    ])

    def _csv_value(value: Any) -> Any:
        return value if value is not None else ''

    merchant_name = payload["merchant_name"] or ""
    for product in payload["products"]:
        campaigns = product.get("campaigns") if isinstance(product.get("campaigns"), list) else []
        campaigns_str = ", ".join(campaigns) if campaigns else ""

        writer.writerow([
            _csv_value(product.get("sku")),
            _csv_value(product.get("barcode")),
            _csv_value(product.get("product_name")),
            _csv_value(product.get("brand")),
            _csv_value(product.get("seller_stock_code")),
            _csv_value(product.get("product_url")),
            _csv_value(product.get("threshold_price")),
            _csv_value(product.get("seller_price")),
            _csv_value(product.get("price_difference")),
            'YES' if product.get("price_alert") else 'NO',
            _csv_value(product.get("alert_campaign_price")),
            _csv_value(product.get("campaign_price")),
            _csv_value(product.get("campaign_difference")),
            'YES' if product.get("campaign_alert") else 'NO',
            campaigns_str,
            _csv_value(product.get("snapshot_date")),
        ])

    output.seek(0)

    tr_to_ascii = str.maketrans('İıĞğÜüŞşÖöÇç', 'IiGgUuSsOoCc')
    safe_merchant_name = merchant_name.translate(tr_to_ascii)
    safe_merchant_name = "".join(c for c in safe_merchant_name if c.isascii() and (c.isalnum() or c in (' ', '-', '_'))).strip()
    safe_merchant_name = safe_merchant_name or "seller"
    filename = f"{safe_merchant_name}_products.csv"

    # UTF-8 BOM ekle - Excel'in UTF-8 encoding'i tanıması için
    bom = '\ufeff'
    csv_content = bom + output.getvalue()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
