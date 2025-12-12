import asyncio
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID
from app.db.database import get_db, SessionLocal
from app.db.models import Product, ProductSnapshot, ProductSeller, ProductReview, SearchTask, SponsoredBrandAd
from app.services.scraping import ScrapingService, get_proxy_status
from app.services.llm_service import LLMService

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
            else:
                products_data = []
                sponsored_brands = []
            
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
                print(f"Saved {len(sponsored_brands)} brand ads to database")
            
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
        import traceback
        traceback.print_exc()
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
