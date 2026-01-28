import asyncio
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID
from app.db.database import get_db, SessionLocal
from app.db.models import Product, ProductSnapshot, ProductSeller, ProductReview, SearchTask, SponsoredBrandAd, SearchSponsoredProduct, MonitoredProduct, SellerSnapshot, PriceMonitorTask
from app.services.scraping import ScrapingService, get_proxy_status
from app.services.llm_service import LLMService
from app.services.price_monitor_service import price_monitor_service
from app.services.trendyol_price_monitor_service import trendyol_price_monitor_service
from app.core.logger import api_logger as logger

router = APIRouter()

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

async def run_scraping_background(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
        if not task:
            return
        
        task.status = "running"
        db.commit()
        
        scraper = ScrapingService()
        try:
            await scraper.init_browser()
            
            if task.platform == "hepsiburada":
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
                            review_date=review.get("review_date"),
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
            
            existing = db.query(MonitoredProduct).filter(
                MonitoredProduct.sku == sku,
                MonitoredProduct.platform == platform
            ).first()
            
            if existing:
                if item.productUrl:
                    existing.product_url = item.productUrl
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
                if item.sellerStockCode:
                    existing.seller_stock_code = item.sellerStockCode
                existing.is_active = True
                updated += 1
            else:
                product = MonitoredProduct(
                    platform=platform,
                    sku=sku,
                    barcode=item.barcode,
                    product_url=item.productUrl,
                    product_name=item.productName,
                    brand=item.brand,
                    threshold_price=item.price,
                    alert_campaign_price=item.campaignPrice,
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
    search: Optional[str] = None
):
    """İzlenen ürün listesini getir - platform, marka, price alert ve arama filtresi ile"""
    query = db.query(MonitoredProduct)
    if active_only:
        query = query.filter(MonitoredProduct.is_active == True)
    if platform:
        query = query.filter(MonitoredProduct.platform == platform.lower())
    if brand:
        query = query.filter(MonitoredProduct.brand == brand)
    
    products = query.order_by(desc(MonitoredProduct.created_at)).all()
    
    result = []
    for product in products:
        latest_snapshots = db.query(SellerSnapshot).filter(
            SellerSnapshot.monitored_product_id == product.id
        ).order_by(desc(SellerSnapshot.snapshot_date)).limit(20).all()
        
        seller_count = len(set(s.merchant_id for s in latest_snapshots))
        
        threshold = float(product.threshold_price) if product.threshold_price else None
        campaign_threshold = float(product.alert_campaign_price) if product.alert_campaign_price else None
        
        price_alert_count = 0
        campaign_alert_count = 0
        
        if latest_snapshots:
            for s in latest_snapshots:
                orig_price = float(s.original_price) if s.original_price else None
                camp_price = float(s.campaign_price) if s.campaign_price else None
                
                if threshold and orig_price and orig_price < threshold:
                    price_alert_count += 1
                
                if campaign_threshold and camp_price and camp_price < campaign_threshold:
                    campaign_alert_count += 1
        
        has_price_alert = price_alert_count > 0
        has_campaign_alert = campaign_alert_count > 0
        
        if price_alert_only and not has_price_alert and not has_campaign_alert:
            continue
        
        if search:
            search_lower = search.lower()
            searchable = f"{product.sku or ''} {product.barcode or ''} {product.product_name or ''} {product.seller_stock_code or ''}".lower()
            if search_lower not in searchable:
                continue
        
        result.append({
            "id": str(product.id),
            "platform": product.platform,
            "sku": product.sku,
            "barcode": product.barcode,
            "product_url": product.product_url,
            "product_name": product.product_name,
            "brand": product.brand,
            "seller_stock_code": product.seller_stock_code,
            "threshold_price": float(product.threshold_price) if product.threshold_price else None,
            "alert_campaign_price": float(product.alert_campaign_price) if product.alert_campaign_price else None,
            "image_url": product.image_url,
            "is_active": product.is_active,
            "last_fetched_at": product.last_fetched_at.isoformat() if product.last_fetched_at else None,
            "seller_count": seller_count,
            "has_price_alert": has_price_alert,
            "price_alert_count": price_alert_count,
            "has_campaign_alert": has_campaign_alert,
            "campaign_alert_count": campaign_alert_count
        })
    
    return {"products": result, "total": len(result)}


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
                
                if s.buybox_order == 1:
                    min_price_seller = {
                        "merchant_name": s.merchant_name,
                        "merchant_url": merchant_url,
                        "price": float(s.price) if s.price else None,
                        "buybox_order": 1
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
            
            orig_price = float(s.original_price) if s.original_price else None
            camp_price = float(s.campaign_price) if s.campaign_price else None
            
            has_price_alert = threshold is not None and orig_price is not None and orig_price < threshold
            has_campaign_alert = campaign_threshold is not None and camp_price is not None and camp_price < campaign_threshold
            
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
                "price": float(s.price) if s.price else None,
                "original_price": orig_price,
                "minimum_price": float(s.minimum_price) if s.minimum_price else None,
                "discount_rate": s.discount_rate,
                "stock_quantity": s.stock_quantity,
                "buybox_order": s.buybox_order,
                "free_shipping": s.free_shipping,
                "fast_shipping": s.fast_shipping,
                "is_fulfilled_by_hb": s.is_fulfilled_by_hb,
                "campaigns": s.campaigns if s.campaigns else [],
                "campaign_price": camp_price,
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
        if task:
            if platform == "trendyol":
                await trendyol_price_monitor_service.fetch_all_products(db, task, product_ids, platform)
            else:
                await price_monitor_service.fetch_all_products(db, task, product_ids, platform, fetch_type)
    finally:
        db.close()


@router.post("/price-monitor/fetch")
async def start_fetch_task(
    background_tasks: BackgroundTasks,
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
    task = PriceMonitorTask(platform=platform, status="pending", fetch_type=fetch_type)
    db.add(task)
    db.commit()
    db.refresh(task)
    
    background_tasks.add_task(run_fetch_task, str(task.id), platform, product_ids, fetch_type)
    
    return {
        "task_id": str(task.id),
        "platform": platform,
        "fetch_type": fetch_type,
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


@router.post("/price-monitor/fetch-single/{product_id}")
async def fetch_single_product(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Tek bir ürün için satıcı fiyatlarını çek - platform otomatik belirlenir"""
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
    db: Session = Depends(get_db)
):
    """Tüm satıcıları listele - her satıcının ürün sayısı ve price alert sayısı ile"""
    from sqlalchemy import func, distinct, case
    
    products = db.query(MonitoredProduct).filter(
        MonitoredProduct.platform == platform,
        MonitoredProduct.is_active == True
    ).all()
    
    product_ids = [p.id for p in products]
    product_thresholds = {str(p.id): float(p.threshold_price) if p.threshold_price else None for p in products}
    
    if not product_ids:
        return {"sellers": [], "total": 0}
    
    latest_snapshots_subq = db.query(
        SellerSnapshot.merchant_id,
        SellerSnapshot.monitored_product_id,
        func.max(SellerSnapshot.snapshot_date).label('max_date')
    ).filter(
        SellerSnapshot.monitored_product_id.in_(product_ids)
    ).group_by(
        SellerSnapshot.merchant_id,
        SellerSnapshot.monitored_product_id
    ).subquery()
    
    snapshots = db.query(SellerSnapshot).join(
        latest_snapshots_subq,
        (SellerSnapshot.merchant_id == latest_snapshots_subq.c.merchant_id) &
        (SellerSnapshot.monitored_product_id == latest_snapshots_subq.c.monitored_product_id) &
        (SellerSnapshot.snapshot_date == latest_snapshots_subq.c.max_date)
    ).all()
    
    sellers_data = {}
    for s in snapshots:
        if s.merchant_id not in sellers_data:
            sellers_data[s.merchant_id] = {
                'merchant_id': s.merchant_id,
                'merchant_name': s.merchant_name,
                'merchant_logo': s.merchant_logo,
                'merchant_url_postfix': s.merchant_url_postfix,
                'merchant_rating': float(s.merchant_rating) if s.merchant_rating else None,
                'product_count': 0,
                'price_alert_count': 0,
                'products': []
            }
        
        sellers_data[s.merchant_id]['product_count'] += 1
        
        threshold = product_thresholds.get(str(s.monitored_product_id))
        seller_price = float(s.price) if s.price else None
        if threshold and seller_price and seller_price < threshold:
            sellers_data[s.merchant_id]['price_alert_count'] += 1
    
    sellers_list = sorted(
        sellers_data.values(), 
        key=lambda x: x['price_alert_count'], 
        reverse=True
    )
    
    return {"sellers": sellers_list, "total": len(sellers_list)}


@router.get("/sellers/{merchant_id}/products")
async def get_seller_products(
    merchant_id: str,
    platform: str = Query("hepsiburada", description="Platform"),
    price_alert_only: bool = Query(False, description="Sadece price alert olan ürünleri göster"),
    db: Session = Depends(get_db)
):
    """Satıcının sattığı ürünleri listele - price alert filtresi ile"""
    from sqlalchemy import func
    
    products = db.query(MonitoredProduct).filter(
        MonitoredProduct.platform == platform,
        MonitoredProduct.is_active == True
    ).all()
    
    product_ids = [p.id for p in products]
    product_map = {str(p.id): p for p in products}
    
    if not product_ids:
        return {"products": [], "total": 0, "merchant_name": ""}
    
    latest_snapshots_subq = db.query(
        SellerSnapshot.merchant_id,
        SellerSnapshot.monitored_product_id,
        func.max(SellerSnapshot.snapshot_date).label('max_date')
    ).filter(
        SellerSnapshot.monitored_product_id.in_(product_ids),
        SellerSnapshot.merchant_id == merchant_id
    ).group_by(
        SellerSnapshot.merchant_id,
        SellerSnapshot.monitored_product_id
    ).subquery()
    
    snapshots = db.query(SellerSnapshot).join(
        latest_snapshots_subq,
        (SellerSnapshot.merchant_id == latest_snapshots_subq.c.merchant_id) &
        (SellerSnapshot.monitored_product_id == latest_snapshots_subq.c.monitored_product_id) &
        (SellerSnapshot.snapshot_date == latest_snapshots_subq.c.max_date)
    ).all()
    
    result = []
    merchant_name = ""
    
    for s in snapshots:
        if not merchant_name:
            merchant_name = s.merchant_name
        
        product = product_map.get(str(s.monitored_product_id))
        if not product:
            continue
        
        threshold = float(product.threshold_price) if product.threshold_price else None
        seller_price = float(s.price) if s.price else None
        has_alert = threshold is not None and seller_price is not None and seller_price < threshold
        
        if price_alert_only and not has_alert:
            continue
        
        base_url = product.product_url or ""
        if platform == "hepsiburada" and merchant_id:
            if "?" in base_url:
                seller_url = f"{base_url}&magaza={merchant_id}"
            else:
                seller_url = f"{base_url}?magaza={merchant_id}"
        else:
            seller_url = base_url
        
        result.append({
            "product_id": str(product.id),
            "sku": product.sku,
            "barcode": product.barcode,
            "product_name": product.product_name,
            "product_url": product.product_url,
            "seller_url": seller_url,
            "brand": product.brand,
            "seller_stock_code": product.seller_stock_code,
            "image_url": product.image_url,
            "threshold_price": threshold,
            "seller_price": seller_price,
            "original_price": float(s.original_price) if s.original_price else None,
            "campaign_price": float(s.campaign_price) if s.campaign_price else None,
            "campaigns": s.campaigns if s.campaigns else [],
            "price_alert": has_alert,
            "price_difference": round(threshold - seller_price, 2) if threshold and seller_price else None,
            "snapshot_date": s.snapshot_date.isoformat()
        })
    
    result.sort(key=lambda x: (not x['price_alert'], x['product_name'] or ''))
    
    return {"products": result, "total": len(result), "merchant_name": merchant_name}


@router.get("/sellers/{merchant_id}/export")
async def export_seller_products(
    merchant_id: str,
    platform: str = Query("hepsiburada", description="Platform"),
    price_alert_only: bool = Query(False, description="Sadece price alert olan ürünleri indir"),
    db: Session = Depends(get_db)
):
    """Satıcının ürünlerini CSV olarak indir"""
    from fastapi.responses import StreamingResponse
    import csv
    import io
    from sqlalchemy import func
    
    products = db.query(MonitoredProduct).filter(
        MonitoredProduct.platform == platform,
        MonitoredProduct.is_active == True
    ).all()
    
    product_ids = [p.id for p in products]
    product_map = {str(p.id): p for p in products}
    
    latest_snapshots_subq = db.query(
        SellerSnapshot.merchant_id,
        SellerSnapshot.monitored_product_id,
        func.max(SellerSnapshot.snapshot_date).label('max_date')
    ).filter(
        SellerSnapshot.monitored_product_id.in_(product_ids),
        SellerSnapshot.merchant_id == merchant_id
    ).group_by(
        SellerSnapshot.merchant_id,
        SellerSnapshot.monitored_product_id
    ).subquery()
    
    snapshots = db.query(SellerSnapshot).join(
        latest_snapshots_subq,
        (SellerSnapshot.merchant_id == latest_snapshots_subq.c.merchant_id) &
        (SellerSnapshot.monitored_product_id == latest_snapshots_subq.c.monitored_product_id) &
        (SellerSnapshot.snapshot_date == latest_snapshots_subq.c.max_date)
    ).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'SKU', 'Barcode', 'Product Name', 'Brand', 'Stock Code',
        'Product URL', 'Threshold Price', 'Seller Price', 
        'Price Difference', 'Price Alert', 'Campaigns', 'Snapshot Date'
    ])
    
    merchant_name = ""
    for s in snapshots:
        if not merchant_name:
            merchant_name = s.merchant_name
            
        product = product_map.get(str(s.monitored_product_id))
        if not product:
            continue
        
        threshold = float(product.threshold_price) if product.threshold_price else None
        seller_price = float(s.price) if s.price else None
        has_alert = threshold is not None and seller_price is not None and seller_price < threshold
        
        if price_alert_only and not has_alert:
            continue
        
        price_diff = round(threshold - seller_price, 2) if threshold and seller_price else None
        campaigns_str = ", ".join(s.campaigns) if s.campaigns else ""
        
        writer.writerow([
            product.sku or '',
            product.barcode or '',
            product.product_name or '',
            product.brand or '',
            product.seller_stock_code or '',
            product.product_url or '',
            threshold or '',
            seller_price or '',
            price_diff or '',
            'YES' if has_alert else 'NO',
            campaigns_str,
            s.snapshot_date.isoformat()
        ])
    
    output.seek(0)
    
    safe_merchant_name = "".join(c for c in merchant_name if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_merchant_name}_products{'_alerts' if price_alert_only else ''}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
