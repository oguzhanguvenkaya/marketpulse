import asyncio
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, text
from sqlalchemy.exc import OperationalError
from typing import List, Optional, Dict, Any, Callable
from pydantic import BaseModel
from uuid import UUID
from urllib.parse import quote_plus
from time import perf_counter
from app.db.database import get_db, SessionLocal
from app.db.models import Product, ProductSnapshot, ProductSeller, ProductReview, SearchTask, SponsoredBrandAd, SearchSponsoredProduct, MonitoredProduct, SellerSnapshot, PriceMonitorTask
from app.services.scraping import ScrapingService, get_proxy_status
from app.services.llm_service import LLMService
from app.services.price_monitor_service import price_monitor_service
from app.services.trendyol_price_monitor_service import trendyol_price_monitor_service
from app.core.config import settings
from app.core.logger import api_logger as logger, log_endpoint_metric
from app.core.security import require_mutating_api_key

router = APIRouter(dependencies=[Depends(require_mutating_api_key)])

class SearchRequest(BaseModel):
    keyword: str
    platform: str = "hepsiburada"

class AnalysisRequest(BaseModel):
    product_ids: List[str]
    question: Optional[str] = None

class SearchTaskResponse(BaseModel):
    id: str
    keyword: str
    platform: str
    status: str
    total_products: int
    created_at: str
    
    class Config:
        from_attributes = True

class CouponResponse(BaseModel):
    amount: Optional[int] = None
    min_order: Optional[int] = None

class CampaignResponse(BaseModel):
    name: str
    url: Optional[str] = None

class SellerResponse(BaseModel):
    seller_name: str
    seller_rating: Optional[float] = None
    price: Optional[float] = None
    is_authorized: bool = False

class ReviewResponse(BaseModel):
    author: Optional[str] = None
    rating: Optional[int] = None
    review_text: Optional[str] = None
    review_date: Optional[str] = None
    seller_name: Optional[str] = None

class ProductResponse(BaseModel):
    id: str
    platform: str
    external_id: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    name: str
    url: str
    brand: Optional[str] = None
    seller_name: Optional[str] = None
    seller_rating: Optional[float] = None
    category_path: Optional[str] = None
    category_hierarchy: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    origin_country: Optional[str] = None
    latest_price: Optional[float] = None
    discounted_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    latest_rating: Optional[float] = None
    reviews_count: Optional[int] = None
    stock_count: Optional[int] = None
    in_stock: Optional[bool] = None
    is_sponsored: Optional[bool] = None
    coupons: Optional[List[Dict[str, Any]]] = None
    campaigns: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        from_attributes = True

class ProductDetailResponse(ProductResponse):
    other_sellers: List[SellerResponse] = []
    reviews: List[ReviewResponse] = []

class SnapshotResponse(BaseModel):
    id: int
    price: Optional[float] = None
    discounted_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    stock_count: Optional[int] = None
    in_stock: bool = True
    is_sponsored: bool = False
    coupons: Optional[List[Dict[str, Any]]] = None
    campaigns: Optional[List[Dict[str, Any]]] = None
    snapshot_date: str
    
    class Config:
        from_attributes = True


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _calculate_price_alerts(
    platform: str,
    snapshot: SellerSnapshot,
    threshold: Optional[float],
    campaign_threshold: Optional[float]
) -> Dict[str, Optional[float]]:
    current_price = _to_float(snapshot.price)
    original_price = _to_float(snapshot.original_price)
    campaign_price = _to_float(snapshot.campaign_price)

    if platform == "trendyol":
        list_price = original_price if original_price is not None else current_price
        selling_price = current_price
        has_price_alert = threshold is not None and list_price is not None and list_price < threshold
        has_campaign_alert = (
            campaign_threshold is not None
            and original_price is not None
            and current_price is not None
            and current_price < campaign_threshold
        )
    else:
        list_price = original_price if original_price is not None else current_price
        selling_price = campaign_price if campaign_price is not None else current_price
        has_price_alert = threshold is not None and list_price is not None and list_price < threshold
        has_campaign_alert = campaign_threshold is not None and campaign_price is not None and campaign_price < campaign_threshold

    return {
        "list_price": list_price,
        "selling_price": selling_price,
        "original_price": original_price,
        "campaign_price": campaign_price,
        "has_price_alert": has_price_alert,
        "has_campaign_alert": has_campaign_alert,
    }


