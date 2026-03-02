"""Add hybrid search: pgvector + pg_trgm extensions, embedding + tsvector columns.

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-03-02

Faz 1: Sadece monitored_products tablosu.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "e5f6g7h8i9j0"
down_revision: Union[str, None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable extensions (Neon supports these natively)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. New columns on monitored_products
    op.execute("ALTER TABLE monitored_products ADD COLUMN IF NOT EXISTS search_text TEXT")
    op.execute("ALTER TABLE monitored_products ADD COLUMN IF NOT EXISTS embedding vector(1536)")

    # Generated tsvector column — auto-updates when product_name/brand/sku change
    # Uses 'simple' config (no stemming) to preserve brand names and model numbers
    op.execute("""
        ALTER TABLE monitored_products
        ADD COLUMN IF NOT EXISTS search_tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('simple',
                coalesce(product_name, '') || ' ' ||
                coalesce(brand, '') || ' ' ||
                coalesce(sku, '')
            )
        ) STORED
    """)

    # 3. Indexes
    # pg_trgm GIN index for fuzzy matching on product_name
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_mp_name_trgm
        ON monitored_products USING gin (product_name gin_trgm_ops)
    """)

    # tsvector GIN index for full-text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_mp_search_tsv
        ON monitored_products USING gin (search_tsv)
    """)

    # pgvector HNSW index for cosine similarity search
    # m=16, ef_construction=64 is appropriate for 1K-10K products
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_mp_embedding_hnsw
        ON monitored_products USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_mp_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_mp_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_mp_name_trgm")

    # Drop columns
    op.execute("ALTER TABLE monitored_products DROP COLUMN IF EXISTS search_tsv")
    op.execute("ALTER TABLE monitored_products DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE monitored_products DROP COLUMN IF EXISTS search_text")

    # Don't drop extensions — other tables may use them in the future
