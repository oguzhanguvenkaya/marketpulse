from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, distinct
from typing import List, Optional

from app.db.database import get_db, SessionLocal
from app.db.models import Product, ProductSnapshot, ProductSeller, ProductReview, SearchTask, SponsoredBrandAd, SearchSponsoredProduct, User
from app.core.logger import api_logger as logger
from app.core.auth import get_current_user

from app.api._shared import (
    SearchRequest,
    SearchTaskResponse,
    _get_scraping_service,
    _parse_review_date,
)

router = APIRouter(dependencies=[Depends(get_current_user)])

async def run_scraping_background(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
        if not task:
            return

        task.status = "running"
        db.commit()

        scraper = _get_scraping_service()
        browser_initialized = False
        try:
            if task.platform == "hepsiburada":
                await scraper.init_browser()
                browser_initialized = True
                search_result = await scraper.scrape_hepsiburada_search(task.keyword, max_products=8)
                products_data = search_result.get('products', [])
                sponsored_brands = search_result.get('sponsored_brands', [])
                sponsored_products = search_result.get('sponsored_products', [])
            else:
                products_data = []
                sponsored_brands = []
                sponsored_products = []

            today = date.today()
            saved_count = 0

            for brand_ad in sponsored_brands:
                existing_ad = db.query(SponsoredBrandAd).filter(
                    SponsoredBrandAd.search_task_id == task.id,
                    SponsoredBrandAd.seller_name == brand_ad['seller_name']
                ).first()

                if not existing_ad:
                    new_ad = SponsoredBrandAd(
                        search_task_id=task.id,
                        seller_name=brand_ad['seller_name'],
                        seller_id=brand_ad.get('seller_id'),
                        position=brand_ad.get('position'),
                        products=brand_ad.get('products', []),
                        snapshot_date=today
                    )
                    db.add(new_ad)

            if sponsored_brands:
                logger.info(f"Saved {len(sponsored_brands)} brand ads to database")

            for sp in sponsored_products:
                product_url = sp.get('url') or sp.get('product_url', '')
                existing_sp = db.query(SearchSponsoredProduct).filter(
                    SearchSponsoredProduct.search_task_id == task.id,
                    SearchSponsoredProduct.product_url == product_url
                ).first()

                if not existing_sp and product_url:
                    new_sp = SearchSponsoredProduct(
                        search_task_id=task.id,
                        order_index=sp.get('order_index', 0),
                        product_url=product_url,
                        product_name=sp.get('name') or sp.get('product_name'),
                        seller_name=sp.get('seller_name'),
                        price=sp.get('price'),
                        discounted_price=sp.get('discounted_price'),
                        image_url=sp.get('image_url'),
                        payload=sp.get('payload'),
                        snapshot_date=today
                    )
                    db.add(new_sp)

            if sponsored_products:
                task.total_sponsored_products = len(sponsored_products)
                logger.info(f"Saved {len(sponsored_products)} sponsored products to database")

            for p_data in products_data:
                existing = db.query(Product).filter(
                    Product.platform == p_data["platform"],
                    Product.external_id == p_data["external_id"]
                ).first()

                if existing:
                    product = existing
                    product.name = p_data.get("name", product.name)
                    product.brand = p_data.get("brand", product.brand)
                    product.seller_name = p_data.get("seller_name", product.seller_name)
                    product.seller_rating = p_data.get("seller_rating", product.seller_rating)
                    product.category_path = p_data.get("category_path", product.category_path)
                    product.category_hierarchy = p_data.get("category_hierarchy", product.category_hierarchy)
                    product.image_url = p_data.get("image_url", product.image_url)
                    product.description = p_data.get("description", product.description)
                    product.sku = p_data.get("sku", product.sku)
                    product.barcode = p_data.get("barcode", product.barcode)
                    product.origin_country = p_data.get("origin_country", product.origin_country)
                    product.updated_at = datetime.utcnow()
                else:
                    product = Product(
                        platform=p_data["platform"],
                        external_id=p_data["external_id"],
                        name=p_data.get("name", "Unknown"),
                        url=p_data["url"],
                        brand=p_data.get("brand"),
                        seller_name=p_data.get("seller_name"),
                        seller_rating=p_data.get("seller_rating"),
                        category_path=p_data.get("category_path"),
                        category_hierarchy=p_data.get("category_hierarchy"),
                        image_url=p_data.get("image_url"),
                        description=p_data.get("description"),
                        sku=p_data.get("sku"),
                        barcode=p_data.get("barcode"),
                        origin_country=p_data.get("origin_country")
                    )
                    db.add(product)
                    db.flush()

                existing_snapshot = db.query(ProductSnapshot).filter(
                    ProductSnapshot.product_id == product.id,
                    ProductSnapshot.snapshot_date == today
                ).first()

                if existing_snapshot:
                    if p_data.get("price") is not None:
                        existing_snapshot.price = p_data.get("price")
                    if p_data.get("discounted_price") is not None:
                        existing_snapshot.discounted_price = p_data.get("discounted_price")
                    if p_data.get("discount_percentage") is not None:
                        existing_snapshot.discount_percentage = p_data.get("discount_percentage")
                    if p_data.get("rating") is not None:
                        existing_snapshot.rating = p_data.get("rating")
                    if p_data.get("reviews_count") is not None:
                        existing_snapshot.reviews_count = p_data.get("reviews_count")
                    if p_data.get("stock_count") is not None:
                        existing_snapshot.stock_count = p_data.get("stock_count")
                    if p_data.get("in_stock") is not None:
                        existing_snapshot.in_stock = p_data.get("in_stock")
                    if p_data.get("is_sponsored"):
                        existing_snapshot.is_sponsored = True
                    if p_data.get("coupons"):
                        existing_snapshot.coupons = p_data.get("coupons")
                    if p_data.get("campaigns"):
                        existing_snapshot.campaigns = p_data.get("campaigns")
                else:
                    snapshot = ProductSnapshot(
                        product_id=product.id,
                        price=p_data.get("price"),
                        discounted_price=p_data.get("discounted_price"),
                        discount_percentage=p_data.get("discount_percentage"),
                        rating=p_data.get("rating"),
                        reviews_count=p_data.get("reviews_count", 0),
                        stock_count=p_data.get("stock_count"),
                        in_stock=p_data.get("in_stock", True),
                        is_sponsored=p_data.get("is_sponsored", False),
                        coupons=p_data.get("coupons", []),
                        campaigns=p_data.get("campaigns", []),
                        snapshot_date=today
                    )
                    db.add(snapshot)

                db.query(ProductSeller).filter(
                    ProductSeller.product_id == product.id,
                    ProductSeller.snapshot_date == today
                ).delete()

                for seller in p_data.get("other_sellers", []):
                    ps = ProductSeller(
                        product_id=product.id,
                        seller_name=seller.get("seller_name", "Unknown"),
                        seller_rating=seller.get("seller_rating"),
                        price=seller.get("price"),
                        is_authorized=seller.get("is_authorized", False),
                        shipping_info=seller.get("shipping_info"),
                        snapshot_date=today
                    )
                    db.add(ps)

                existing_reviews = db.query(ProductReview).filter(
                    ProductReview.product_id == product.id
                ).count()

                if existing_reviews == 0:
                    for review in p_data.get("reviews", [])[:20]:
                        pr = ProductReview(
                            product_id=product.id,
                            author=review.get("author"),
                            rating=review.get("rating"),
                            review_text=review.get("review_text"),
                            review_date=_parse_review_date(review.get("review_date")),
                            seller_name=review.get("seller_name")
                        )
                        db.add(pr)

                saved_count += 1

            db.commit()

            task.status = "completed"
            task.total_products = saved_count
            task.completed_at = datetime.utcnow()
            db.commit()
        finally:
            if browser_initialized:
                await scraper.close_browser()
    except Exception as e:
        logger.error(f"Search task {task_id} failed: {e}")
        task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.error_message = str(e)
            db.commit()
    finally:
        db.close()

@router.post("/search", response_model=SearchTaskResponse)
async def create_search_task(request: SearchRequest, background_tasks: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = SearchTask(
        keyword=request.keyword,
        platform=request.platform,
        status="pending",
        user_id=user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(run_scraping_background, str(task.id))

    return SearchTaskResponse(
        id=str(task.id),
        keyword=task.keyword,
        platform=task.platform,
        status=task.status,
        total_products=task.total_products,
        created_at=task.created_at.isoformat()
    )

@router.get("/search/{task_id}", response_model=SearchTaskResponse)
async def get_search_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return SearchTaskResponse(
        id=str(task.id),
        keyword=task.keyword,
        platform=task.platform,
        status=task.status,
        total_products=task.total_products,
        created_at=task.created_at.isoformat()
    )

@router.get("/tasks", response_model=List[SearchTaskResponse])
async def list_tasks(
    limit: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tasks = db.query(SearchTask).filter(SearchTask.user_id == user.id).order_by(desc(SearchTask.created_at)).limit(limit).all()
    return [
        SearchTaskResponse(
            id=str(t.id),
            keyword=t.keyword,
            platform=t.platform,
            status=t.status,
            total_products=t.total_products,
            created_at=t.created_at.isoformat()
        ) for t in tasks
    ]

@router.get("/search/{task_id}/sponsored-brands")
async def get_sponsored_brands(task_id: str, db: Session = Depends(get_db)):
    """Get brand ads (marka reklamları) for a search task"""
    task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    brand_ads = db.query(SponsoredBrandAd).filter(
        SponsoredBrandAd.search_task_id == task.id
    ).order_by(SponsoredBrandAd.position).all()

    return {
        "keyword": task.keyword,
        "sponsored_brands": [
            {
                "seller_name": ad.seller_name,
                "seller_id": ad.seller_id,
                "position": ad.position,
                "products": ad.products or [],
                "snapshot_date": ad.snapshot_date.isoformat() if ad.snapshot_date else None
            }
            for ad in brand_ads
        ]
    }

@router.get("/keyword-history")
async def get_keyword_history(
    platform: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının arama geçmişi — tekil keyword'ler, son arama tarihi ve toplam sonuç."""
    query = db.query(
        SearchTask.keyword,
        SearchTask.platform,
        func.count(SearchTask.id).label("search_count"),
        func.max(SearchTask.created_at).label("last_searched"),
        func.max(SearchTask.total_products).label("max_products"),
    ).filter(
        SearchTask.user_id == user.id,
        SearchTask.status == "completed"
    )

    if platform:
        query = query.filter(SearchTask.platform == platform)

    results = query.group_by(
        SearchTask.keyword, SearchTask.platform
    ).order_by(
        func.max(SearchTask.created_at).desc()
    ).limit(limit).all()

    return {
        "keywords": [
            {
                "keyword": r.keyword,
                "platform": r.platform,
                "search_count": r.search_count,
                "last_searched": r.last_searched.isoformat() if r.last_searched else None,
                "max_products": r.max_products,
            }
            for r in results
        ]
    }


@router.get("/keyword-comparison/{keyword}")
async def compare_keyword_over_time(
    keyword: str,
    platform: str = Query("hepsiburada"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Aynı keyword'ün zaman içindeki arama sonuçlarını karşılaştır."""
    tasks = db.query(SearchTask).filter(
        SearchTask.user_id == user.id,
        SearchTask.keyword == keyword,
        SearchTask.platform == platform,
        SearchTask.status == "completed"
    ).order_by(desc(SearchTask.created_at)).limit(10).all()

    if not tasks:
        raise HTTPException(404, "Bu keyword için arama sonucu bulunamadı")

    comparison = []
    for task in tasks:
        # Her task için sponsorlu ürün sayısını al
        sponsored_count = db.query(func.count(SearchSponsoredProduct.id)).filter(
            SearchSponsoredProduct.search_task_id == task.id
        ).scalar() or 0

        brand_ad_count = db.query(func.count(SponsoredBrandAd.id)).filter(
            SponsoredBrandAd.search_task_id == task.id
        ).scalar() or 0

        comparison.append({
            "task_id": str(task.id),
            "date": task.created_at.isoformat(),
            "total_products": task.total_products,
            "sponsored_products": sponsored_count,
            "brand_ads": brand_ad_count,
        })

    return {
        "keyword": keyword,
        "platform": platform,
        "total_searches": len(comparison),
        "history": comparison,
    }


@router.get("/search/{task_id}/sponsored-products")
async def get_sponsored_products(task_id: str, db: Session = Depends(get_db)):
    """Get sponsored products for a search task (sıralı liste)"""
    task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    sponsored = db.query(SearchSponsoredProduct).filter(
        SearchSponsoredProduct.search_task_id == task.id
    ).order_by(SearchSponsoredProduct.order_index).all()

    return {
        "keyword": task.keyword,
        "total_sponsored": len(sponsored),
        "sponsored_products": [
            {
                "order_index": sp.order_index,
                "product_url": sp.product_url,
                "product_name": sp.product_name,
                "seller_name": sp.seller_name,
                "price": float(sp.price) if sp.price else None,
                "discounted_price": float(sp.discounted_price) if sp.discounted_price else None,
                "image_url": sp.image_url,
                "snapshot_date": sp.snapshot_date.isoformat() if sp.snapshot_date else None
            }
            for sp in sponsored
        ]
    }
