"""Kampanya Firsat Merkezi (Opportunity Hub) routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.campaign_service import campaign_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])


@router.get("/available")
async def get_available_campaigns(
    platform: Optional[str] = Query(None, description="Platform filtresi (hepsiburada, trendyol)"),
    status: Optional[str] = Query(None, description="Kampanya durumu (active, upcoming)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanilabilir kampanyalari listele."""
    return await campaign_service.get_available_campaigns(user, db, platform, status)


class AnalyzeRequest(BaseModel):
    campaign_id: str
    product_id: Optional[str] = None


@router.post("/analyze")
async def analyze_campaign(
    req: AnalyzeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kampanya firsatini analiz et — karlilik simulasyonu ve AI onerisi."""
    return await campaign_service.analyze_campaign_opportunity(
        user, db, req.campaign_id, req.product_id
    )


@router.get("/history")
async def get_campaign_history(
    product_id: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kampanya gecmisi — onceki katilimlar ve fiyat degisiklikleri."""
    return await campaign_service.get_campaign_history(user, db, product_id)
