"""Trend/Rota Tabanli Reklam Kelimesi Onerisi Servisi.

HB Rota / TY Trend verilerini analiz ederek reklam kelimesi onerir.
Bosa tiklama riski tespiti yapar.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    User,
    MonitoredProduct,
    SearchTask,
    CategoryProduct,
    CategorySession,
)

logger = logging.getLogger(__name__)


class KeywordRecommendationService:
    """Reklam kelimesi oneri servisi."""

    async def get_keyword_recommendations(
        self,
        user: User,
        db: Session,
        product_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """Urun veya magaza icin reklam kelimesi onerileri.

        Veri kaynaklari:
        1. Kullanicinin onceki keyword aramalari
        2. Urunun kategori verileri
        3. Rakip analizi verileri
        """
        recommendations = []

        # 1. Kullanicinin basarili keyword aramalari
        keyword_stats = await self._analyze_keyword_history(user, db, platform)

        # 2. Urun bazli oneri
        product_keywords = []
        if product_id:
            product_keywords = await self._analyze_product_keywords(user, db, product_id)

        # 3. Kategori bazli trend
        category_trends = await self._analyze_category_trends(user, db, platform)

        # Birlestir ve skorla
        all_keywords = {}

        for kw in keyword_stats:
            key = kw["keyword"].lower()
            all_keywords[key] = {
                "keyword": kw["keyword"],
                "source": "search_history",
                "score": kw.get("score", 50),
                "search_count": kw.get("search_count", 0),
                "avg_products": kw.get("avg_products", 0),
                "sponsored_ratio": kw.get("sponsored_ratio", 0),
                "click_waste_risk": "high" if kw.get("sponsored_ratio", 0) > 0.3 else "low",
                "platform": kw.get("platform"),
            }

        for kw in product_keywords:
            key = kw["keyword"].lower()
            if key in all_keywords:
                all_keywords[key]["score"] += 20
                all_keywords[key]["source"] = "product+history"
            else:
                all_keywords[key] = {
                    "keyword": kw["keyword"],
                    "source": "product_analysis",
                    "score": kw.get("score", 40),
                    "relevance": kw.get("relevance", "medium"),
                }

        for kw in category_trends:
            key = kw["keyword"].lower()
            if key in all_keywords:
                all_keywords[key]["score"] += 15
                all_keywords[key]["is_trending"] = True
            else:
                all_keywords[key] = {
                    "keyword": kw["keyword"],
                    "source": "category_trend",
                    "score": kw.get("score", 35),
                    "is_trending": True,
                    "category": kw.get("category"),
                }

        # Skora gore sirala
        sorted_keywords = sorted(all_keywords.values(), key=lambda x: x.get("score", 0), reverse=True)

        return {
            "total": len(sorted_keywords),
            "recommendations": sorted_keywords[:limit],
            "data_sources": {
                "search_history": len(keyword_stats),
                "product_analysis": len(product_keywords),
                "category_trends": len(category_trends),
            },
        }

    async def _analyze_keyword_history(
        self, user: User, db: Session, platform: Optional[str] = None
    ) -> list[dict]:
        """Kullanicinin keyword arama gecmisini analiz et."""
        query = db.query(
            SearchTask.keyword,
            SearchTask.platform,
            func.count(SearchTask.id).label("search_count"),
            func.avg(SearchTask.total_products).label("avg_products"),
            func.avg(SearchTask.total_sponsored_products).label("avg_sponsored"),
        ).filter(
            SearchTask.user_id == user.id,
            SearchTask.status == "completed",
        )

        if platform:
            query = query.filter(SearchTask.platform == platform)

        results = query.group_by(
            SearchTask.keyword, SearchTask.platform
        ).order_by(desc("search_count")).limit(20).all()

        keywords = []
        for r in results:
            avg_products = float(r.avg_products or 0)
            avg_sponsored = float(r.avg_sponsored or 0)
            sponsored_ratio = avg_sponsored / avg_products if avg_products > 0 else 0

            # Skor: arama sayisi + urun hacmi - sponsorlu oran
            score = min(100, int(r.search_count * 10 + avg_products * 0.5 - sponsored_ratio * 30))

            keywords.append({
                "keyword": r.keyword,
                "platform": r.platform,
                "search_count": r.search_count,
                "avg_products": round(avg_products),
                "avg_sponsored": round(avg_sponsored),
                "sponsored_ratio": round(sponsored_ratio, 2),
                "score": max(0, score),
            })

        return keywords

    async def _analyze_product_keywords(
        self, user: User, db: Session, product_id: str
    ) -> list[dict]:
        """Urunun ismi ve kategorisinden keyword onerileri cikar."""
        product = db.query(MonitoredProduct).filter(
            MonitoredProduct.id == product_id,
            MonitoredProduct.user_id == user.id,
        ).first()

        if not product or not product.product_name:
            return []

        keywords = []

        # Urun adindaki kelimeleri cikar
        name = product.product_name
        words = [w.strip().lower() for w in name.split() if len(w.strip()) > 2]

        # 2-3 kelimelik kombinasyonlar
        for i in range(len(words)):
            if i + 1 < len(words):
                bigram = f"{words[i]} {words[i+1]}"
                keywords.append({
                    "keyword": bigram,
                    "score": 45,
                    "relevance": "high",
                    "source_type": "product_name_bigram",
                })

        # Marka + urun tipi
        if product.brand:
            keywords.append({
                "keyword": product.brand.lower(),
                "score": 60,
                "relevance": "high",
                "source_type": "brand",
            })

        return keywords[:10]

    async def _analyze_category_trends(
        self, user: User, db: Session, platform: Optional[str] = None
    ) -> list[dict]:
        """Kategori verilerinden trend keyword'leri cikar."""
        query = db.query(CategorySession).filter(
            CategorySession.user_id == user.id,
            CategorySession.status == "active",
        )
        if platform:
            query = query.filter(CategorySession.platform == platform)

        sessions = query.order_by(desc(CategorySession.created_at)).limit(5).all()

        trends = []
        for session in sessions:
            if session.category_name:
                # Kategori adini keyword olarak onerCategory
                trends.append({
                    "keyword": session.category_name.lower(),
                    "score": 30,
                    "category": session.category_name,
                    "platform": session.platform,
                })

            # Kategori urunlerinden en cok tekrar eden marka/kelime
            products = db.query(CategoryProduct).filter(
                CategoryProduct.session_id == session.id,
            ).limit(40).all()

            brand_counts: dict[str, int] = {}
            for p in products:
                if p.brand:
                    b = p.brand.strip().lower()
                    brand_counts[b] = brand_counts.get(b, 0) + 1

            for brand, count in sorted(brand_counts.items(), key=lambda x: -x[1])[:3]:
                if count >= 3:
                    trends.append({
                        "keyword": brand,
                        "score": 25 + count * 2,
                        "category": session.category_name,
                        "frequency": count,
                    })

        return trends

    async def detect_click_waste_risk(
        self,
        user: User,
        db: Session,
        keyword: str,
        product_id: Optional[str] = None,
    ) -> dict:
        """Bosa tiklama riski tespiti.

        Yanlis kategori + yanlis keyword kombinasyonunu tespit eder.
        """
        # Keyword arama sonuclari
        searches = db.query(SearchTask).filter(
            SearchTask.user_id == user.id,
            SearchTask.keyword == keyword,
            SearchTask.status == "completed",
        ).order_by(desc(SearchTask.created_at)).limit(5).all()

        if not searches:
            return {
                "keyword": keyword,
                "risk_level": "unknown",
                "message": "Bu keyword icin yeterli veri yok — once arama yapin",
            }

        total_products = sum(s.total_products or 0 for s in searches)
        total_sponsored = sum(s.total_sponsored_products or 0 for s in searches)
        avg_products = total_products / len(searches) if searches else 0
        sponsored_ratio = total_sponsored / total_products if total_products > 0 else 0

        risk_factors = []
        risk_score = 0

        # Yuksek sponsorlu oran
        if sponsored_ratio > 0.4:
            risk_factors.append(f"Yuksek sponsorlu oran: %{sponsored_ratio*100:.0f}")
            risk_score += 30

        # Dusuk urun sayisi (keyword cok nicse)
        if avg_products < 10:
            risk_factors.append(f"Dusuk urun hacmi: {avg_products:.0f} urun")
            risk_score += 20

        # Urun varsa kategori uyumu kontrol et
        if product_id:
            product = db.query(MonitoredProduct).filter(
                MonitoredProduct.id == product_id,
                MonitoredProduct.user_id == user.id,
            ).first()

            if product and product.product_name:
                # Basit kelime eslestirme (LLM ile daha iyi yapilabilir)
                product_words = set(product.product_name.lower().split())
                keyword_words = set(keyword.lower().split())
                overlap = product_words & keyword_words
                if not overlap:
                    risk_factors.append("Urun adi ile keyword arasinda kelime eslesmesi yok")
                    risk_score += 25

        risk_score = min(100, risk_score)

        if risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "keyword": keyword,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "stats": {
                "total_searches": len(searches),
                "avg_products": round(avg_products),
                "sponsored_ratio": round(sponsored_ratio, 2),
            },
            "recommendation": (
                "Bu keyword icin reklam vermek riskli — bosa tiklama orani yuksek olabilir"
                if risk_level == "high"
                else "Bu keyword icin reklam verilebilir"
                if risk_level == "low"
                else "Dikkatli degerlendirin — orta riskli keyword"
            ),
        }


keyword_recommendation_service = KeywordRecommendationService()
