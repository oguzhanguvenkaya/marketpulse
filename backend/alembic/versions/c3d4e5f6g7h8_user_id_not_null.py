"""make user_id NOT NULL on 8 multi-tenant tables

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 8 tablo — hepsi nullable=True olan user_id'ye sahip
TABLES = [
    'monitored_products',
    'search_tasks',
    'price_monitor_tasks',
    'json_files',
    'scrape_jobs',
    'transcript_jobs',
    'store_products',
    'category_sessions',
]


def upgrade() -> None:
    """user_id kolonlarını NOT NULL yap.

    Strateji:
    1. users tablosunda en az 1 kullanıcı olduğundan emin ol (yoksa seed user oluştur)
    2. NULL user_id olan satırları ilk kullanıcıya ata
    3. Kolonu NOT NULL yap
    """
    conn = op.get_bind()

    # 1. En az bir kullanıcı olduğundan emin ol
    result = conn.execute(sa.text("SELECT id FROM users LIMIT 1"))
    row = result.fetchone()

    if row is None:
        # Seed user oluştur — development/migration için
        conn.execute(sa.text(
            "INSERT INTO users (id, email, full_name, plan_tier, created_at, updated_at) "
            "VALUES (gen_random_uuid(), 'admin@marketpulse.local', 'System Admin', 'enterprise', now(), now())"
        ))
        result = conn.execute(sa.text("SELECT id FROM users LIMIT 1"))
        row = result.fetchone()

    default_user_id = row[0]

    # 2. NULL user_id olan satırları default user'a ata
    for table in TABLES:
        conn.execute(sa.text(
            f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"
        ), {"uid": default_user_id})

    # 3. Kolonu NOT NULL yap
    for table in TABLES:
        op.alter_column(
            table,
            'user_id',
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )


def downgrade() -> None:
    """user_id kolonlarını tekrar nullable yap."""
    for table in TABLES:
        op.alter_column(
            table,
            'user_id',
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )
