"""Kampanya Firsat Merkezi (Opportunity Hub) Servisi.

HB/TY Promotions API'lerinden aktif kampanyalari cekme,
AI onerisi ve karlilik simulasyonu entegrasyonu.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User, MonitoredProduct, SellerSnapshot

logger = logging.getLogger(__name__)


# Ornek kampanya verileri (gercek API entegrasyonunda bunlar API'den gelecek)
SAMPLE_CAMPAIGNS = {
    "hepsiburada": [
        {
            "id": "hb_camp_1",
            "name": "Hafta Sonu Indirimi",
            "type": "discount",
            "discount_rate": 10,
            "start_date": "2026-02-28",
            "end_date": "2026-03-02",
            "categories": ["Elektronik", "Telefon"],
            "min_discount_rate": 5,
            "status": "active",
        },
        {
            "id": "hb_camp_2",
            "name": "Sepette %15 Indirim",
            "type": "cart_discount",
            "discount_rate": 15,
            "start_date": "2026-02-27",
            "end_date": "2026-03-05",
            "categories": ["Ev & Yasam", "Mutfak"],
            "min_discount_rate": 10,
            "status": "active",
        },
        {
            "id": "hb_camp_3",
            "name": "Ucretsiz Kargo Kampanyasi",
            "type": "free_shipping",
            "discount_rate": 0,
            "start_date": "2026-03-01",
            "end_date": "2026-03-07",
            "categories": [],
            "min_discount_rate": 0,
            "status": "upcoming",
        },
    ],
    "trendyol": [
        {
            "id": "ty_camp_1",
            "name": "Satis Kampanyasi",
            "type": "discount",
            "discount_rate": 20,
            "start_date": "2026-02-27",
            "end_date": "2026-03-03",
            "categories": ["Kisisel Bakim", "Kozmetik"],
            "min_discount_rate": 15,
            "status": "active",
        },
        {
            "id": "ty_camp_2",
            "name": "Flash Sale",
            "type": "flash_sale",
            "discount_rate": 30,
            "start_date": "2026-03-01",
            "end_date": "2026-03-01",
            "categories": ["Elektronik"],
            "min_discount_rate": 20,
            "status": "upcoming",
        },
    ],
}


class CampaignService:
    """Kampanya Firsat Merkezi servisi."""

    async def get_available_campaigns(
        self,
        user: User,
        db: Session,
        platform: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """Kullanilabilir kampanyalari listele.

        Gercek entegrasyonda HB/TY API'lerinden cekilecek.
        Simdilik ornek veri donuyor.
        """
        campaigns = []

        platforms = [platform] if platform else ["hepsiburada", "trendyol"]

        for p in platforms:
            platform_campaigns = SAMPLE_CAMPAIGNS.get(p, [])
            for camp in platform_campaigns:
                if status and camp["status"] != status:
                    continue
                camp_copy = {**camp, "platform": p}
                campaigns.append(camp_copy)

        return {
            "total": len(campaigns),
            "campaigns": campaigns,
        }

    async def analyze_campaign_opportunity(
        self,
        user: User,
        db: Session,
        campaign_id: str,
        product_id: Optional[str] = None,
    ) -> dict:
        """Kampanya firsati analizi — bir urun icin kampanyaya katilim simulasyonu.

        Karlilik etkisini hesaplar, AI onerisi uretir.
        """
        # Kampanya bul
        campaign = None
        campaign_platform = None
        for platform, camps in SAMPLE_CAMPAIGNS.items():
            for camp in camps:
                if camp["id"] == campaign_id:
                    campaign = camp
                    campaign_platform = platform
                    break

        if not campaign:
            return {"error": f"Kampanya bulunamadi: {campaign_id}"}

        # Urun varsa karlilik simulasyonu
        profitability_impact = None
        if product_id:
            product = db.query(MonitoredProduct).filter(
                MonitoredProduct.id == product_id,
                MonitoredProduct.user_id == user.id,
            ).first()

            if product:
                # Son fiyat
                latest_snapshot = db.query(SellerSnapshot).filter(
                    SellerSnapshot.monitored_product_id == product.id,
                    SellerSnapshot.buybox_order == 1,
                ).order_by(desc(SellerSnapshot.snapshot_date)).first()

                if latest_snapshot:
                    current_price = float(latest_snapshot.price)
                    discount_rate = campaign.get("discount_rate", 0)
                    campaign_price = current_price * (1 - discount_rate / 100)

                    unit_cost = float(product.unit_cost) if product.unit_cost else 0
                    shipping_cost = float(product.shipping_cost) if product.shipping_cost else 0

                    # Komisyon tahmini (%12 default)
                    commission_rate = 0.12
                    commission = campaign_price * commission_rate

                    net_profit_before = current_price - unit_cost - shipping_cost - (current_price * commission_rate)
                    net_profit_after = campaign_price - unit_cost - shipping_cost - commission

                    profitability_impact = {
                        "product_name": product.product_name or product.sku,
                        "current_price": current_price,
                        "campaign_price": round(campaign_price, 2),
                        "discount_rate": discount_rate,
                        "unit_cost": unit_cost,
                        "shipping_cost": shipping_cost,
                        "commission": round(commission, 2),
                        "net_profit_before": round(net_profit_before, 2),
                        "net_profit_after": round(net_profit_after, 2),
                        "profit_change": round(net_profit_after - net_profit_before, 2),
                        "is_profitable": net_profit_after > 0,
                    }

        # AI onerisi (basit rule-based, ileride LLM ile)
        recommendation = self._generate_recommendation(campaign, profitability_impact)

        return {
            "campaign": {**campaign, "platform": campaign_platform},
            "profitability_impact": profitability_impact,
            "recommendation": recommendation,
        }

    def _generate_recommendation(self, campaign: dict, profitability: Optional[dict]) -> dict:
        """Kampanya onerisi olustur."""
        score = 50  # Base score

        reasons = []

        if campaign["status"] == "active":
            score += 10
            reasons.append("Kampanya aktif — hemen katilabilirsiniz")

        if campaign["type"] == "free_shipping":
            score += 15
            reasons.append("Ucretsiz kargo kampanyasi — maliyet artisi yok")

        if campaign.get("discount_rate", 0) <= 10:
            score += 10
            reasons.append("Dusuk indirim orani — kar marjina etkisi sinirli")
        elif campaign.get("discount_rate", 0) >= 25:
            score -= 15
            reasons.append("Yuksek indirim orani — kar marjini dikkatli degerlendirin")

        if profitability:
            if profitability["is_profitable"]:
                score += 20
                reasons.append(f"Kampanya sonrasi net kar: {profitability['net_profit_after']:.2f} TL")
            else:
                score -= 30
                reasons.append(f"UYARI: Kampanya sonrasi zarar: {profitability['net_profit_after']:.2f} TL")

            if profitability.get("profit_change", 0) > -5:
                score += 5
            else:
                score -= 10
                reasons.append(f"Kar kaybi: {abs(profitability['profit_change']):.2f} TL")

        score = max(0, min(100, score))

        if score >= 70:
            action = "katil"
            label = "Onerilen"
        elif score >= 40:
            action = "degerlendir"
            label = "Dikkatli Degerlendirin"
        else:
            action = "katilma"
            label = "Onerilmiyor"

        return {
            "score": score,
            "action": action,
            "label": label,
            "reasons": reasons,
        }

    async def get_campaign_history(
        self, user: User, db: Session, product_id: Optional[str] = None
    ) -> dict:
        """Kampanya gecmisi — onceki katilimlar."""
        # SellerSnapshot'lardaki campaign_info verisi
        query = db.query(SellerSnapshot).join(MonitoredProduct).filter(
            MonitoredProduct.user_id == user.id,
            SellerSnapshot.campaign_info.isnot(None),
        )

        if product_id:
            query = query.filter(MonitoredProduct.id == product_id)

        snapshots = query.order_by(desc(SellerSnapshot.snapshot_date)).limit(50).all()

        history = []
        for s in snapshots:
            history.append({
                "product_id": str(s.monitored_product_id),
                "merchant_name": s.merchant_name,
                "campaign_info": s.campaign_info,
                "campaign_price": float(s.campaign_price) if s.campaign_price else None,
                "regular_price": float(s.price),
                "date": s.snapshot_date.isoformat() if s.snapshot_date else None,
            })

        return {
            "total": len(history),
            "history": history,
        }


campaign_service = CampaignService()
