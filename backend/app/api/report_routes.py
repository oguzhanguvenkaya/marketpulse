"""Raporlama API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.report_service import report_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/weekly-summary")
async def get_weekly_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Haftalik ozet rapor verisi."""
    return await report_service.generate_weekly_summary(user, db)


@router.post("/weekly-summary/send-email")
async def send_weekly_summary_email(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Haftalik ozet raporunu email ile gonder."""
    success = await report_service.send_weekly_report_email(user, db)
    if success:
        return {"mesaj": "Haftalik rapor email ile gonderildi", "email": user.email}
    return {"mesaj": "Email gonderilemedi — RESEND_API_KEY kontrol edin", "success": False}


@router.get("/price-changes")
async def get_price_change_report(
    days: int = Query(7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fiyat degisim raporu."""
    return await report_service.generate_price_change_report(user, db, days)


@router.get("/competitors")
async def get_competitor_report(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rakip analiz raporu."""
    return await report_service.generate_competitor_report(user, db)


@router.get("/buybox-performance")
async def get_buybox_report(
    days: int = Query(7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Buybox performans raporu."""
    return await report_service.generate_buybox_report(user, db, days)
