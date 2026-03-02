#!/usr/bin/env python3
"""Mevcut urunler icin embedding backfill scripti.

Kullanim:
    cd backend
    python -m scripts.backfill_embeddings --table monitored_products --batch-size 100
    python -m scripts.backfill_embeddings --table monitored_products --user-id <uuid>
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Path bootstrap (runtime_preflight.py ile ayni pattern)
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.database import get_session_local  # noqa: E402
from app.db.models import MonitoredProduct  # noqa: E402
from app.services.embedding_service import (  # noqa: E402
    build_search_text_monitored,
    generate_embeddings_batch,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TABLE_MAP = {
    "monitored_products": (MonitoredProduct, build_search_text_monitored),
}


async def backfill(table_name: str, batch_size: int = 100, user_id: str | None = None):
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not configured. Aborting.")
        sys.exit(1)

    model_class, build_fn = TABLE_MAP[table_name]
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        query = db.query(model_class).filter(
            model_class.embedding.is_(None),
            model_class.product_name.isnot(None),
        )
        if user_id:
            query = query.filter(model_class.user_id == user_id)

        total = query.count()
        logger.info("Found %d products without embeddings in %s", total, table_name)

        if total == 0:
            logger.info("Nothing to do.")
            return

        processed = 0
        embedded = 0

        while True:
            batch = query.limit(batch_size).all()
            if not batch:
                break

            texts = [build_fn(p) for p in batch]
            embeddings = await generate_embeddings_batch(texts)

            batch_embedded = 0
            for product, search_text, embedding in zip(batch, texts, embeddings):
                if embedding is not None:
                    product.search_text = search_text
                    product.embedding = embedding
                    batch_embedded += 1

            db.commit()
            processed += len(batch)
            embedded += batch_embedded
            logger.info(
                "Progress: %d/%d processed, %d embedded (%.1f%%)",
                processed,
                total,
                embedded,
                processed / total * 100,
            )

    finally:
        db.close()

    logger.info(
        "Backfill complete: %d products processed, %d embeddings created",
        processed,
        embedded,
    )


def main():
    parser = argparse.ArgumentParser(description="Backfill product embeddings")
    parser.add_argument(
        "--table",
        required=True,
        choices=TABLE_MAP.keys(),
        help="Table to backfill",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for embedding generation (default: 100)",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="Optional: only backfill products for this user",
    )
    args = parser.parse_args()

    asyncio.run(backfill(args.table, args.batch_size, args.user_id))


if __name__ == "__main__":
    main()
