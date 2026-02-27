"""Reklam Kelimesi Onerisi API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.keyword_recommendation_service import keyword_recommendation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keyword-recommendations", tags=["Keyword Recommendations"])


@router.get("/")
async def get_recommendations(
    product_id: Optional[str] = Query(None, description="Urun ID (UUID)"),
    platform: Optional[str] = Query(None, description="Platform filtresi"),
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reklam kelimesi onerileri al."""
    return await keyword_recommendation_service.get_keyword_recommendations(
        user, db, product_id, platform, limit
    )


class ClickWasteRequest(BaseModel):
    keyword: str
    product_id: Optional[str] = None


@router.post("/click-waste-check")
async def check_click_waste_risk(
    req: ClickWasteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bosa tiklama riski tespiti."""
    return await keyword_recommendation_service.detect_click_waste_risk(
        user, db, req.keyword, req.product_id
    )
