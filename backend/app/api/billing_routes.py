"""Billing / Subscription API endpoint'leri."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User, Subscription
from app.core.auth import get_current_user
from app.services.stripe_service import (
    create_checkout_session,
    create_billing_portal_session,
    handle_webhook_event,
    get_plan_limits,
    PLAN_CONFIG,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["Billing"])


class CheckoutRequest(BaseModel):
    plan_tier: str  # starter, pro, enterprise
    success_url: str = ""
    cancel_url: str = ""


class BillingPortalRequest(BaseModel):
    return_url: str = ""


@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stripe Checkout Session oluştur."""
    if req.plan_tier not in ("starter", "pro", "enterprise"):
        raise HTTPException(status_code=400, detail="Geçersiz plan tipi")

    # Default URL'ler
    success_url = req.success_url or "{origin}/settings?payment=success"
    cancel_url = req.cancel_url or "{origin}/settings?payment=canceled"

    try:
        url = create_checkout_session(user, req.plan_tier, db, success_url, cancel_url)
        return {"checkout_url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Checkout session oluşturma hatası: {e}")
        raise HTTPException(status_code=500, detail="Ödeme sayfası oluşturulamadı")


@router.post("/portal")
async def create_portal(
    req: BillingPortalRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stripe Billing Portal URL döndür."""
    return_url = req.return_url or "{origin}/settings"
    try:
        url = create_billing_portal_session(user, db, return_url)
        return {"portal_url": url}
    except Exception as e:
        logger.error(f"Portal session oluşturma hatası: {e}")
        raise HTTPException(status_code=500, detail="Portal sayfası oluşturulamadı")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe webhook handler — signature doğrulama ile."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        result = handle_webhook_event(payload, sig_header, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Webhook işleme hatası: {e}")
        raise HTTPException(status_code=500, detail="Webhook işlenemedi")


@router.get("/subscription")
async def get_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının mevcut abonelik bilgisi."""
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()

    plan_tier = sub.plan_tier if sub else "free"
    limits = get_plan_limits(plan_tier)

    # Mevcut SKU sayısını hesapla
    from app.db.models import MonitoredProduct
    current_sku_count = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user.id,
        MonitoredProduct.is_active == True,
    ).count()

    return {
        "plan_tier": plan_tier,
        "status": sub.status if sub else "active",
        "sku_limit": limits["sku_limit"],
        "scan_frequency": limits["scan_frequency"],
        "current_sku_count": current_sku_count,
        "stripe_subscription_id": sub.stripe_subscription_id if sub else None,
        "created_at": sub.created_at.isoformat() if sub and sub.created_at else None,
    }


@router.get("/plans")
async def get_plans():
    """Mevcut plan seçenekleri."""
    return {
        "plans": [
            {
                "tier": "free",
                "name": "Ucretsiz",
                "price_monthly": 0,
                "currency": "TRY",
                "sku_limit": 10,
                "scan_frequency": "Gunde 1x",
                "platforms": "1 platform",
                "history_days": 7,
                "email_alerts": False,
                "export": False,
                "features": ["10 SKU takibi", "Gunluk 1x tarama", "7 gun gecmis"],
            },
            {
                "tier": "starter",
                "name": "Starter",
                "price_monthly": 299,
                "currency": "TRY",
                "sku_limit": 200,
                "scan_frequency": "Gunde 2x",
                "platforms": "HB + Trendyol",
                "history_days": 30,
                "email_alerts": True,
                "email_alert_limit": 10,
                "export": "JSON",
                "features": ["200 SKU takibi", "Gunde 2x otomatik tarama", "30 gun gecmis", "10 email alarm/gun", "JSON export"],
            },
            {
                "tier": "pro",
                "name": "Pro",
                "price_monthly": 899,
                "currency": "TRY",
                "sku_limit": 1000,
                "scan_frequency": "Gunde 4x",
                "platforms": "Tum platformlar",
                "history_days": 90,
                "email_alerts": True,
                "email_alert_limit": None,
                "export": "JSON + CSV",
                "webhook": True,
                "features": ["1.000 SKU takibi", "Gunde 4x otomatik tarama", "90 gun gecmis", "Sinırsız email alarm", "JSON + CSV export", "Webhook destegi"],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price_monthly": None,
                "currency": "TRY",
                "sku_limit": None,
                "scan_frequency": "Saatlik",
                "platforms": "Tum platformlar",
                "history_days": None,
                "email_alerts": True,
                "email_alert_limit": None,
                "export": "JSON + CSV + API",
                "webhook": True,
                "features": ["Sınırsız SKU", "Saatlik tarama", "Sınırsız gecmis", "Sınırsız alarm", "API erisimi", "Ozel destek"],
            },
        ]
    }
