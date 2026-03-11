"""Embedding service — OpenAI embedding uretimi ve search text olusturma."""
from __future__ import annotations

import logging
from typing import Optional, List

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("ai.embedding")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


def build_search_text_monitored(product) -> str:
    """MonitoredProduct icin search text olustur.

    Bu metin hem embedding kaynagi hem de degisiklik tespiti icin kullanilir.
    search_text degismemisse yeni embedding uretmeye gerek yok.
    """
    parts = [
        product.product_name,
        product.brand,
        product.sku,
        product.barcode,
        product.platform,
    ]
    return " | ".join(p for p in parts if p).strip()


async def generate_embedding(text: str) -> Optional[List[float]]:
    """Tek metin icin OpenAI embedding uret.

    Hata durumunda None doner — embedding uretimi kritik degil,
    ILIKE fallback her zaman aktif.
    """
    if not text or not text.strip():
        return None
    try:
        client = _get_client()
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text.strip()[:8000],
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        return None


async def generate_embeddings_batch(
    texts: List[str],
) -> List[Optional[List[float]]]:
    """Toplu embedding uretimi (100'er batch).

    Bos/None text'ler icin None doner.
    """
    if not texts:
        return []

    valid_indices: list[int] = []
    valid_texts: list[str] = []
    for i, text in enumerate(texts):
        if text and text.strip():
            valid_indices.append(i)
            valid_texts.append(text.strip()[:8000])

    if not valid_texts:
        return [None] * len(texts)

    results: List[Optional[List[float]]] = [None] * len(texts)

    try:
        client = _get_client()
        batch_size = 100
        for batch_start in range(0, len(valid_texts), batch_size):
            batch = valid_texts[batch_start : batch_start + batch_size]
            batch_indices = valid_indices[batch_start : batch_start + batch_size]

            response = await client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )

            for j, embedding_data in enumerate(response.data):
                original_idx = batch_indices[j]
                results[original_idx] = embedding_data.embedding

    except Exception as e:
        logger.error("Batch embedding generation failed: %s", e)

    return results


def build_search_text_category(product) -> str:
    """CategoryProduct icin search text olustur.

    name + brand + description[:500] + specs values[:300]
    """
    parts = [product.name, product.brand]

    if product.description:
        parts.append(product.description[:500])

    if product.specs and isinstance(product.specs, dict):
        spec_text = " ".join(str(v) for v in product.specs.values())
        parts.append(spec_text[:300])

    return " | ".join(p for p in parts if p).strip()


async def embed_category_product(product, db) -> bool:
    """CategoryProduct icin embedding uret ve kaydet.

    search_text degismemisse skip eder.
    Returns True if embedding was updated, False otherwise.
    """
    search_text = build_search_text_category(product)
    if not search_text:
        return False
    if search_text == product.search_text and product.embedding is not None:
        return False  # Degisiklik yok

    embedding = await generate_embedding(search_text)
    if embedding is None:
        return False

    product.search_text = search_text
    product.embedding = embedding
    return True


async def embed_monitored_product(product, db) -> bool:
    """MonitoredProduct icin embedding uret ve kaydet.

    search_text degismemisse skip eder (gereksiz API cagrisi onlenir).
    Returns True if embedding was updated, False otherwise.
    """
    search_text = build_search_text_monitored(product)
    if not search_text:
        return False
    if search_text == product.search_text and product.embedding is not None:
        return False  # Degisiklik yok

    embedding = await generate_embedding(search_text)
    if embedding is None:
        return False

    product.search_text = search_text
    product.embedding = embedding
    return True
