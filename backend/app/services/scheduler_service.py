"""
Otomatik zamanlama servisi — Dual Executor: Local + Celery.

Plan tier'a göre frekans kontrolü, due task dispatch, deduplication.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ScheduledTask, User, MonitoredProduct

logger = logging.getLogger(__name__)


class SchedulerService:
    """Executor-agnostic task dispatch logic."""

    TIER_LIMITS = {
        "free": {"frequency_hours": 24, "max_skus": 10},
        "starter": {"frequency_hours": 12, "max_skus": 200},
        "pro": {"frequency_hours": 6, "max_skus": 1000},
        "enterprise": {"frequency_hours": 1, "max_skus": None},
    }

    # In-memory dedup — aynı task aynı anda 2x dispatch olmasın
    _running_keys: set = set()

    def get_tier_limits(self, plan_tier: str) -> dict:
        return self.TIER_LIMITS.get(plan_tier, self.TIER_LIMITS["free"])

    async def dispatch_due_tasks(self, db: Session) -> int:
        """Due olan task'ları bul ve executor'a gönder. Dispatch edilen sayı döner."""
        now = datetime.utcnow()
        due_tasks = (
            db.query(ScheduledTask)
            .filter(
                ScheduledTask.next_run_at <= now,
                ScheduledTask.is_active == True,
            )
            .all()
        )

        dispatched = 0
        for task in due_tasks:
            dedup_key = f"{task.user_id}:{task.platform}:{task.task_type}"
            if dedup_key in self._running_keys:
                logger.debug(f"Skipping duplicate task: {dedup_key}")
                continue

            try:
                self._running_keys.add(dedup_key)
                await self._execute_task(task, db)
                dispatched += 1

                # next_run_at güncelle
                task.last_run_at = now
                task.next_run_at = now + timedelta(hours=task.frequency_hours)
                db.commit()
            except Exception as e:
                logger.error(f"Task dispatch failed {dedup_key}: {e}")
                db.rollback()
            finally:
                self._running_keys.discard(dedup_key)

        if dispatched > 0:
            logger.info(f"Dispatched {dispatched}/{len(due_tasks)} due tasks")
        return dispatched

    async def _execute_task(self, task: ScheduledTask, db: Session):
        """Task'ı executor'a gönder (local veya celery)."""
        executor = settings.price_monitor_executor()

        if task.task_type == "price_monitor":
            if executor == "local":
                await self._run_price_monitor_local(task, db)
            else:
                self._run_price_monitor_celery(task)
        else:
            logger.warning(f"Unknown task_type: {task.task_type}")

    async def _run_price_monitor_local(self, task: ScheduledTask, db: Session):
        """Local mode: in-process async fetch."""
        from app.db.models import PriceMonitorTask
        from app.api.price_monitor_routes import run_fetch_task

        pm_task = PriceMonitorTask(
            user_id=task.user_id,
            platform=task.platform,
            status="pending",
            fetch_type="active",
        )
        db.add(pm_task)
        db.commit()
        db.refresh(pm_task)

        asyncio.create_task(
            run_fetch_task(str(pm_task.id), task.platform)
        )
        logger.info(
            f"Local dispatch: user={task.user_id} platform={task.platform} "
            f"pm_task={pm_task.id}"
        )

    def _run_price_monitor_celery(self, task: ScheduledTask):
        """Celery mode: task'ı Redis queue'ya gönder."""
        from app.tasks import send_price_monitor_task
        from app.db.database import SessionLocal

        db = SessionLocal()
        try:
            from app.db.models import PriceMonitorTask
            pm_task = PriceMonitorTask(
                user_id=task.user_id,
                platform=task.platform,
                status="pending",
                fetch_type="active",
            )
            db.add(pm_task)
            db.commit()
            db.refresh(pm_task)

            send_price_monitor_task(str(pm_task.id), task.platform, "active")
            logger.info(
                f"Celery dispatch: user={task.user_id} platform={task.platform} "
                f"pm_task={pm_task.id}"
            )
        finally:
            db.close()

    async def create_default_schedule(
        self,
        db: Session,
        user_id,
        platform: str,
        plan_tier: str = "free",
    ) -> ScheduledTask:
        """Kullanıcı için varsayılan schedule oluştur."""
        limits = self.get_tier_limits(plan_tier)
        now = datetime.utcnow()

        existing = (
            db.query(ScheduledTask)
            .filter(
                ScheduledTask.user_id == user_id,
                ScheduledTask.platform == platform,
                ScheduledTask.task_type == "price_monitor",
            )
            .first()
        )
        if existing:
            existing.frequency_hours = limits["frequency_hours"]
            existing.is_active = True
            db.commit()
            return existing

        task = ScheduledTask(
            user_id=user_id,
            platform=platform,
            task_type="price_monitor",
            frequency_hours=limits["frequency_hours"],
            next_run_at=now + timedelta(hours=limits["frequency_hours"]),
            is_active=True,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def get_user_sku_count(self, db: Session, user_id) -> int:
        """Kullanıcının toplam aktif SKU sayısı."""
        return (
            db.query(MonitoredProduct)
            .filter(
                MonitoredProduct.user_id == user_id,
                MonitoredProduct.is_active == True,
            )
            .count()
        )

    def check_sku_limit(self, db: Session, user_id, plan_tier: str) -> bool:
        """Kullanıcı SKU limitini aşmış mı kontrol et."""
        limits = self.get_tier_limits(plan_tier)
        max_skus = limits.get("max_skus")
        if max_skus is None:  # enterprise — sınırsız
            return True
        current = self.get_user_sku_count(db, user_id)
        return current < max_skus

    async def cleanup_old_snapshots(self, db: Session):
        """Plan tier'a göre eski seller_snapshots kayıtlarını temizle."""
        from sqlalchemy import text

        retention_days = {
            "free": 7,
            "starter": 30,
            "pro": 90,
        }

        for tier, days in retention_days.items():
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = db.execute(
                text("""
                    DELETE FROM seller_snapshots
                    WHERE monitored_product_id IN (
                        SELECT mp.id FROM monitored_products mp
                        JOIN users u ON mp.user_id = u.id
                        WHERE u.plan_tier = :tier
                    )
                    AND snapshot_date < :cutoff
                """),
                {"tier": tier, "cutoff": cutoff},
            )
            if result.rowcount > 0:
                logger.info(f"Cleaned {result.rowcount} old snapshots for {tier} users (>{days} days)")

        db.commit()


scheduler_service = SchedulerService()
