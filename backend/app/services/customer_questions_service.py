"""AI Musteri Hizmetleri Servisi.

Pazaryeri musteri sorularina AI ile otonom veya yari-otonom yanit.
HB/TY Customer Questions API polling, context derleme, AI yanit uretimi.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User

logger = logging.getLogger(__name__)


# Ornek musteri sorulari (gercek API entegrasyonunda polling ile gelecek)
SAMPLE_QUESTIONS = [
    {
        "id": "q1",
        "platform": "hepsiburada",
        "product_name": "Apple iPhone 15 128GB",
        "product_sku": "HBV00001ABCDE",
        "customer_name": "Mehmet Y.",
        "question": "Bu urun garantili mi? Garanti suresi ne kadar?",
        "asked_at": "2026-02-27T10:30:00",
        "status": "pending",
    },
    {
        "id": "q2",
        "platform": "trendyol",
        "product_name": "Samsung Galaxy S24 Ultra",
        "product_sku": "TY-12345678",
        "customer_name": "Ayse K.",
        "question": "Kargo ne zaman gelir? Istanbul'a kac gunde teslimat yapilir?",
        "asked_at": "2026-02-27T11:15:00",
        "status": "pending",
    },
    {
        "id": "q3",
        "platform": "hepsiburada",
        "product_name": "Dyson V15 Detect",
        "product_sku": "HBV000034567",
        "customer_name": "Ali S.",
        "question": "Urunun renk secenekleri var mi? Gold renk mevcut mu?",
        "asked_at": "2026-02-27T12:00:00",
        "status": "pending",
    },
]


# Magaza politikalari template
DEFAULT_STORE_POLICIES = {
    "shipping": "Siparisler 1-3 is gunu icerisinde kargoya verilir. Istanbul ici teslimat genellikle 1-2 is gunu, diger iller 2-4 is gunudur.",
    "warranty": "Tum urunlerimiz 2 yil resmi distribütor garantisi altindadir. Garanti kapsami disinda kalan durumlar icin Tuketici Hakem Heyeti'ne basvurabilirsiniz.",
    "return": "Urunler teslim alindigindan itibaren 14 gun icerisinde ucretsiz iade edilebilir. Urunun kullanilmamis ve orijinal ambalajinda olmasi gerekmektedir.",
    "payment": "Kredi karti, banka karti, havale/EFT ve kapida odeme secenekleri mevcuttur.",
}


ANSWER_GENERATION_PROMPT = """Sen bir e-ticaret magaza asistanisin. Musteri sorusuna cevap yazacaksin.

URUN BILGISI:
- Urun Adi: {product_name}
- SKU: {product_sku}
- Platform: {platform}
{product_context}

MAGAZA POLITIKALARI:
{store_policies}

MUSTERI SORUSU:
"{question}"

KURALLAR:
1. Kibarca ve profesyonelce yanit ver
2. Sadece bildigin bilgileri paylasan — tahmin yapma, hallucination yapma
3. Urun bilgisi yoksa "Bu konuda detayli bilgi icin magaza ile iletisime gecebilirsiniz" de
4. Turkce yaz, resmi ama sicak bir dil kullan
5. Yanitini kisa tut (1-3 cumle), gereksiz uzatma
6. Magaza politikalarina uygun yanit ver

YANITINI ASAGIDAKI JSON FORMATINDA VER:
{{
  "answer": "Musteri yanitinin tam metni",
  "confidence": 0.0-1.0 arasi guven skoru (1.0 = cok emin),
  "sources": ["yanit icin kullanilan bilgi kaynaklari"],
  "needs_human_review": true/false
}}
"""


def _get_openai_client():
    """Lazy OpenAI client."""
    from openai import OpenAI
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY ayarlanmadi")
    return OpenAI(api_key=api_key)


class CustomerQuestionsService:
    """Musteri sorulari servisi."""

    async def get_pending_questions(
        self,
        user: User,
        db: Session,
        platform: Optional[str] = None,
    ) -> dict:
        """Bekleyen musteri sorularini listele.

        Gercek entegrasyonda API polling ile gelecek.
        Simdilik ornek veri donuyor.
        """
        questions = [q for q in SAMPLE_QUESTIONS]
        if platform:
            questions = [q for q in questions if q["platform"] == platform]

        return {
            "total": len(questions),
            "questions": questions,
        }

    async def generate_ai_answer(
        self,
        user: User,
        db: Session,
        question_id: str,
        custom_context: Optional[str] = None,
        store_policies: Optional[dict] = None,
    ) -> dict:
        """AI ile musteri sorusuna yanit olustur."""
        # Soruyu bul
        question_data = None
        for q in SAMPLE_QUESTIONS:
            if q["id"] == question_id:
                question_data = q
                break

        if not question_data:
            return {"error": f"Soru bulunamadi: {question_id}"}

        # Context derle
        product_context = custom_context or ""
        policies = store_policies or DEFAULT_STORE_POLICIES
        policies_text = "\n".join(f"- {k.capitalize()}: {v}" for k, v in policies.items())

        # LLM ile yanit uret
        prompt = ANSWER_GENERATION_PROMPT.format(
            product_name=question_data["product_name"],
            product_sku=question_data["product_sku"],
            platform=question_data["platform"],
            product_context=product_context,
            store_policies=policies_text,
            question=question_data["question"],
        )

        try:
            client = _get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen bir e-ticaret magaza musteri hizmetleri asistanisin. Sadece JSON formatinda yanit ver."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            return {
                "question_id": question_id,
                "question": question_data["question"],
                "product_name": question_data["product_name"],
                "answer": result.get("answer", ""),
                "confidence": result.get("confidence", 0),
                "sources": result.get("sources", []),
                "needs_human_review": result.get("needs_human_review", True),
                "mode": "copilot",  # copilot = insan onay, autopilot = otomatik gonder
                "generated_at": datetime.utcnow().isoformat(),
            }

        except json.JSONDecodeError:
            return {"error": "AI yanit parse hatasi", "question_id": question_id}
        except Exception as e:
            logger.error(f"AI yanit uretim hatasi: {e}")
            return {"error": str(e), "question_id": question_id}

    async def approve_and_send(
        self,
        user: User,
        db: Session,
        question_id: str,
        answer: str,
        edited: bool = False,
    ) -> dict:
        """Onayli yaniti pazaryerine gonder.

        Gercek entegrasyonda HB/TY API'si ile gonderilecek.
        """
        # TODO: Gercek API gonderimi (Marketplace API entegrasyonu ile)
        return {
            "question_id": question_id,
            "status": "sent",
            "answer": answer,
            "edited_by_human": edited,
            "sent_at": datetime.utcnow().isoformat(),
            "message": "Yanit basariyla gonderildi (simule)",
        }

    async def get_answer_history(
        self,
        user: User,
        db: Session,
        limit: int = 50,
    ) -> dict:
        """Yanit gecmisi ve basari orani."""
        # TODO: DB'den gecmis verileri cek
        return {
            "total_answered": 0,
            "auto_approved": 0,
            "human_edited": 0,
            "avg_confidence": 0,
            "history": [],
        }

    async def update_store_policies(
        self,
        user: User,
        db: Session,
        policies: dict,
    ) -> dict:
        """Magaza politikalarini guncelle.

        AI yanit uretiminde kullanilacak.
        """
        # TODO: DB'ye kaydet (user_settings tablosunda)
        return {
            "success": True,
            "policies": policies,
            "message": "Magaza politikalari guncellendi",
        }


customer_questions_service = CustomerQuestionsService()
