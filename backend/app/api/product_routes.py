from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional

from app.db.database import get_db
from app.db.models import Product, ProductSnapshot, ProductSeller, ProductReview
from app.core.security import require_mutating_api_key

from app.api._shared import (
    AnalysisRequest,
    ProductResponse,
    ProductDetailResponse,
    SellerResponse,
    ReviewResponse,
    SnapshotResponse,
    _get_llm_service,
)

router = APIRouter(dependencies=[Depends(require_mutating_api_key)])

@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    keyword: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if keyword:
        query = query.filter(Product.name.ilike(f"%{keyword}%"))
    if platform:
        query = query.filter(Product.platform == platform)

    products = query.order_by(desc(Product.created_at)).limit(limit).all()

    result = []
    for p in products:
        latest = db.query(ProductSnapshot).filter(
            ProductSnapshot.product_id == p.id
        ).order_by(desc(ProductSnapshot.snapshot_date)).first()

        result.append(ProductResponse(
            id=str(p.id),
            platform=p.platform,
            external_id=p.external_id,
            sku=p.sku,
            barcode=p.barcode,
            name=p.name,
            url=p.url,
            brand=p.brand,
            seller_name=p.seller_name,
            seller_rating=p.seller_rating,
            category_path=p.category_path,
            category_hierarchy=p.category_hierarchy,
            image_url=p.image_url,
            description=p.description[:500] if p.description else None,
            origin_country=p.origin_country,
            latest_price=float(latest.price) if latest and latest.price else None,
            discounted_price=float(latest.discounted_price) if latest and latest.discounted_price else None,
            discount_percentage=latest.discount_percentage if latest else None,
            latest_rating=latest.rating if latest else None,
            reviews_count=latest.reviews_count if latest else None,
            stock_count=latest.stock_count if latest else None,
            in_stock=latest.in_stock if latest else None,
            is_sponsored=latest.is_sponsored if latest else None,
            coupons=latest.coupons if latest else None,
            campaigns=latest.campaigns if latest else None
        ))

    return result

@router.get("/products/{product_id}", response_model=ProductDetailResponse)
async def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    latest = db.query(ProductSnapshot).filter(
        ProductSnapshot.product_id == product.id
    ).order_by(desc(ProductSnapshot.snapshot_date)).first()

    other_sellers = db.query(ProductSeller).filter(
        ProductSeller.product_id == product.id
    ).order_by(desc(ProductSeller.snapshot_date)).limit(10).all()

    reviews = db.query(ProductReview).filter(
        ProductReview.product_id == product.id
    ).limit(20).all()

    return ProductDetailResponse(
        id=str(product.id),
        platform=product.platform,
        external_id=product.external_id,
        sku=product.sku,
        barcode=product.barcode,
        name=product.name,
        url=product.url,
        brand=product.brand,
        seller_name=product.seller_name,
        seller_rating=product.seller_rating,
        category_path=product.category_path,
        category_hierarchy=product.category_hierarchy,
        image_url=product.image_url,
        description=product.description,
        origin_country=product.origin_country,
        latest_price=float(latest.price) if latest and latest.price else None,
        discounted_price=float(latest.discounted_price) if latest and latest.discounted_price else None,
        discount_percentage=latest.discount_percentage if latest else None,
        latest_rating=latest.rating if latest else None,
        reviews_count=latest.reviews_count if latest else None,
        stock_count=latest.stock_count if latest else None,
        in_stock=latest.in_stock if latest else None,
        is_sponsored=latest.is_sponsored if latest else None,
        coupons=latest.coupons if latest else None,
        campaigns=latest.campaigns if latest else None,
        other_sellers=[
            SellerResponse(
                seller_name=s.seller_name,
                seller_rating=s.seller_rating,
                price=float(s.price) if s.price else None,
                is_authorized=s.is_authorized
            ) for s in other_sellers
        ],
        reviews=[
            ReviewResponse(
                author=r.author,
                rating=r.rating,
                review_text=r.review_text,
                review_date=r.review_date.isoformat() if r.review_date else None,
                seller_name=r.seller_name
            ) for r in reviews
        ]
    )

@router.get("/products/{product_id}/snapshots", response_model=List[SnapshotResponse])
async def get_product_snapshots(
    product_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    start_date = date.today() - timedelta(days=days)
    snapshots = db.query(ProductSnapshot).filter(
        ProductSnapshot.product_id == product_id,
        ProductSnapshot.snapshot_date >= start_date
    ).order_by(ProductSnapshot.snapshot_date).all()

    return [
        SnapshotResponse(
            id=s.id,
            price=float(s.price) if s.price else None,
            discounted_price=float(s.discounted_price) if s.discounted_price else None,
            discount_percentage=s.discount_percentage,
            rating=s.rating,
            reviews_count=s.reviews_count,
            stock_count=s.stock_count,
            in_stock=s.in_stock,
            is_sponsored=s.is_sponsored,
            coupons=s.coupons,
            campaigns=s.campaigns,
            snapshot_date=s.snapshot_date.isoformat()
        ) for s in snapshots
    ]

@router.post("/analyze")
async def analyze_products(request: AnalysisRequest, db: Session = Depends(get_db)):
    products_data = []
    for pid in request.product_ids:
        product = db.query(Product).filter(Product.id == pid).first()
        if product:
            snapshots = db.query(ProductSnapshot).filter(
                ProductSnapshot.product_id == product.id
            ).order_by(desc(ProductSnapshot.snapshot_date)).limit(30).all()

            products_data.append({
                "name": product.name,
                "brand": product.brand,
                "platform": product.platform,
                "seller": product.seller_name,
                "category": product.category_hierarchy,
                "description": product.description[:1000] if product.description else None,
                "snapshots": [
                    {
                        "date": s.snapshot_date.isoformat(),
                        "price": float(s.price) if s.price else None,
                        "discounted_price": float(s.discounted_price) if s.discounted_price else None,
                        "rating": s.rating,
                        "reviews": s.reviews_count,
                        "stock": s.stock_count,
                        "sponsored": s.is_sponsored,
                        "coupons": s.coupons,
                        "campaigns": s.campaigns
                    } for s in snapshots
                ]
            })

    llm = _get_llm_service()
    analysis = await llm.analyze_products(products_data, request.question)
    return {"analysis": analysis}
