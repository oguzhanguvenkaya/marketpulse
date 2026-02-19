#!/usr/bin/env python3
"""
Guarded recovery script for products that were marked inactive during a failed fetch window.

Rule:
- Use a completed price_monitor_task.
- Candidate SKUs come from task.last_inactive_skus.
- Reactivate only products that are currently inactive AND had no seller snapshots
  written during that task window.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
from typing import Iterable
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.database import SessionLocal
from app.db.models import MonitoredProduct, SellerSnapshot, PriceMonitorTask


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reactivate guarded inactive products for a failed fetch window."
    )
    parser.add_argument(
        "--platform",
        default="hepsiburada",
        choices=["hepsiburada", "trendyol"],
        help="Target platform (default: hepsiburada).",
    )
    parser.add_argument(
        "--task-id",
        default=None,
        help="Optional specific price_monitor_task UUID. If omitted, latest completed task is used.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag script runs as dry-run.",
    )
    return parser.parse_args()


def load_task(db, platform: str, task_id: str | None) -> PriceMonitorTask | None:
    if task_id:
        try:
            parsed_id = UUID(task_id)
        except ValueError:
            raise SystemExit(f"Invalid --task-id UUID: {task_id}")
        return db.query(PriceMonitorTask).filter(PriceMonitorTask.id == parsed_id).first()

    return (
        db.query(PriceMonitorTask)
        .filter(
            PriceMonitorTask.platform == platform,
            PriceMonitorTask.status == "completed",
        )
        .order_by(PriceMonitorTask.completed_at.desc())
        .first()
    )


def select_reactivation_candidates(
    db,
    task: PriceMonitorTask,
    platform: str,
    inactive_skus: Iterable[str],
) -> list[MonitoredProduct]:
    window_start = task.created_at
    window_end = task.completed_at or datetime.utcnow()

    products = (
        db.query(MonitoredProduct)
        .filter(
            MonitoredProduct.platform == platform,
            MonitoredProduct.is_active.is_(False),
            MonitoredProduct.sku.in_(list(inactive_skus)),
        )
        .all()
    )

    candidates: list[MonitoredProduct] = []
    for product in products:
        has_snapshot_in_window = (
            db.query(SellerSnapshot.id)
            .filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.snapshot_date >= window_start,
                SellerSnapshot.snapshot_date <= window_end,
            )
            .first()
            is not None
        )
        if not has_snapshot_in_window:
            candidates.append(product)

    return candidates


def main() -> int:
    args = parse_args()
    db = SessionLocal()
    try:
        task = load_task(db, args.platform, args.task_id)
        if not task:
            print("No matching price monitor task found.")
            return 1

        inactive_skus = task.last_inactive_skus or []
        if not inactive_skus:
            print("Task has no last_inactive_skus; nothing to do.")
            return 0

        candidates = select_reactivation_candidates(db, task, args.platform, inactive_skus)
        print(
            f"Task={task.id} platform={args.platform} "
            f"inactive_skus={len(inactive_skus)} guarded_candidates={len(candidates)}"
        )

        if not candidates:
            print("No guarded candidates found.")
            return 0

        for product in candidates:
            print(f"- {product.id} | SKU={product.sku} | name={product.product_name}")

        if not args.apply:
            print("Dry-run mode. Use --apply to perform reactivation.")
            return 0

        for product in candidates:
            product.is_active = True
            product.last_fetched_at = datetime.utcnow()

        db.commit()
        print(f"Reactivated {len(candidates)} products.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
