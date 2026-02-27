from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Product, ProductSnapshot, ProductSeller, ProductReview, SearchTask
from app.core.auth import get_current_user

from app.api._shared import _get_proxy_status

router = APIRouter(dependencies=[Depends(get_current_user)])

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
    status = _get_proxy_status()
    return status
