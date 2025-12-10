import asyncio
from datetime import datetime, date
from celery import Celery
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Product, ProductSnapshot, SearchTask
from app.services.scraping import ScrapingService

celery_app = Celery(
    'tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Europe/Istanbul',
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
)

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@celery_app.task(bind=True, max_retries=3)
def run_scraping_task(self, task_id: str):
    db = SessionLocal()
    try:
        task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        task.status = "running"
        db.commit()
        
        scraper = ScrapingService()
        products = run_async(scrape_and_save(scraper, task.keyword, task.platform, db))
        
        task.status = "completed"
        task.total_products = len(products)
        task.completed_at = datetime.utcnow()
        db.commit()
        
        return {"status": "completed", "products_count": len(products)}
    
    except Exception as e:
        task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.error_message = str(e)
            db.commit()
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()

async def scrape_and_save(scraper: ScrapingService, keyword: str, platform: str, db: Session):
    try:
        await scraper.init_browser()
        
        if platform == "hepsiburada":
            products_data = await scraper.scrape_hepsiburada_search(keyword, max_products=100)
        else:
            products_data = []
        
        saved_products = []
        today = date.today()
        
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
            
            saved_products.append(product)
        
        db.commit()
        return saved_products
    
    finally:
        await scraper.close_browser()
