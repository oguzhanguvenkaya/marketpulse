import asyncio
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from app.db.database import get_db, SessionLocal
from app.db.models import Product, ProductSnapshot, SearchTask
from app.services.scraping import ScrapingService
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

class ProductResponse(BaseModel):
    id: str
    platform: str
    external_id: str
    name: str
    url: str
    seller_name: Optional[str]
    category_path: Optional[str]
    image_url: Optional[str]
    latest_price: Optional[float] = None
    latest_rating: Optional[float] = None
    reviews_count: Optional[int] = None
    is_sponsored: Optional[bool] = None
    
    class Config:
        from_attributes = True

class SnapshotResponse(BaseModel):
    id: int
    price: Optional[float]
    rating: Optional[float]
    reviews_count: Optional[int]
    in_stock: bool
    is_sponsored: bool
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
                products_data = await scraper.scrape_hepsiburada_search(task.keyword, max_products=50)
            else:
                products_data = []
            
            today = date.today()
            saved_count = 0
            
            for p_data in products_data:
                existing = db.query(Product).filter(
                    Product.platform == p_data["platform"],
                    Product.external_id == p_data["external_id"]
                ).first()
                
                if existing:
                    product = existing
                else:
                    product = Product(
                        platform=p_data["platform"],
                        external_id=p_data["external_id"],
                        name=p_data["name"],
                        url=p_data["url"],
                        seller_name=p_data.get("seller_name"),
                        image_url=p_data.get("image_url")
                    )
                    db.add(product)
                    db.flush()
                
                existing_snapshot = db.query(ProductSnapshot).filter(
                    ProductSnapshot.product_id == product.id,
                    ProductSnapshot.snapshot_date == today
                ).first()
                
                if not existing_snapshot:
                    snapshot = ProductSnapshot(
                        product_id=product.id,
                        price=p_data.get("price"),
                        rating=p_data.get("rating"),
                        reviews_count=p_data.get("reviews_count", 0),
                        in_stock=p_data.get("in_stock", True),
                        is_sponsored=p_data.get("is_sponsored", False),
                        snapshot_date=today
                    )
                    db.add(snapshot)
                
                saved_count += 1
            
            db.commit()
            
            task.status = "completed"
            task.total_products = saved_count
            task.completed_at = datetime.utcnow()
            db.commit()
        finally:
            await scraper.close_browser()
    except Exception as e:
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
            name=p.name,
            url=p.url,
            seller_name=p.seller_name,
            category_path=p.category_path,
            image_url=p.image_url,
            latest_price=float(latest.price) if latest and latest.price else None,
            latest_rating=latest.rating if latest else None,
            reviews_count=latest.reviews_count if latest else None,
            is_sponsored=latest.is_sponsored if latest else None
        ))
    
    return result

@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    latest = db.query(ProductSnapshot).filter(
        ProductSnapshot.product_id == product.id
    ).order_by(desc(ProductSnapshot.snapshot_date)).first()
    
    return ProductResponse(
        id=str(product.id),
        platform=product.platform,
        external_id=product.external_id,
        name=product.name,
        url=product.url,
        seller_name=product.seller_name,
        category_path=product.category_path,
        image_url=product.image_url,
        latest_price=float(latest.price) if latest and latest.price else None,
        latest_rating=latest.rating if latest else None,
        reviews_count=latest.reviews_count if latest else None,
        is_sponsored=latest.is_sponsored if latest else None
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
            rating=s.rating,
            reviews_count=s.reviews_count,
            in_stock=s.in_stock,
            is_sponsored=s.is_sponsored,
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
                "platform": product.platform,
                "seller": product.seller_name,
                "snapshots": [
                    {
                        "date": s.snapshot_date.isoformat(),
                        "price": float(s.price) if s.price else None,
                        "rating": s.rating,
                        "reviews": s.reviews_count,
                        "sponsored": s.is_sponsored
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
    
    return {
        "total_products": total_products,
        "total_snapshots": total_snapshots,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks
    }
