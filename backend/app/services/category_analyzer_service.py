"""
AI Kategori Uyum Denetimi — ürünün doğru kategoride olup olmadığını analiz eder.

Mevcut Category Explorer altyapısını kullanarak kategorideki ilk N ürünü çeker,
ardından LLM ile ürünün kategoriye uyumluluğunu değerlendirir.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from openai import OpenAI

from app.core.config import settings
from app.db.models import MonitoredProduct, CategoryProduct, CategorySession

logger = logging.getLogger(__name__)


CATEGORY_ANALYSIS_PROMPT = """Sen bir e-ticaret kategori uzmanısın. Türk pazaryerlerinde (Hepsiburada, Trendyol)
ürün kategorizasyonu konusunda uzmansın.

Bir ürünün bulunduğu kategorideki rakip ürünlerle ne kadar uyumlu olduğunu analiz et.

## Analiz Edilecek Ürün
Adı: {product_name}
SKU: {product_sku}
Platform: {platform}

## Kategorideki Rakip Ürünler (ilk {competitor_count} ürün)
{competitor_list}

## Görevin
1. Ürünün kategoriye uyumluluk skorunu 0-100 arasında ver
2. Kategorideki ürünlerin genel profili nedir? (ne tür ürünler satılıyor)
3. Analiz edilen ürün bu profile uyuyor mu?
4. Eğer uyumsuzluk varsa, neden uyumsuz olduğunu açıkla
5. Daha uygun kategori önerisi var mı?

JSON formatında yanıt ver:
{{
    "uyumluluk_skoru": 0-100,
    "kategori_profili": "Kategorideki ürünlerin genel açıklaması",
    "uyumlu_mu": true/false,
    "analiz": "Detaylı analiz metni",
    "uyumsuzluk_nedeni": "Eğer uyumsuz ise neden (yoksa null)",
    "onerilen_kategori": "Daha uygun kategori önerisi (yoksa null)",
    "rakip_ozeti": {{
        "ortalama_fiyat": sayı veya null,
        "en_cok_marka": "marka adı veya null",
        "urun_tipi": "ürün türü açıklaması"
    }}
}}
"""


class CategoryAnalyzerService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    async def analyze_product_category(
        self,
        user_id: str,
        product_id: str,
        db: Session,
        max_competitors: int = 40,
    ) -> dict:
        """Ürünün kategorideki uyumluluğunu AI ile analiz et."""
        if not self.client:
            return {"error": "AI servisi yapılandırılmamış. OPENAI_API_KEY gerekli."}

        # Ürünü bul
        product = db.query(MonitoredProduct).filter(
            MonitoredProduct.id == product_id,
            MonitoredProduct.user_id == user_id,
        ).first()

        if not product:
            return {"error": "Ürün bulunamadı"}

        # Kategorideki ürünleri bul (mevcut category session'lardan)
        competitors = self._get_category_competitors(db, product, max_competitors)

        if not competitors:
            return {
                "error": "Bu ürün için kategori verisi bulunamadı. "
                "Önce Category Explorer ile kategori taraması yapın."
            }

        # LLM ile analiz
        competitor_list = self._format_competitors(competitors)

        prompt = CATEGORY_ANALYSIS_PROMPT.format(
            product_name=product.product_name or product.sku,
            product_sku=product.sku,
            platform=product.platform,
            competitor_count=len(competitors),
            competitor_list=competitor_list,
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )
            import json
            result = json.loads(response.choices[0].message.content)
            result["product_id"] = product_id
            result["product_name"] = product.product_name
            result["platform"] = product.platform
            result["competitor_count"] = len(competitors)
            return result
        except Exception as e:
            logger.error(f"Kategori analizi hatası: {e}")
            return {"error": f"AI analizi başarısız: {str(e)}"}

    def _get_category_competitors(
        self,
        db: Session,
        product: MonitoredProduct,
        max_count: int,
    ) -> list:
        """Ürünün kategorisindeki rakip ürünleri bul."""
        # Aynı platform'daki en son category session'dan ürünleri çek
        latest_session = (
            db.query(CategorySession)
            .filter(
                CategorySession.platform == product.platform,
                CategorySession.status == "active",
            )
            .order_by(CategorySession.created_at.desc())
            .first()
        )

        if not latest_session:
            return []

        competitors = (
            db.query(CategoryProduct)
            .filter(CategoryProduct.session_id == latest_session.id)
            .order_by(CategoryProduct.position)
            .limit(max_count)
            .all()
        )

        return competitors

    def _format_competitors(self, competitors: list) -> str:
        """Rakip ürünleri LLM prompt'u için formatla."""
        lines = []
        for i, c in enumerate(competitors, 1):
            price_str = f"{float(c.price):.2f} TL" if c.price else "Fiyat yok"
            brand_str = c.brand or "Marka yok"
            lines.append(f"{i}. {c.name} | Marka: {brand_str} | Fiyat: {price_str}")
        return "\n".join(lines)

    async def quick_category_check(
        self, product_name: str, category_products: list[str]
    ) -> dict:
        """Hızlı kategori uyum kontrolü (ürün adı ve rakip isimleri ile)."""
        if not self.client:
            return {"error": "AI servisi yapılandırılmamış."}

        prompt = f"""Ürün: {product_name}
Kategorideki diğer ürünler: {', '.join(category_products[:20])}

Bu ürün kategorideki diğer ürünlerle uyumlu mu?
Kısa yanıt ver: uyumluluk_skoru (0-100), uyumlu_mu (true/false), kisa_analiz (1 cümle)
JSON formatında yanıt ver."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            import json
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}


category_analyzer_service = CategoryAnalyzerService()
