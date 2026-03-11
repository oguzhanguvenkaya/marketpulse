"""Reranker service — Cohere rerank ile sonuc yeniden siralama.

Hybrid search sonuclarini LLM-tabanli reranker ile yeniden siralar.
API key yoksa veya hata olursa gracefully orijinal sirayi korur.
"""
from __future__ import annotations

import logging
from typing import Callable, List, TypeVar

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("ai.reranker")

T = TypeVar("T")


async def rerank_products(
    query: str,
    products: List[T],
    build_doc_fn: Callable[[T], str],
    top_n: int | None = None,
) -> List[T]:
    """Urunleri Cohere reranker ile yeniden sirala.

    Args:
        query: Kullanici arama sorgusu
        products: Siralanacak urun listesi
        build_doc_fn: Urun → arama dokumani string donusturucusu
        top_n: Donecek maksimum sonuc (None ise config'den alir)

    Returns:
        Yeniden siralanmis urun listesi. Hata durumunda orijinal liste.
    """
    if not products:
        return []

    if not settings.RERANKER_ENABLED:
        logger.debug("[RERANKER] Disabled via config")
        _top_n = top_n or settings.RERANKER_TOP_N
        return products[:_top_n]

    api_key = settings.COHERE_API_KEY
    if not api_key:
        logger.info("[RERANKER] No COHERE_API_KEY, returning original order")
        _top_n = top_n or settings.RERANKER_TOP_N
        return products[:_top_n]

    _top_n = top_n or settings.RERANKER_TOP_N

    # Dokumanlari hazirla
    documents = [build_doc_fn(p) for p in products]

    try:
        import cohere

        client = cohere.AsyncClientV2(api_key=api_key)
        response = await client.rerank(
            model=settings.RERANKER_MODEL,
            query=query,
            documents=documents,
            top_n=min(_top_n, len(products)),
        )

        reranked = [products[r.index] for r in response.results]
        logger.info(
            "[RERANKER] query=%r items=%d → top_%d reranked",
            query[:50],
            len(products),
            len(reranked),
        )
        return reranked

    except ImportError:
        logger.warning("[RERANKER] cohere package not installed, returning original order")
        return products[:_top_n]
    except Exception as e:
        logger.error("[RERANKER] Rerank failed: %s, returning original order", e)
        return products[:_top_n]
