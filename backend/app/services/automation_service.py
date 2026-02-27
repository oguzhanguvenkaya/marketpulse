"""Kirmizi Cizgi Otomasyon Servisi — Actionable Rules Engine.

Urun/magaza bazli minimum kar marji kurali, fiyat savaslarinda dry-run,
otomatik aksiyon (kampanyaya katil/cekil), if/then kural motoru.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.db.models import (
    User,
    MonitoredProduct,
    SellerSnapshot,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# Kural tipleri
RULE_TYPES = {
    "min_profit_margin": {
        "name": "Minimum Kar Marji",
        "description": "Kar marji belirtilen yuzdenin altina dustugunde tetiklenir",
        "params": ["min_margin_pct"],
        "actions": ["alert", "pause_campaign", "adjust_price"],
    },
    "price_war_protection": {
        "name": "Fiyat Savasi Korumasi",
        "description": "Rakipler fiyat kirdiginda tetiklenir",
        "params": ["max_follow_discount_pct", "min_price"],
        "actions": ["alert", "hold_price", "match_price"],
    },
    "buybox_recovery": {
        "name": "Buybox Kurtarma",
        "description": "Buybox kaybedildiginde otomatik fiyat ayarlama",
        "params": ["max_discount_pct", "min_profit_after"],
        "actions": ["alert", "match_winner_price", "undercut_by_amount"],
    },
    "campaign_auto_join": {
        "name": "Otomatik Kampanya Katilimi",
        "description": "Karliysa kampanyaya otomatik katil",
        "params": ["min_net_profit"],
        "actions": ["alert", "auto_join", "dry_run"],
    },
    "stock_alert": {
        "name": "Stok Uyarisi",
        "description": "Stok belirli seviyenin altina dustugunde uyar",
        "params": ["min_stock_count"],
        "actions": ["alert"],
    },
}


class AutomationService:
    """Otomasyon kural motoru."""

    def get_rule_types(self) -> list[dict]:
        """Kullanilabilir kural tiplerini dondur."""
        return [
            {"type": key, **info}
            for key, info in RULE_TYPES.items()
        ]

    async def create_rule(
        self,
        user: User,
        db: Session,
        rule_type: str,
        name: str,
        params: dict,
        action: str,
        product_ids: Optional[list[str]] = None,
        platform: Optional[str] = None,
        is_active: bool = True,
    ) -> dict:
        """Yeni otomasyon kurali olustur."""
        if rule_type not in RULE_TYPES:
            return {"error": f"Bilinmeyen kural tipi: {rule_type}"}

        type_info = RULE_TYPES[rule_type]
        if action not in type_info["actions"]:
            return {"error": f"Gecersiz aksiyon: {action}. Gecerli: {type_info['actions']}"}

        # Kural verisi (DB'ye kaydedilecek — simdilik in-memory)
        rule = {
            "id": str(uuid.uuid4()),
            "user_id": str(user.id),
            "rule_type": rule_type,
            "name": name,
            "params": params,
            "action": action,
            "product_ids": product_ids,
            "platform": platform,
            "is_active": is_active,
            "created_at": datetime.utcnow().isoformat(),
            "trigger_count": 0,
            "last_triggered_at": None,
        }

        # TODO: DB'ye kaydet (AutomationRule modeli Faz 4'te eklenecek)
        return {
            "success": True,
            "rule": rule,
            "mesaj": f"Kural olusturuldu: {name}",
        }

    async def evaluate_rules(self, user: User, db: Session) -> list[dict]:
        """Tum aktif kurallari degerlendir ve tetiklenmesi gerekenleri dondur.

        Bu method scheduler loop icerisinden cagirilir.
        """
        # TODO: DB'den kuralları cek
        # Simdilik bos liste dondur
        triggered = []
        return triggered

    async def dry_run_price_war(
        self,
        user: User,
        db: Session,
        product_id: str,
        scenario: str = "match_lowest",
    ) -> dict:
        """Fiyat savasi dry-run simulasyonu.

        Scenariolar:
        - match_lowest: En dusuk fiyata esle
        - undercut_1: 1 TL altina in
        - hold: Fiyati koru, karlilik hesapla
        """
        product = db.query(MonitoredProduct).filter(
            MonitoredProduct.id == product_id,
            MonitoredProduct.user_id == user.id,
        ).first()

        if not product:
            return {"error": "Urun bulunamadi"}

        # Son snapshot'lari al
        latest_snapshots = db.query(SellerSnapshot).filter(
            SellerSnapshot.monitored_product_id == product.id,
        ).order_by(desc(SellerSnapshot.snapshot_date)).limit(20).all()

        if not latest_snapshots:
            return {"error": "Fiyat verisi bulunamadi"}

        # Fiyatlari sirala
        prices = sorted(
            [
                {
                    "merchant": s.merchant_name,
                    "price": float(s.price),
                    "buybox_order": s.buybox_order,
                    "campaign_price": float(s.campaign_price) if s.campaign_price else None,
                }
                for s in latest_snapshots
            ],
            key=lambda x: x["price"],
        )

        lowest_price = prices[0]["price"] if prices else 0
        my_price = float(product.threshold_price) if product.threshold_price else (
            prices[0]["price"] if prices else 0
        )
        unit_cost = float(product.unit_cost) if product.unit_cost else 0
        shipping_cost = float(product.shipping_cost) if product.shipping_cost else 0
        commission_rate = 0.12

        # Senaryo simulasyonu
        scenarios = {}

        # Match lowest
        match_price = lowest_price
        match_commission = match_price * commission_rate
        match_profit = match_price - unit_cost - shipping_cost - match_commission
        scenarios["match_lowest"] = {
            "new_price": round(match_price, 2),
            "commission": round(match_commission, 2),
            "net_profit": round(match_profit, 2),
            "profit_margin_pct": round(match_profit / match_price * 100, 1) if match_price > 0 else 0,
            "is_profitable": match_profit > 0,
        }

        # Undercut by 1 TL
        undercut_price = max(lowest_price - 1, 0)
        undercut_commission = undercut_price * commission_rate
        undercut_profit = undercut_price - unit_cost - shipping_cost - undercut_commission
        scenarios["undercut_1"] = {
            "new_price": round(undercut_price, 2),
            "commission": round(undercut_commission, 2),
            "net_profit": round(undercut_profit, 2),
            "profit_margin_pct": round(undercut_profit / undercut_price * 100, 1) if undercut_price > 0 else 0,
            "is_profitable": undercut_profit > 0,
        }

        # Hold current price
        hold_commission = my_price * commission_rate
        hold_profit = my_price - unit_cost - shipping_cost - hold_commission
        scenarios["hold"] = {
            "new_price": round(my_price, 2),
            "commission": round(hold_commission, 2),
            "net_profit": round(hold_profit, 2),
            "profit_margin_pct": round(hold_profit / my_price * 100, 1) if my_price > 0 else 0,
            "is_profitable": hold_profit > 0,
            "buybox_risk": "high" if my_price > lowest_price * 1.05 else "low",
        }

        # Break-even fiyat hesapla
        break_even_price = (unit_cost + shipping_cost) / (1 - commission_rate) if commission_rate < 1 else 0

        return {
            "product": {
                "name": product.product_name or product.sku,
                "sku": product.sku,
                "platform": product.platform,
                "unit_cost": unit_cost,
                "shipping_cost": shipping_cost,
            },
            "current_market": {
                "lowest_price": lowest_price,
                "seller_count": len(prices),
                "sellers": prices[:5],
            },
            "scenarios": scenarios,
            "break_even_price": round(break_even_price, 2),
            "recommended_scenario": scenario,
        }

    async def get_automation_logs(
        self, user: User, db: Session, limit: int = 50
    ) -> list[dict]:
        """Otomasyon log'larini dondur."""
        # TODO: AutomationLog modelinden cek
        return []


automation_service = AutomationService()
