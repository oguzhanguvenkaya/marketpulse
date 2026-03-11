"""Add hybrid search columns to category_products table.

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-03-04

Faz 2A: category_products tablosuna search_text, embedding, search_tsv ekleme.
pg_trgm + tsvector + pgvector index'leri ile hybrid arama desteği.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "f6g7h8i9j0k1"
down_revision: Union[str, None] = "e5f6g7h8i9j0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions already enabled in e5f6g7h8i9j0 (vector, pg_trgm)

    # 1. New columns on category_products
    op.execute("ALTER TABLE category_products ADD COLUMN IF NOT EXISTS search_text TEXT")
    op.execute("ALTER TABLE category_products ADD COLUMN IF NOT EXISTS embedding vector(1536)")

    # Generated tsvector column — auto-updates when name/brand/description change
    # Uses 'simple' config (no stemming) to preserve brand names and model numbers
    op.execute("""
        ALTER TABLE category_products
        ADD COLUMN IF NOT EXISTS search_tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('simple',
                coalesce(name, '') || ' ' ||
                coalesce(brand, '') || ' ' ||
                coalesce(description, '')
            )
        ) STORED
    """)

    # 2. Indexes
    # pg_trgm GIN index on search_text for fuzzy matching (word_similarity)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_cp_search_trgm
        ON category_products USING gin (search_text gin_trgm_ops)
    """)

    # tsvector GIN index for full-text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_cp_search_tsv
        ON category_products USING gin (search_tsv)
    """)

    # pgvector HNSW index for cosine similarity search
    # m=16, ef_construction=64 is appropriate for 1K-10K products
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_cp_embedding_hnsw
        ON category_products USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_cp_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_cp_search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_cp_search_trgm")

    # Drop columns
    op.execute("ALTER TABLE category_products DROP COLUMN IF EXISTS search_tsv")
    op.execute("ALTER TABLE category_products DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE category_products DROP COLUMN IF EXISTS search_text")
