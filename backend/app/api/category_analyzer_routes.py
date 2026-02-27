"""
AI Kategori Uyum Denetimi API endpoint'leri.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.models import User, MonitoredProduct, CategorySession, CategoryProduct
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/category-analyzer", tags=["Category Analyzer"])


class AnalyzeRequest(BaseModel):
    product_id: str
    max_competitors: int = 40


@router.post("/analyze")
async def analyze_product_category(
    request: AnalyzeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ürünün kategorideki uyumluluğunu AI ile analiz et."""
    from app.services.category_analyzer_service import category_analyzer_service

    result = await category_analyzer_service.analyze_product_category(
        user_id=str(user.id),
        product_id=request.product_id,
        db=db,
        max_competitors=request.max_competitors,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/quick-check")
async def quick_category_check(
    product_name: str,
    category_products: list[str],
    user: User = Depends(get_current_user),
):
    """Hızlı kategori uyum kontrolü (ürün adı ve rakip isimleri ile)."""
    from app.services.category_analyzer_service import category_analyzer_service

    result = await category_analyzer_service.quick_category_check(
        product_name=product_name,
        category_products=category_products,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/available-sessions")
async def get_available_sessions(
    platform: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının mevcut kategori tarama oturumlarını listele."""
    query = db.query(CategorySession).filter(
        CategorySession.user_id == user.id,
        CategorySession.status == "active",
    )
    if platform:
        query = query.filter(CategorySession.platform == platform)

    sessions = query.order_by(CategorySession.created_at.desc()).limit(20).all()

    return [
        {
            "id": str(s.id),
            "platform": s.platform,
            "category_name": s.category_name,
            "category_url": s.category_url,
            "total_products": s.total_products,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]
