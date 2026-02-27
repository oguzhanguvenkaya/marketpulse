"""Otomasyon Kurallari API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.automation_service import automation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/automation", tags=["Automation"])


@router.get("/rule-types")
async def get_rule_types(user: User = Depends(get_current_user)):
    """Kullanilabilir otomasyon kural tiplerini dondur."""
    return automation_service.get_rule_types()


class CreateRuleRequest(BaseModel):
    rule_type: str
    name: str
    params: dict
    action: str
    product_ids: Optional[list[str]] = None
    platform: Optional[str] = None
    is_active: bool = True


@router.post("/rules")
async def create_rule(
    req: CreateRuleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Yeni otomasyon kurali olustur."""
    return await automation_service.create_rule(
        user, db,
        rule_type=req.rule_type,
        name=req.name,
        params=req.params,
        action=req.action,
        product_ids=req.product_ids,
        platform=req.platform,
        is_active=req.is_active,
    )


class DryRunRequest(BaseModel):
    product_id: str
    scenario: str = "match_lowest"


@router.post("/dry-run")
async def dry_run_price_war(
    req: DryRunRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fiyat savasi dry-run simulasyonu."""
    return await automation_service.dry_run_price_war(
        user, db, req.product_id, req.scenario
    )


@router.get("/logs")
async def get_automation_logs(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Otomasyon calisma log'lari."""
    return await automation_service.get_automation_logs(user, db, limit)