def _parse_review_date(value: Any) -> Optional[date]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _is_valid_http_url(url: Optional[str]) -> bool:
    return isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))


def _build_product_search_url(platform: str, sku: Optional[str]) -> Optional[str]:
    if not isinstance(sku, str):
        return None

    normalized = sku.strip()
    if not normalized:
        return None

    encoded = quote_plus(normalized)
    if platform.lower() == "trendyol":
        return f"https://www.trendyol.com/arama?q={encoded}"
    return f"https://www.hepsiburada.com/ara?q={encoded}"


def _resolve_product_url(platform: str, sku: Optional[str], product_url: Optional[str]) -> str:
    if _is_valid_http_url(product_url):
        return product_url.strip()

    return _build_product_search_url(platform, sku) or ""


def _require_scraper_api_or_503() -> str:
    try:
        return settings.require_scraper_api_key()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


def _is_queue_reachable() -> bool:
    client = None
    try:
        from redis import Redis
        client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        return bool(client.ping())
    except Exception:
        return False
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def _require_queue_or_503() -> None:
    if not _is_queue_reachable():
        raise HTTPException(status_code=503, detail="Fetch queue unavailable. Check Redis/Celery worker.")


def _is_retryable_db_operational_error(exc: OperationalError) -> bool:
    text = str(exc).lower()
    retryable_markers = (
        "ssl connection has been closed unexpectedly",
        "server closed the connection unexpectedly",
        "connection not open",
        "could not receive data from server",
    )
    return any(marker in text for marker in retryable_markers)


def _run_read_query_with_retry(
    db: Session,
    operation: Callable[[], Any],
    endpoint_name: str,
) -> Any:
    attempts = 2
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except OperationalError as exc:
            db.rollback()
            if attempt >= attempts or not _is_retryable_db_operational_error(exc):
                raise
            logger.warning(
                f"Retrying read endpoint '{endpoint_name}' after OperationalError (attempt {attempt}/{attempts}): {exc}"
            )
    return operation()

