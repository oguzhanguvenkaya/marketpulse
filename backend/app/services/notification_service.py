"""
Notification servisi — fiyat değişimi, buybox kaybı ve kampanya alert'leri.

Price monitor fetch tamamlandığında bu servis çağrılır.
Threshold ihlali varsa email gönderir ve AlertLog kaydı oluşturur.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from app.db.models import User, MonitoredProduct, SellerSnapshot, AlertLog

logger = logging.getLogger(__name__)

# Günlük alert limitleri (plan tier'a göre)
DAILY_ALERT_LIMITS = {
    "free": 0,       # Free plan'da email alarm yok
    "starter": 10,
    "pro": 999999,   # pratik olarak sınırsız
    "enterprise": 999999,
}


def _to_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


async def check_and_send_alerts(
    db: Session,
    user: User,
    product: MonitoredProduct,
    old_snapshots: List[Dict],
    new_snapshots: List[Dict],
) -> int:
    """Eski ve yeni snapshot'ları karşılaştır, alert varsa email gönder.

    Returns: gönderilen alert sayısı
    """
    if not user.email_alerts_enabled:
        return 0

    plan_tier = user.plan_tier or "free"
    daily_limit = DAILY_ALERT_LIMITS.get(plan_tier, 0)
    if daily_limit == 0:
        return 0

    # Bugün kaç alert gönderilmiş?
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = (
        db.query(AlertLog)
        .filter(
            AlertLog.user_id == user.id,
            AlertLog.email_sent == True,
            AlertLog.created_at >= today_start,
        )
        .count()
    )
    if sent_today >= daily_limit:
        return 0

    remaining = daily_limit - sent_today
    alerts_sent = 0

    threshold = _to_float(product.threshold_price)
    campaign_threshold = _to_float(product.alert_campaign_price)

    # Eski snapshot'ları merchant_id bazlı map'e çevir
    old_map: Dict[str, Dict] = {}
    for s in old_snapshots:
        mid = s.get("merchant_id", "")
        if mid and mid not in old_map:
            old_map[mid] = s

    # Eski buybox winner'ı bul
    old_buybox_winner = None
    for s in old_snapshots:
        if s.get("buybox_order") == 1:
            old_buybox_winner = s.get("merchant_name", "")
            break

    for new_s in new_snapshots:
        if alerts_sent >= remaining:
            break

        mid = new_s.get("merchant_id", "")
        new_price = _to_float(new_s.get("price"))
        new_original = _to_float(new_s.get("original_price"))
        new_campaign = _to_float(new_s.get("campaign_price"))
        merchant_name = new_s.get("merchant_name", "")

        old_s = old_map.get(mid, {})
        old_price = _to_float(old_s.get("price"))

        # --- Price Alert ---
        list_price = new_original if new_original is not None else new_price
        if threshold is not None and list_price is not None and list_price < threshold:
            if old_price is None or old_price >= threshold:
                # Yeni ihlal — email gönder
                sent = await _send_price_alert(
                    db, user, product, merchant_name,
                    old_price or 0.0, list_price, threshold,
                )
                if sent:
                    alerts_sent += 1

        # --- Campaign Alert ---
        if (
            campaign_threshold is not None
            and new_campaign is not None
            and new_campaign < campaign_threshold
        ):
            old_campaign = _to_float(old_s.get("campaign_price"))
            if old_campaign is None or old_campaign >= campaign_threshold:
                sent = await _send_campaign_alert(
                    db, user, product, merchant_name,
                    new_campaign, campaign_threshold,
                )
                if sent:
                    alerts_sent += 1

        # --- Buybox Lost ---
        if new_s.get("buybox_order") == 1:
            new_winner = merchant_name
            if old_buybox_winner and old_buybox_winner != new_winner:
                sent = await _send_buybox_alert(
                    db, user, product, old_buybox_winner, new_winner,
                    new_price or 0.0,
                )
                if sent:
                    alerts_sent += 1

    return alerts_sent


async def _send_price_alert(
    db: Session,
    user: User,
    product: MonitoredProduct,
    merchant_name: str,
    old_price: float,
    new_price: float,
    threshold: float,
) -> bool:
    from app.services.email_service import send_price_alert_email

    sent = await send_price_alert_email(
        to_email=user.email,
        product_name=product.product_name or "",
        sku=product.sku,
        platform=product.platform,
        merchant_name=merchant_name,
        old_price=old_price,
        new_price=new_price,
        threshold=threshold,
    )

    alert = AlertLog(
        user_id=user.id,
        product_id=product.id,
        alert_type="price_change",
        old_value=f"{old_price:.2f}",
        new_value=f"{new_price:.2f}",
        email_sent=sent,
    )
    db.add(alert)
    db.commit()
    return sent


async def _send_campaign_alert(
    db: Session,
    user: User,
    product: MonitoredProduct,
    merchant_name: str,
    campaign_price: float,
    threshold: float,
) -> bool:
    from app.services.email_service import send_campaign_alert_email

    sent = await send_campaign_alert_email(
        to_email=user.email,
        product_name=product.product_name or "",
        sku=product.sku,
        platform=product.platform,
        merchant_name=merchant_name,
        campaign_price=campaign_price,
        threshold=threshold,
    )

    alert = AlertLog(
        user_id=user.id,
        product_id=product.id,
        alert_type="campaign_alert",
        old_value="",
        new_value=f"{campaign_price:.2f}",
        email_sent=sent,
    )
    db.add(alert)
    db.commit()
    return sent


async def _send_buybox_alert(
    db: Session,
    user: User,
    product: MonitoredProduct,
    old_winner: str,
    new_winner: str,
    new_price: float,
) -> bool:
    from app.services.email_service import send_buybox_lost_email

    sent = await send_buybox_lost_email(
        to_email=user.email,
        product_name=product.product_name or "",
        sku=product.sku,
        platform=product.platform,
        old_winner=old_winner,
        new_winner=new_winner,
        new_winner_price=new_price,
    )

    alert = AlertLog(
        user_id=user.id,
        product_id=product.id,
        alert_type="buybox_lost",
        old_value=old_winner,
        new_value=new_winner,
        email_sent=sent,
    )
    db.add(alert)
    db.commit()
    return sent
