"""Stripe entegrasyon servisi — checkout, webhook, subscription yönetimi."""

import stripe
import logging
from app.core.config import settings
from app.db.models import User, Subscription
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

PLAN_CONFIG = {
    "free": {"sku_limit": 10, "scan_frequency": 1, "price_id": None},
    "starter": {"sku_limit": 200, "scan_frequency": 2, "price_id": None},  # Runtime'da settings'ten
    "pro": {"sku_limit": 1000, "scan_frequency": 4, "price_id": None},
    "enterprise": {"sku_limit": 999999, "scan_frequency": 24, "price_id": None},
}


def _init_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    PLAN_CONFIG["starter"]["price_id"] = settings.STRIPE_PRICE_STARTER
    PLAN_CONFIG["pro"]["price_id"] = settings.STRIPE_PRICE_PRO
    PLAN_CONFIG["enterprise"]["price_id"] = settings.STRIPE_PRICE_ENTERPRISE


def get_or_create_stripe_customer(user: User, db: Session) -> str:
    """Kullanıcının Stripe customer'ını bul veya oluştur."""
    _init_stripe()
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if sub and sub.stripe_customer_id:
        return sub.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name or "",
        metadata={"user_id": str(user.id)}
    )

    if not sub:
        sub = Subscription(
            user_id=user.id,
            plan_tier="free",
            status="active",
            stripe_customer_id=customer.id,
            sku_limit=PLAN_CONFIG["free"]["sku_limit"],
            scan_frequency=PLAN_CONFIG["free"]["scan_frequency"],
        )
        db.add(sub)
    else:
        sub.stripe_customer_id = customer.id
    db.commit()
    db.refresh(sub)
    return customer.id


def create_checkout_session(user: User, plan_tier: str, db: Session, success_url: str, cancel_url: str) -> str:
    """Stripe Checkout Session oluştur ve URL döndür."""
    _init_stripe()

    if plan_tier not in PLAN_CONFIG or plan_tier == "free":
        raise ValueError(f"Geçersiz plan: {plan_tier}")

    price_id = PLAN_CONFIG[plan_tier]["price_id"]
    if not price_id:
        raise ValueError(f"{plan_tier} planı için Stripe Price ID ayarlanmamış")

    customer_id = get_or_create_stripe_customer(user, db)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id), "plan_tier": plan_tier},
    )
    return session.url


def create_billing_portal_session(user: User, db: Session, return_url: str) -> str:
    """Stripe Billing Portal URL döndür (plan yönetimi)."""
    _init_stripe()
    customer_id = get_or_create_stripe_customer(user, db)
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def handle_webhook_event(payload: bytes, sig_header: str, db: Session) -> dict:
    """Stripe webhook event'ini işle."""
    _init_stripe()

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise ValueError("Geçersiz webhook imzası")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data, db)
    elif event_type == "invoice.paid":
        _handle_invoice_paid(data, db)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        _handle_subscription_change(data, db)

    return {"status": "ok", "type": event_type}


def _handle_checkout_completed(session_data: dict, db: Session):
    """Checkout tamamlandığında subscription oluştur/güncelle."""
    customer_id = session_data.get("customer")
    subscription_id = session_data.get("subscription")
    plan_tier = session_data.get("metadata", {}).get("plan_tier", "starter")

    sub = db.query(Subscription).filter(Subscription.stripe_customer_id == customer_id).first()
    if sub:
        sub.stripe_subscription_id = subscription_id
        sub.plan_tier = plan_tier
        sub.status = "active"
        sub.sku_limit = PLAN_CONFIG.get(plan_tier, {}).get("sku_limit", 10)
        sub.scan_frequency = PLAN_CONFIG.get(plan_tier, {}).get("scan_frequency", 1)

        # User'ın plan_tier'ını da güncelle
        user = db.query(User).filter(User.id == sub.user_id).first()
        if user:
            user.plan_tier = plan_tier

        db.commit()
        logger.info(f"Subscription activated: customer={customer_id}, plan={plan_tier}")


def _handle_invoice_paid(invoice_data: dict, db: Session):
    """Fatura ödendiğinde subscription'ı aktif tut."""
    customer_id = invoice_data.get("customer")
    sub = db.query(Subscription).filter(Subscription.stripe_customer_id == customer_id).first()
    if sub:
        sub.status = "active"
        db.commit()


def _handle_subscription_change(sub_data: dict, db: Session):
    """Subscription güncellendiğinde veya iptal edildiğinde."""
    stripe_sub_id = sub_data.get("id")
    status = sub_data.get("status")  # active, canceled, past_due, unpaid

    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_sub_id).first()
    if not sub:
        return

    if status in ("canceled", "unpaid"):
        sub.status = "canceled"
        sub.plan_tier = "free"
        sub.sku_limit = PLAN_CONFIG["free"]["sku_limit"]
        sub.scan_frequency = PLAN_CONFIG["free"]["scan_frequency"]

        user = db.query(User).filter(User.id == sub.user_id).first()
        if user:
            user.plan_tier = "free"
    elif status == "past_due":
        sub.status = "past_due"
    elif status == "active":
        sub.status = "active"

    db.commit()
    logger.info(f"Subscription updated: id={stripe_sub_id}, status={status}")


def get_plan_limits(plan_tier: str) -> dict:
    """Plan limitleri döndür."""
    config = PLAN_CONFIG.get(plan_tier, PLAN_CONFIG["free"])
    return {
        "plan_tier": plan_tier,
        "sku_limit": config["sku_limit"],
        "scan_frequency": config["scan_frequency"],
    }
