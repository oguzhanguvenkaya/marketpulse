import asyncio
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logger import price_monitor_logger as logger

_celery_app = None


def get_celery_app():
    global _celery_app
    if _celery_app is None:
        from celery import Celery
        _celery_app = Celery(
            'tasks',
            broker=settings.REDIS_URL,
            backend=settings.REDIS_URL
        )
        _celery_app.conf.update(
            task_serializer='json',
            result_serializer='json',
            accept_content=['json'],
            timezone='Europe/Istanbul',
            enable_utc=True,
            task_track_started=True,
            result_expires=3600,
        )
        _register_tasks(_celery_app)
    return _celery_app


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _register_tasks(app):
    @app.task(bind=True, max_retries=3, name='tasks.run_scraping_task')
    def _run_scraping_task(self, task_id: str):
        from app.db.database import get_session_local
        from app.db.models import Product, ProductSnapshot, SearchTask
        from app.services.scraping import ScrapingService

        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            task = db.query(SearchTask).filter(SearchTask.id == task_id).first()
            if not task:
                return {"error": "Task not found"}

            task.status = "running"
            db.commit()

            scraper = ScrapingService()
            products = run_async(_scrape_and_save(scraper, task.keyword, task.platform, db))

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

    @app.task(bind=True, max_retries=0, name='tasks.run_price_monitor_fetch_task')
    def _run_price_monitor_fetch_task(
        self,
        task_id: str,
        platform: str,
        fetch_type: str = "active",
        product_ids: Optional[List[str]] = None,
    ):
        from app.db.database import get_session_local
        from app.db.models import PriceMonitorTask
        from app.services.price_monitor_service import price_monitor_service
        from app.services.trendyol_price_monitor_service import trendyol_price_monitor_service

        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            task = db.query(PriceMonitorTask).filter(PriceMonitorTask.id == task_id).first()
            if not task:
                return {"error": "Task not found"}

            try:
                settings.require_scraper_api_key()
            except ValueError as exc:
                task.status = "failed"
                task.error_message = str(exc)
                task.completed_at = datetime.utcnow()
                db.commit()
                return {"status": "failed", "reason": "missing_scraper_key"}

            logger.info(
                f"Starting celery price-monitor fetch task_id={task_id} platform={platform} fetch_type={fetch_type}"
            )

            if platform == "trendyol":
                run_async(
                    trendyol_price_monitor_service.fetch_all_products(
                        db=db,
                        task=task,
                        product_ids=product_ids,
                        platform=platform,
                        fetch_type=fetch_type,
                    )
                )
            else:
                run_async(
                    price_monitor_service.fetch_all_products(
                        db=db,
                        task=task,
                        product_ids=product_ids,
                        platform=platform,
                        fetch_type=fetch_type,
                    )
                )

            return {"status": "completed", "task_id": task_id}
        except Exception as exc:
            db.rollback()
            task = db.query(PriceMonitorTask).filter(PriceMonitorTask.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = str(exc)
                task.completed_at = datetime.utcnow()
                db.commit()
            logger.error(f"Price monitor celery task failed task_id={task_id}: {exc}")
            raise
        finally:
            db.close()


async def _scrape_and_save(scraper, keyword: str, platform: str, db: Session):
    from app.db.models import Product, ProductSnapshot

    try:
        await scraper.init_browser()

        if platform == "hepsiburada":
            search_result = await scraper.scrape_hepsiburada_search(keyword, max_products=100)
            products_data = search_result.get('products', [])
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


def send_price_monitor_task(task_id: str, platform: str, fetch_type: str, product_ids=None):
    celery = get_celery_app()
    return celery.send_task(
        'tasks.run_price_monitor_fetch_task',
        args=[task_id, platform, fetch_type, product_ids],
    )


def send_scraping_task(task_id: str):
    celery = get_celery_app()
    return celery.send_task(
        'tasks.run_scraping_task',
        args=[task_id],
    )
