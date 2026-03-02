"""Hybrid search service — pg_trgm + tsvector + pgvector ile RRF fusion.

Uc katmanli arama:
1. pg_trgm similarity  — yazim hatasi toleransi ("Sonaxs" → "Sonax")
2. tsvector full-text   — keyword relevans siralama
3. pgvector cosine      — anlamsal benzerlik ("araba parlatma" → cila)

Embedding yoksa veya feature flag kapali ise ILIKE fallback aktif.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.db.models import MonitoredProduct

logger = get_logger("ai.hybrid_search")

# Reciprocal Rank Fusion constant (standard from literature)
RRF_K = 60


async def hybrid_search_monitored(
    db: Session,
    user_id: str,
    query: str,
    platform: str = "",
    limit: int = 10,
) -> List[MonitoredProduct]:
    """monitored_products tablosunda hybrid arama.

    Feature flag kapali veya embedding yoksa ILIKE fallback'e doner.
    Platform filtresi tum katmanlarda uygulanir.
    """
    if not query or not query.strip():
        return []

    query = query.strip()

    if not settings.HYBRID_SEARCH_ENABLED:
        logger.info("[HYBRID_SEARCH] Feature flag disabled, using ILIKE fallback")
        return _ilike_fallback(db, user_id, query, platform, limit)

    # Tabloda embedding var mi kontrol
    try:
        has_embeddings = _check_embeddings_exist(db, user_id, platform)
    except Exception:
        logger.warning("[HYBRID_SEARCH] Extension check failed, using ILIKE fallback")
        return _ilike_fallback(db, user_id, query, platform, limit)

    if not has_embeddings:
        logger.info("[HYBRID_SEARCH] No embeddings found, using ILIKE fallback")
        return _ilike_fallback(db, user_id, query, platform, limit)

    # Query embedding uret
    from app.services.embedding_service import generate_embedding

    query_embedding = await generate_embedding(query)
    if query_embedding is None:
        logger.warning("[HYBRID_SEARCH] Query embedding failed, using ILIKE fallback")
        return _ilike_fallback(db, user_id, query, platform, limit)

    # RRF hybrid search
    try:
        product_ids = _execute_rrf_query(
            db, user_id, query, query_embedding, platform, limit
        )
    except Exception as e:
        logger.error("[HYBRID_SEARCH] RRF query failed: %s, using ILIKE fallback", e)
        return _ilike_fallback(db, user_id, query, platform, limit)

    if not product_ids:
        # RRF sonuc bulamadiysa ILIKE dene
        return _ilike_fallback(db, user_id, query, platform, limit)

    # Product nesnelerini cek ve RRF sirasini koru
    products = (
        db.query(MonitoredProduct)
        .filter(MonitoredProduct.id.in_(product_ids))
        .all()
    )
    product_map = {p.id: p for p in products}
    return [product_map[pid] for pid in product_ids if pid in product_map]


def _check_embeddings_exist(
    db: Session, user_id: str, platform: str
) -> bool:
    """Kullanicinin urunlerinde embedding var mi kontrol et."""
    params = {"user_id": user_id}
    platform_clause = ""
    if platform:
        platform_clause = "AND platform = :platform"
        params["platform"] = platform

    result = db.execute(
        text(f"""
            SELECT EXISTS(
                SELECT 1 FROM monitored_products
                WHERE user_id = :user_id
                  AND is_active = true
                  AND embedding IS NOT NULL
                  {platform_clause}
                LIMIT 1
            )
        """),
        params,
    ).scalar()
    return bool(result)


def _execute_rrf_query(
    db: Session,
    user_id: str,
    query: str,
    query_embedding: List[float],
    platform: str,
    limit: int,
) -> List:
    """Uc katmanli RRF fusion sorgusu calistir."""
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    params = {
        "user_id": user_id,
        "query": query,
        "embedding": embedding_str,
        "rrf_k": RRF_K,
        "limit": limit,
    }

    # Platform filtresi dinamik — bossa tum platformlar
    platform_clause = ""
    if platform:
        platform_clause = "AND platform = :platform"
        params["platform"] = platform

    sql = text(f"""
        WITH
        -- Layer 1: pg_trgm fuzzy match
        trgm_results AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       ORDER BY similarity(product_name, :query) DESC
                   ) AS rank
            FROM monitored_products
            WHERE user_id = :user_id
              AND is_active = true
              {platform_clause}
              AND product_name IS NOT NULL
              AND similarity(product_name, :query) > 0.05
            ORDER BY similarity(product_name, :query) DESC
            LIMIT 50
        ),
        -- Layer 2: tsvector full-text search
        fts_results AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       ORDER BY ts_rank(search_tsv, plainto_tsquery('simple', :query)) DESC
                   ) AS rank
            FROM monitored_products
            WHERE user_id = :user_id
              AND is_active = true
              {platform_clause}
              AND search_tsv IS NOT NULL
              AND search_tsv @@ plainto_tsquery('simple', :query)
            ORDER BY ts_rank(search_tsv, plainto_tsquery('simple', :query)) DESC
            LIMIT 50
        ),
        -- Layer 3: pgvector cosine similarity
        vec_results AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       ORDER BY embedding <=> :embedding::vector
                   ) AS rank
            FROM monitored_products
            WHERE user_id = :user_id
              AND is_active = true
              {platform_clause}
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT 50
        ),
        -- Combine with RRF
        combined AS (
            SELECT
                COALESCE(t.id, f.id, v.id) AS id,
                COALESCE(1.0 / (:rrf_k + t.rank), 0)
                + COALESCE(1.0 / (:rrf_k + f.rank), 0)
                + COALESCE(1.0 / (:rrf_k + v.rank), 0) AS score
            FROM trgm_results t
            FULL OUTER JOIN fts_results f ON t.id = f.id
            FULL OUTER JOIN vec_results v ON COALESCE(t.id, f.id) = v.id
        )
        SELECT id, score
        FROM combined
        ORDER BY score DESC
        LIMIT :limit
    """)

    rows = db.execute(sql, params).fetchall()
    logger.info(
        "[HYBRID_SEARCH] query=%r platform=%r results=%d",
        query,
        platform or "all",
        len(rows),
    )
    return [row.id for row in rows]


def _ilike_fallback(
    db: Session,
    user_id: str,
    query: str,
    platform: str,
    limit: int,
) -> List[MonitoredProduct]:
    """ILIKE fallback — mevcut davranis ile birebir ayni."""
    q = db.query(MonitoredProduct).filter(
        MonitoredProduct.user_id == user_id,
        MonitoredProduct.is_active == True,  # noqa: E712
        MonitoredProduct.product_name.ilike(f"%{query}%"),
    )
    if platform:
        q = q.filter(MonitoredProduct.platform == platform)
    return q.limit(limit).all()
