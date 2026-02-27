"""AI-Destekli Generic Web Scraping routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.ai_scraper_service import (
    ai_scrape_url,
    get_cache_stats,
    clear_selector_cache,
)
from app.services.url_scraper_service import UrlScraperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-scraper", tags=["AI Scraper"])


class AIScrapeRequest(BaseModel):
    url: str
    use_cache: bool = True


class AIScrapeResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/extract", response_model=AIScrapeResponse)
async def ai_extract_product(
    req: AIScrapeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI ile bilinmeyen URL'den urun bilgisi cikar."""
    # URL'yi fetch et
    scraper = UrlScraperService()
    html = await scraper.fetch_url(req.url)
    if not html:
        # ScraperAPI yoksa direkt aiohttp dene
        import aiohttp
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(req.url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        html = await resp.text()
        except Exception:
            pass

    if not html:
        return AIScrapeResponse(success=False, error="URL'ye erisilemedi")

    # AI ile analiz
    result = await ai_scrape_url(req.url, html, db)
    if result.get("error"):
        return AIScrapeResponse(success=False, error=result["error"], data=result)

    return AIScrapeResponse(success=True, data=result)


@router.get("/cache/stats")
async def cache_statistics(user: User = Depends(get_current_user)):
    """Selector cache istatistikleri."""
    return get_cache_stats()


@router.delete("/cache/{domain}")
async def clear_domain_cache(
    domain: str,
    user: User = Depends(get_current_user),
):
    """Belirli domain icin cache temizle."""
    clear_selector_cache(domain)
    return {"mesaj": f"'{domain}' cache temizlendi"}


@router.delete("/cache")
async def clear_all_cache(user: User = Depends(get_current_user)):
    """Tum selector cache'ini temizle."""
    clear_selector_cache()
    return {"mesaj": "Tum cache temizlendi"}
