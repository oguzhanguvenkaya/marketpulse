"""
Scheduler API endpoint'leri.

- POST /api/scheduler/dispatch — Cloud Scheduler trigger (veya manuel)
- GET /api/scheduler/tasks — Kullanıcının schedule'larını listele
- POST /api/scheduler/tasks — Yeni schedule oluştur
- PUT /api/scheduler/tasks/{id} — Schedule güncelle
- DELETE /api/scheduler/tasks/{id} — Schedule sil
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.models import ScheduledTask, User
from app.core.auth import get_current_user
from app.services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/scheduler",
    tags=["Scheduler"],
    dependencies=[Depends(get_current_user)],
)


class ScheduleCreateRequest(BaseModel):
    platform: str
    task_type: str = "price_monitor"


class ScheduleUpdateRequest(BaseModel):
    is_active: Optional[bool] = None


@router.post("/dispatch")
async def trigger_dispatch(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Due olan task'ları dispatch et.

    Cloud Scheduler bu endpoint'i her 30 dk'da çağırır.
    Kullanıcı da manuel tetikleyebilir (kendi task'ları için).
    """
    dispatched = await scheduler_service.dispatch_due_tasks(db)
    return {"dispatched": dispatched, "message": f"{dispatched} task dispatched"}


@router.get("/tasks")
async def list_schedules(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının aktif schedule'larını listele."""
    tasks = (
        db.query(ScheduledTask)
        .filter(ScheduledTask.user_id == user.id)
        .order_by(ScheduledTask.platform)
        .all()
    )
    return {
        "schedules": [
            {
                "id": str(t.id),
                "platform": t.platform,
                "task_type": t.task_type,
                "frequency_hours": t.frequency_hours,
                "is_active": t.is_active,
                "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
                "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
            }
            for t in tasks
        ]
    }


@router.post("/tasks")
async def create_schedule(
    request: ScheduleCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Yeni schedule oluştur (plan tier'a göre frekans otomatik belirlenir)."""
    task = await scheduler_service.create_default_schedule(
        db=db,
        user_id=user.id,
        platform=request.platform.lower(),
        plan_tier=user.plan_tier or "free",
    )
    return {
        "id": str(task.id),
        "platform": task.platform,
        "frequency_hours": task.frequency_hours,
        "next_run_at": task.next_run_at.isoformat(),
        "is_active": task.is_active,
    }


@router.put("/tasks/{task_id}")
async def update_schedule(
    task_id: str,
    request: ScheduleUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Schedule güncelle (aktif/pasif)."""
    task = (
        db.query(ScheduledTask)
        .filter(ScheduledTask.id == task_id, ScheduledTask.user_id == user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Schedule bulunamadı")

    if request.is_active is not None:
        task.is_active = request.is_active

    db.commit()
    return {"success": True, "is_active": task.is_active}


@router.delete("/tasks/{task_id}")
async def delete_schedule(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Schedule sil."""
    task = (
        db.query(ScheduledTask)
        .filter(ScheduledTask.id == task_id, ScheduledTask.user_id == user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Schedule bulunamadı")

    db.delete(task)
    db.commit()
    return {"success": True, "message": "Schedule silindi"}
