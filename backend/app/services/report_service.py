"""Raporlama servisi — haftalik ozet, fiyat degisim, rakip analiz raporlari.

Email ile PDF veya HTML rapor gonderir.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.db.models import (
    User,
    MonitoredProduct,
    SellerSnapshot,
    CompetitorSeller,
    CompetitorProduct,
    AlertLog,
    SearchTask,
)
from app.services.email_service import send_email

logger = logging.getLogger(__name__)


class ReportService:
    """Kullanici raporlari olusturma ve gonderme servisi."""

    async def generate_weekly_summary(self, user: User, db: Session) -> dict:
        """Haftalik ozet rapor verisi olustur."""
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)

        # Izlenen urun sayisi
        total_products = db.query(func.count(MonitoredProduct.id)).filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.is_active == True,
        ).scalar() or 0

        # Platform dagilimi
        platform_counts = db.query(
            MonitoredProduct.platform,
            func.count(MonitoredProduct.id),
        ).filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.is_active == True,
        ).group_by(MonitoredProduct.platform).all()

        # Bu haftaki alarm sayisi
        alert_count = db.query(func.count(AlertLog.id)).filter(
            AlertLog.user_id == user.id,
            AlertLog.created_at >= week_ago,
        ).scalar() or 0

        # En cok fiyat dusurumu
        price_drops = self._get_price_changes(db, user.id, week_ago, direction="drop", limit=5)

        # En cok fiyat artisi
        price_increases = self._get_price_changes(db, user.id, week_ago, direction="increase", limit=5)

        # Buybox degisiklikleri
        buybox_changes = self._get_buybox_changes(db, user.id, week_ago, limit=5)

        # Arama sayisi
        search_count = db.query(func.count(SearchTask.id)).filter(
            SearchTask.user_id == user.id,
            SearchTask.created_at >= week_ago,
        ).scalar() or 0

        # Rakip ozet
        competitor_count = db.query(func.count(CompetitorSeller.id)).filter(
            CompetitorSeller.user_id == user.id,
            CompetitorSeller.is_active == True,
        ).scalar() or 0

        return {
            "period": {"start": week_ago.isoformat(), "end": now.isoformat()},
            "total_products": total_products,
            "platform_distribution": {p: c for p, c in platform_counts},
            "alert_count": alert_count,
            "search_count": search_count,
            "competitor_count": competitor_count,
            "price_drops": price_drops,
            "price_increases": price_increases,
            "buybox_changes": buybox_changes,
        }

    def _get_price_changes(
        self, db: Session, user_id, since: datetime, direction: str = "drop", limit: int = 5
    ) -> list[dict]:
        """Fiyat degisimlerini hesapla."""
        products = db.query(MonitoredProduct).filter(
            MonitoredProduct.user_id == user_id,
            MonitoredProduct.is_active == True,
        ).all()

        changes = []
        for product in products:
            # Son ve onceki snapshot'lari al (buybox=1)
            recent_snapshot = db.query(SellerSnapshot).filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.buybox_order == 1,
            ).order_by(desc(SellerSnapshot.snapshot_date)).first()

            old_snapshot = db.query(SellerSnapshot).filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.buybox_order == 1,
                SellerSnapshot.snapshot_date <= since,
            ).order_by(desc(SellerSnapshot.snapshot_date)).first()

            if not recent_snapshot or not old_snapshot:
                continue
            if recent_snapshot.price is None or old_snapshot.price is None:
                continue

            old_price = float(old_snapshot.price)
            new_price = float(recent_snapshot.price)
            if old_price == 0:
                continue

            change_pct = ((new_price - old_price) / old_price) * 100

            if direction == "drop" and change_pct < -1:
                changes.append({
                    "product_name": product.product_name or product.sku,
                    "sku": product.sku,
                    "platform": product.platform,
                    "old_price": old_price,
                    "new_price": new_price,
                    "change_pct": round(change_pct, 1),
                })
            elif direction == "increase" and change_pct > 1:
                changes.append({
                    "product_name": product.product_name or product.sku,
                    "sku": product.sku,
                    "platform": product.platform,
                    "old_price": old_price,
                    "new_price": new_price,
                    "change_pct": round(change_pct, 1),
                })

        changes.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        return changes[:limit]

    def _get_buybox_changes(self, db: Session, user_id, since: datetime, limit: int = 5) -> list[dict]:
        """Buybox degisikliklerini bul."""
        alerts = db.query(AlertLog).filter(
            AlertLog.user_id == user_id,
            AlertLog.alert_type == "buybox_lost",
            AlertLog.created_at >= since,
        ).order_by(desc(AlertLog.created_at)).limit(limit).all()

        return [
            {
                "alert_type": a.alert_type,
                "old_value": a.old_value,
                "new_value": a.new_value,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ]

    async def send_weekly_report_email(self, user: User, db: Session) -> bool:
        """Haftalik ozet raporunu email ile gonder."""
        report = await self.generate_weekly_summary(user, db)

        # HTML olustur
        html = self._build_weekly_report_html(user, report)
        subject = f"MarketPulse Haftalik Rapor — {report['period']['start'][:10]}"

        return await send_email(user.email, subject, html)

    def _build_weekly_report_html(self, user: User, report: dict) -> str:
        """Haftalik rapor HTML'i olustur."""
        platform_rows = ""
        for platform, count in report.get("platform_distribution", {}).items():
            platform_rows += f"<tr><td style='padding:6px 8px;color:#6b7280;'>{platform.capitalize()}</td><td style='padding:6px 8px;font-weight:600;text-align:right;'>{count}</td></tr>"

        drop_rows = ""
        for item in report.get("price_drops", []):
            drop_rows += f"""
            <tr>
                <td style='padding:6px 8px;'>{item['product_name'][:40]}</td>
                <td style='padding:6px 8px;text-align:right;'>{item['old_price']:.2f} TL</td>
                <td style='padding:6px 8px;text-align:right;color:#16a34a;font-weight:600;'>{item['new_price']:.2f} TL</td>
                <td style='padding:6px 8px;text-align:right;color:#16a34a;'>%{abs(item['change_pct']):.1f}</td>
            </tr>"""

        increase_rows = ""
        for item in report.get("price_increases", []):
            increase_rows += f"""
            <tr>
                <td style='padding:6px 8px;'>{item['product_name'][:40]}</td>
                <td style='padding:6px 8px;text-align:right;'>{item['old_price']:.2f} TL</td>
                <td style='padding:6px 8px;text-align:right;color:#dc2626;font-weight:600;'>{item['new_price']:.2f} TL</td>
                <td style='padding:6px 8px;text-align:right;color:#dc2626;'>+%{item['change_pct']:.1f}</td>
            </tr>"""

        return f"""
        <div style="font-family:'Inter',Arial,sans-serif;max-width:700px;margin:0 auto;padding:20px;background:#f9fafb;">
            <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);border-radius:12px;padding:24px;margin-bottom:20px;color:#fff;">
                <h1 style="margin:0 0 4px;font-size:22px;">Haftalik Rapor</h1>
                <p style="margin:0;opacity:0.9;font-size:14px;">{report['period']['start'][:10]} - {report['period']['end'][:10]}</p>
            </div>

            <div style="display:flex;gap:12px;margin-bottom:20px;">
                <div style="flex:1;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px;text-align:center;">
                    <div style="font-size:28px;font-weight:700;color:#1e40af;">{report['total_products']}</div>
                    <div style="font-size:12px;color:#6b7280;">Izlenen Urun</div>
                </div>
                <div style="flex:1;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px;text-align:center;">
                    <div style="font-size:28px;font-weight:700;color:#dc2626;">{report['alert_count']}</div>
                    <div style="font-size:12px;color:#6b7280;">Alarm</div>
                </div>
                <div style="flex:1;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px;text-align:center;">
                    <div style="font-size:28px;font-weight:700;color:#7c3aed;">{report['search_count']}</div>
                    <div style="font-size:12px;color:#6b7280;">Arama</div>
                </div>
                <div style="flex:1;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px;text-align:center;">
                    <div style="font-size:28px;font-weight:700;color:#059669;">{report['competitor_count']}</div>
                    <div style="font-size:12px;color:#6b7280;">Rakip</div>
                </div>
            </div>

            {'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin-bottom:16px;"><h3 style="margin:0 0 12px;font-size:14px;color:#166534;">En Cok Fiyat Dusen Urunler</h3><table style="width:100%;border-collapse:collapse;font-size:13px;"><tr style="background:#f0fdf4;"><th style="padding:6px 8px;text-align:left;">Urun</th><th style="padding:6px 8px;text-align:right;">Eski</th><th style="padding:6px 8px;text-align:right;">Yeni</th><th style="padding:6px 8px;text-align:right;">Degisim</th></tr>' + drop_rows + '</table></div>' if drop_rows else ''}

            {'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin-bottom:16px;"><h3 style="margin:0 0 12px;font-size:14px;color:#991b1b;">En Cok Fiyat Artan Urunler</h3><table style="width:100%;border-collapse:collapse;font-size:13px;"><tr style="background:#fef2f2;"><th style="padding:6px 8px;text-align:left;">Urun</th><th style="padding:6px 8px;text-align:right;">Eski</th><th style="padding:6px 8px;text-align:right;">Yeni</th><th style="padding:6px 8px;text-align:right;">Degisim</th></tr>' + increase_rows + '</table></div>' if increase_rows else ''}

            <p style="color:#9ca3af;font-size:11px;text-align:center;margin-top:24px;">
                Bu rapor MarketPulse tarafindan otomatik olusturulmustur.
            </p>
        </div>
        """

    async def generate_price_change_report(
        self, user: User, db: Session, days: int = 7
    ) -> dict:
        """Fiyat degisim raporu."""
        since = datetime.utcnow() - timedelta(days=days)
        drops = self._get_price_changes(db, user.id, since, "drop", limit=20)
        increases = self._get_price_changes(db, user.id, since, "increase", limit=20)

        return {
            "period_days": days,
            "total_drops": len(drops),
            "total_increases": len(increases),
            "price_drops": drops,
            "price_increases": increases,
        }

    async def generate_competitor_report(self, user: User, db: Session) -> dict:
        """Rakip analiz raporu."""
        competitors = db.query(CompetitorSeller).filter(
            CompetitorSeller.user_id == user.id,
            CompetitorSeller.is_active == True,
        ).all()

        result = []
        for comp in competitors:
            product_count = db.query(func.count(CompetitorProduct.id)).filter(
                CompetitorProduct.competitor_id == comp.id,
            ).scalar() or 0

            avg_price = db.query(func.avg(CompetitorProduct.price)).filter(
                CompetitorProduct.competitor_id == comp.id,
                CompetitorProduct.price.isnot(None),
            ).scalar()

            result.append({
                "seller_name": comp.seller_name,
                "platform": comp.platform,
                "product_count": product_count,
                "avg_price": round(float(avg_price), 2) if avg_price else None,
                "rating": comp.seller_rating,
                "last_checked": comp.last_checked_at.isoformat() if comp.last_checked_at else None,
            })

        return {
            "total_competitors": len(result),
            "competitors": result,
        }

    async def generate_buybox_report(self, user: User, db: Session, days: int = 7) -> dict:
        """Buybox performans raporu."""
        since = datetime.utcnow() - timedelta(days=days)

        products = db.query(MonitoredProduct).filter(
            MonitoredProduct.user_id == user.id,
            MonitoredProduct.is_active == True,
        ).all()

        buybox_stats = []
        for product in products:
            snapshots = db.query(SellerSnapshot).filter(
                SellerSnapshot.monitored_product_id == product.id,
                SellerSnapshot.snapshot_date >= since,
                SellerSnapshot.buybox_order == 1,
            ).order_by(SellerSnapshot.snapshot_date).all()

            if not snapshots:
                continue

            winners = {}
            for s in snapshots:
                name = s.merchant_name or "Bilinmiyor"
                winners[name] = winners.get(name, 0) + 1

            total = len(snapshots)
            buybox_stats.append({
                "product_name": product.product_name or product.sku,
                "sku": product.sku,
                "platform": product.platform,
                "total_snapshots": total,
                "winner_distribution": {
                    name: {"count": count, "percentage": round(count / total * 100, 1)}
                    for name, count in sorted(winners.items(), key=lambda x: -x[1])
                },
            })

        return {
            "period_days": days,
            "total_products_tracked": len(buybox_stats),
            "products": buybox_stats,
        }


report_service = ReportService()
