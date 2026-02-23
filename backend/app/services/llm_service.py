import os
import logging
from openai import OpenAI
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def analyze_products(self, products_data: List[Dict[str, Any]], question: Optional[str] = None) -> str:
        if not products_data:
            return "Analiz için ürün verisi bulunamadı."
        
        products_summary = self._format_products_for_analysis(products_data)
        
        system_prompt = """Sen bir pazaryeri veri analiz uzmanısın. Türkçe yanıt ver.
        Kullanıcının sağladığı ürün verilerini analiz et ve şunları belirle:
        1. Fiyat trendleri ve değişimleri
        2. Rekabet durumu ve sponsorlu ürün analizi
        3. Satıcı performansı
        4. Öneriler ve stratejiler
        
        Verilen verilere dayanarak somut ve eyleme geçirilebilir öneriler sun."""
        
        user_prompt = f"""Aşağıdaki ürün verilerini analiz et:

{products_summary}

"""
        if question:
            user_prompt += f"Özel soru: {question}\n"
        else:
            user_prompt += "Genel bir pazar analizi ve öneriler sun."
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM analysis failed: {type(e).__name__}: {e}")
            return "Analiz sirasinda beklenmeyen bir hata olustu. Lutfen tekrar deneyin."
    
    def _format_products_for_analysis(self, products_data: List[Dict[str, Any]]) -> str:
        formatted = []
        for i, product in enumerate(products_data, 1):
            formatted.append(f"\n--- Ürün {i}: {product.get('name', 'Bilinmiyor')} ---")
            formatted.append(f"Platform: {product.get('platform', 'Bilinmiyor')}")
            formatted.append(f"Satıcı: {product.get('seller', 'Bilinmiyor')}")
            
            snapshots = product.get('snapshots', [])
            if snapshots:
                formatted.append("Son 30 günlük veriler:")
                for snap in snapshots[:10]:
                    line = f"  {snap.get('date')}: "
                    if snap.get('price'):
                        line += f"Fiyat: {snap['price']} TL, "
                    if snap.get('rating'):
                        line += f"Puan: {snap['rating']}, "
                    if snap.get('reviews'):
                        line += f"Yorum: {snap['reviews']}, "
                    if snap.get('sponsored'):
                        line += "Sponsorlu"
                    formatted.append(line)
        
        return "\n".join(formatted)
    
    async def generate_keyword_suggestions(self, base_keyword: str) -> List[str]:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen bir e-ticaret anahtar kelime uzmanısın. Türkçe yanıt ver."},
                    {"role": "user", "content": f"'{base_keyword}' için pazaryerinde arama yapılabilecek 10 ilgili anahtar kelime öner. Sadece anahtar kelimeleri virgülle ayırarak listele."}
                ],
                max_tokens=200,
                temperature=0.8
            )
            keywords_text = response.choices[0].message.content
            keywords = [k.strip() for k in keywords_text.split(',')]
            return keywords[:10]
        except Exception as e:
            return [base_keyword]
