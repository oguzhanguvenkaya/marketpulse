"""Plan tier limitleri enforcement middleware."""

import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, MonitoredProduct, Subscription
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

TIER_LIMITS = {
    "free": {"max_skus": 10, "max_platforms": 1, "scan_per_day": 1, "history_days": 7, "email_alerts_per_day": 0, "keyword_search_per_day": 5},
    "starter": {"max_skus": 200, "max_platforms": 2, "scan_per_day": 2, "history_days": 30, "email_alerts_per_day": 10, "keyword_search_per_day": 20},
    "pro": {"max_skus": 1000, "max_platforms": 99, "scan_per_day": 4, "history_days": 90, "email_alerts_per_day": 999999, "keyword_search_per_day": 100},
    "enterprise": {"max_skus": 999999, "max_platforms": 99, "scan_per_day": 24, "history_days": 999999, "email_alerts_per_day": 999999, "keyword_search_per_day": 999999},
}


def get_user_limits(user: User) -> dict:
    """Kullanıcının plan limitlerini döndür."""
    return TIER_LIMITS.get(user.plan_tier or "free", TIER_LIMITS["free"])


async def check_sku_limit(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SKU ekleme limiti kontrolü — route dependency olarak kullanılır."""
    limits = get_user_limits(user)
    current_count = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user.id,
        MonitoredProduct.is_active == True,
    ).count()

    if current_count >= limits["max_skus"]:
        raise HTTPException(
            status_code=403,
            detail=f"SKU limitinize ulastiniz ({current_count}/{limits['max_skus']}). "
                   f"Daha fazla SKU eklemek icin planinizi yukseltin."
        )
    return user


def check_feature_access(user: User, feature: str) -> bool:
    """Ozelligin kullanicinin planinda olup olmadigini kontrol et."""
    limits = get_user_limits(user)

    feature_checks = {
        "email_alerts": limits["email_alerts_per_day"] > 0,
        "csv_export": user.plan_tier in ("starter", "pro", "enterprise"),
        "webhook": user.plan_tier in ("pro", "enterprise"),
        "api_access": user.plan_tier == "enterprise",
        "category_explorer": user.plan_tier in ("pro", "enterprise"),
        "url_scraper": user.plan_tier in ("pro", "enterprise"),
        "video_transcripts": user.plan_tier in ("pro", "enterprise"),
        "json_editor": user.plan_tier in ("pro", "enterprise"),
    }

    return feature_checks.get(feature, False)
