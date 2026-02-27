"""AI-Destekli Generic Web Scraping Service.

Bilinmeyen web siteleri icin:
- URL verildiginde sayfa HTML'ini LLM'e gonder
- LLM urun bilgilerini (isim, fiyat, aciklama, resim) tespit eder
- Selector onerisi olusturur ve validate eder
- Sonraki taramalarda ayni selector'i kullanir (cache)
- Basarisiz olursa yeniden LLM'e sor (self-healing)
"""

import json
import logging
import re
import hashlib
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory selector cache: domain -> {selectors, last_used, success_count}
_selector_cache: dict[str, dict] = {}


SELECTOR_EXTRACTION_PROMPT = """Sen bir web scraping uzmanisin. Asagidaki HTML'den urun bilgilerini cikar.

HTML (kisaltilmis):
{html_snippet}

Lutfen su bilgileri JSON olarak dondur:
{{
  "product_name": "urun adi veya null",
  "price": "fiyat (sayi) veya null",
  "currency": "para birimi (TRY, USD, EUR) veya null",
  "original_price": "orijinal fiyat (indirim oncesi) veya null",
  "description": "urun aciklamasi (kisa) veya null",
  "image_url": "ana urun resim URL'si veya null",
  "brand": "marka veya null",
  "sku": "urun kodu veya null",
  "availability": "stok durumu (in_stock, out_of_stock) veya null",
  "seller_name": "satici adi veya null",
  "category": "kategori veya null",
  "rating": "puan (sayi) veya null",
  "review_count": "yorum sayisi (sayi) veya null",
  "selectors": {{
    "product_name": "CSS selector ornegi (h1.product-title gibi)",
    "price": "CSS selector ornegi",
    "image": "CSS selector ornegi"
  }}
}}

KURALLAR:
- Sadece HTML'den cikarabildigin bilgileri doldur, tahmin yapma
- Fiyat icin sayisal deger kullan (1299.90 gibi), para birimi isareti koyma
- selector onerilerini de ekle ki sonraki taramalarda kullanabilelim
- Sadece JSON dondur, baska metin ekleme
"""


def _get_openai_client():
    """Lazy OpenAI client."""
    from openai import OpenAI
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY ayarlanmadi")
    return OpenAI(api_key=api_key)


def _domain_key(url: str) -> str:
    """URL'den domain key cikar."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")


def _truncate_html(html: str, max_chars: int = 12000) -> str:
    """HTML'i LLM icin kisalt — script/style kaldir, body icerigini al."""
    # Script ve style tag'lerini kaldir
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    # Coklu bosluk temizle
    html = re.sub(r'\s+', ' ', html)

    # Body icerigi al
    body_match = re.search(r'<body[^>]*>(.*)</body>', html, re.DOTALL | re.IGNORECASE)
    if body_match:
        html = body_match.group(1)

    if len(html) > max_chars:
        html = html[:max_chars] + "\n... [kisaltildi]"
    return html


def _try_css_selectors(html: str, selectors: dict) -> dict:
    """Cached CSS selector'lari HTML'e uygula."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
    except ImportError:
        return {}

    result = {}
    for field, selector in selectors.items():
        if not selector:
            continue
        try:
            el = soup.select_one(selector)
            if el:
                if field == "image":
                    result["image_url"] = el.get("src") or el.get("data-src") or el.get("content")
                elif field == "price":
                    text = el.get("content") or el.get_text(strip=True)
                    # Fiyat temizle
                    cleaned = re.sub(r'[^\d.,]', '', text.replace('.', '').replace(',', '.') if ',' in text else text)
                    price_match = re.search(r'[\d.]+', cleaned)
                    if price_match:
                        result["price"] = price_match.group(0)
                else:
                    result[field] = el.get("content") or el.get_text(strip=True)
        except Exception:
            continue
    return result


async def ai_scrape_url(url: str, html: str, db: Optional[Session] = None) -> dict:
    """URL'nin HTML'ini AI ile analiz edip urun bilgilerini cikar.

    1. Cached selector varsa once onu dene
    2. Calismiyorsa LLM'e sor
    3. Basarili selector'lari cache'le
    """
    domain = _domain_key(url)

    # 1. Cache'deki selector'lari dene
    cached = _selector_cache.get(domain)
    if cached and cached.get("selectors"):
        selector_result = _try_css_selectors(html, cached["selectors"])
        if selector_result.get("product_name") or selector_result.get("price"):
            cached["success_count"] = cached.get("success_count", 0) + 1
            cached["last_used"] = datetime.utcnow().isoformat()
            logger.info(f"AI Scraper: Cache hit for {domain} (success #{cached['success_count']})")
            return {
                "source": "cached_selectors",
                "domain": domain,
                "url": url,
                **selector_result,
            }
        else:
            logger.info(f"AI Scraper: Cache miss for {domain}, falling back to LLM")

    # 2. LLM ile analiz
    return await _llm_extract(url, html, domain)


async def _llm_extract(url: str, html: str, domain: str, retry: bool = False) -> dict:
    """LLM ile HTML'den urun bilgilerini cikar."""
    snippet = _truncate_html(html)

    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sen bir web scraping uzmanisin. Verilen HTML'den urun bilgilerini cikarirsin. Sadece JSON formatinda yanit ver."},
                {"role": "user", "content": SELECTOR_EXTRACTION_PROMPT.format(html_snippet=snippet)},
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Selector'lari cache'le
        selectors = result.pop("selectors", {})
        if selectors and any(selectors.values()):
            _selector_cache[domain] = {
                "selectors": selectors,
                "last_used": datetime.utcnow().isoformat(),
                "success_count": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
            logger.info(f"AI Scraper: Cached selectors for {domain}: {list(selectors.keys())}")

        result["source"] = "llm_extraction"
        result["domain"] = domain
        result["url"] = url
        return result

    except json.JSONDecodeError:
        if not retry:
            logger.warning(f"AI Scraper: JSON parse hatasi, retry ediliyor ({domain})")
            return await _llm_extract(url, html, domain, retry=True)
        return {"error": "LLM JSON parse hatasi", "url": url, "domain": domain}
    except Exception as e:
        logger.error(f"AI Scraper hatasi ({domain}): {e}")
        return {"error": str(e), "url": url, "domain": domain}


def get_cached_selectors(domain: str) -> Optional[dict]:
    """Domain icin cached selector'lari dondur."""
    return _selector_cache.get(domain)


def clear_selector_cache(domain: Optional[str] = None):
    """Selector cache'ini temizle."""
    if domain:
        _selector_cache.pop(domain, None)
    else:
        _selector_cache.clear()


def get_cache_stats() -> dict:
    """Cache istatistikleri."""
    return {
        "total_domains": len(_selector_cache),
        "domains": {
            domain: {
                "success_count": info.get("success_count", 0),
                "last_used": info.get("last_used"),
                "created_at": info.get("created_at"),
                "selector_count": len([v for v in info.get("selectors", {}).values() if v]),
            }
            for domain, info in _selector_cache.items()
        },
    }