async def run_scraping_background(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
        if not task:
            return
        
        task.status = "running"
        db.commit()
        
        scraper = ScrapingService()
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
async def create_search_task(request: SearchRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = SearchTask(
        keyword=request.keyword,
        platform=request.platform,
        status="pending"
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
    db: Session = Depends(get_db)
):
    tasks = db.query(SearchTask).order_by(desc(SearchTask.created_at)).limit(limit).all()
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
    
    llm = LLMService()
    analysis = await llm.analyze_products(products_data, request.question)
    return {"analysis": analysis}

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    total_products = db.query(Product).count()
    total_snapshots = db.query(ProductSnapshot).count()
    total_tasks = db.query(SearchTask).count()
    completed_tasks = db.query(SearchTask).filter(SearchTask.status == "completed").count()
    total_sellers = db.query(ProductSeller).count()
    total_reviews = db.query(ProductReview).count()
    
    return {
        "total_products": total_products,
        "total_snapshots": total_snapshots,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "total_sellers": total_sellers,
        "total_reviews": total_reviews
    }

@router.get("/scraping/status")
async def get_scraping_status():
    status = get_proxy_status()
    return status


class MonitoredProductInput(BaseModel):
    productUrl: Optional[str] = None
    productName: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None  # threshold_price olarak kaydedilecek (original_price için alert)
    campaignPrice: Optional[float] = None  # alert_campaign_price olarak kaydedilecek (campaign_price için alert)
    sellerStockCode: Optional[str] = None

class BulkProductsRequest(BaseModel):
    products: List[MonitoredProductInput]
    platform: str = "hepsiburada"  # hepsiburada veya trendyol

class MonitoredProductResponse(BaseModel):
    id: str
    platform: str = "hepsiburada"
    sku: str
    barcode: Optional[str] = None
    product_url: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    seller_stock_code: Optional[str] = None
    threshold_price: Optional[float] = None
    alert_campaign_price: Optional[float] = None
    image_url: Optional[str] = None
    is_active: bool = True
    last_fetched_at: Optional[str] = None
    seller_count: int = 0
    has_price_alert: bool = False  # original_price eşik altı satıcı var mı
    price_alert_count: int = 0  # original_price eşik altı satıcı sayısı
    has_campaign_alert: bool = False  # campaign_price eşik altı satıcı var mı
    campaign_alert_count: int = 0  # campaign_price eşik altı satıcı sayısı
    
    class Config:
        from_attributes = True

class SellerSnapshotResponse(BaseModel):
    merchant_id: str
    merchant_name: str
    merchant_logo: Optional[str] = None
    merchant_rating: Optional[float] = None
    merchant_rating_count: Optional[int] = None
    merchant_city: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    minimum_price: Optional[float] = None
    discount_rate: Optional[float] = None
    stock_quantity: Optional[int] = None
    buybox_order: Optional[int] = None
    free_shipping: bool = False
    fast_shipping: bool = False
    price_alert: bool = False  # Eşik fiyatın altında mı
    is_fulfilled_by_hb: bool = False
    campaigns: List[str] = []  # Kampanya ve indirim etiketleri
    campaign_price: Optional[float] = None  # Sepete özel/kampanyalı fiyat
    snapshot_date: str
    
    class Config:
        from_attributes = True

class ProductWithSellersResponse(BaseModel):
    product: MonitoredProductResponse
    sellers: List[SellerSnapshotResponse]

class FetchTaskResponse(BaseModel):
    id: str
    status: str
    total_products: int
    completed_products: int
    failed_products: int
    created_at: str
    completed_at: Optional[str] = None
    
    class Config:
        from_attributes = True


def extract_sku_from_url(url: str, platform: str = "hepsiburada") -> Optional[str]:
    """URL'den SKU çıkar"""
    import re
    if platform == "hepsiburada":
        match = re.search(r'-p[m]?-([A-Z0-9]+)', url, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    elif platform == "trendyol":
        match = re.search(r'-p-(\d+)', url)
        if match:
            return match.group(1)
    return None


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
            errors.append({"sku": item.sku or item.productUrl, "error": str(e)})
    
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
                await trendyol_price_monitor_service.fetch_all_products(db, task, product_ids, platform, fetch_type)
            else:
                await price_monitor_service.fetch_all_products(db, task, product_ids, platform, fetch_type)
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
        success = await trendyol_price_monitor_service.fetch_and_save_product(db, product)
    else:
        success = await price_monitor_service.fetch_and_save_product(db, product)
    
    if success:
        return {"success": True, "message": f"{product.sku} için satıcı verileri güncellendi", "platform": product.platform}
    else:
        raise HTTPException(status_code=500, detail="Satıcı verileri çekilemedi")


@router.get("/sellers")
async def get_sellers(
    platform: str = Query("hepsiburada", description="Platform: hepsiburada veya trendyol"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
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
                    """
                ),
                {"platform": platform.lower()},
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
        {"platform": platform.lower(), "merchant_id": merchant_id},
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


@router.get("/sellers/{merchant_id}/products")
async def get_seller_products(
    merchant_id: str,
    platform: str = Query("hepsiburada", description="Platform"),
    price_alert_only: bool = Query(False, description="Sadece price alert olan ürünleri göster"),
    campaign_alert_only: bool = Query(False, description="Sadece campaign alert olan ürünleri göster"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
