"""add multi-tenant user_id, scheduled_tasks, alert_logs

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-27 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Multi-tenant user_id ekleme + scheduled_tasks + alert_logs tabloları."""

    # --- 1. Mevcut tablolara user_id nullable olarak ekle ---
    tables_with_user_id = [
        'monitored_products',
        'search_tasks',
        'price_monitor_tasks',
        'json_files',
        'scrape_jobs',
        'transcript_jobs',
        'store_products',
        'category_sessions',
    ]

    for table in tables_with_user_id:
        op.add_column(table, sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
        op.create_index(f'ix_{table}_user_id', table, ['user_id'])
        op.create_foreign_key(
            f'fk_{table}_user_id',
            table, 'users',
            ['user_id'], ['id'],
        )

    # --- 2. MonitoredProduct ek kolonlar (kârlılık) ---
    op.add_column('monitored_products', sa.Column('unit_cost', sa.Numeric(10, 2), nullable=True))
    op.add_column('monitored_products', sa.Column('shipping_cost', sa.Numeric(10, 2), nullable=True))

    # --- 3. MonitoredProduct composite index ---
    op.create_index(
        'ix_monitored_products_user_platform',
        'monitored_products',
        ['user_id', 'platform', 'is_active'],
    )

    # --- 4. MonitoredProduct unique constraint ---
    # NOT: user_id nullable olduğu sürece unique constraint partial olacak
    # Production'da user_id NOT NULL yapıldıktan sonra tam constraint olur
    op.create_unique_constraint(
        'uq_monitored_product_user_platform_sku',
        'monitored_products',
        ['user_id', 'platform', 'sku'],
    )

    # --- 5. scheduled_tasks tablosu ---
    op.create_table(
        'scheduled_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('users.id'), nullable=False),
        sa.Column('platform', sa.String(30), nullable=False),
        sa.Column('task_type', sa.String(30), server_default='price_monitor'),
        sa.Column('frequency_hours', sa.Integer(), nullable=False),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_scheduled_tasks_user_id', 'scheduled_tasks', ['user_id'])
    op.create_index('ix_scheduled_tasks_next_run', 'scheduled_tasks', ['next_run_at', 'is_active'])
    op.create_unique_constraint(
        'uq_scheduled_task_user_platform_type',
        'scheduled_tasks',
        ['user_id', 'platform', 'task_type'],
    )

    # --- 6. alert_logs tablosu ---
    op.create_table(
        'alert_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('users.id'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('monitored_products.id'), nullable=True),
        sa.Column('alert_type', sa.String(30), nullable=False),
        sa.Column('old_value', sa.String(255), nullable=True),
        sa.Column('new_value', sa.String(255), nullable=True),
        sa.Column('email_sent', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_alert_logs_user_id', 'alert_logs', ['user_id'])
    op.create_index('ix_alert_logs_product_id', 'alert_logs', ['product_id'])


def downgrade() -> None:
    """Multi-tenant değişikliklerini geri al."""
    op.drop_table('alert_logs')
    op.drop_table('scheduled_tasks')

    op.drop_constraint('uq_monitored_product_user_platform_sku', 'monitored_products', type_='unique')
    op.drop_index('ix_monitored_products_user_platform', 'monitored_products')
    op.drop_column('monitored_products', 'shipping_cost')
    op.drop_column('monitored_products', 'unit_cost')

    tables_with_user_id = [
        'category_sessions',
        'store_products',
        'transcript_jobs',
        'scrape_jobs',
        'json_files',
        'price_monitor_tasks',
        'search_tasks',
        'monitored_products',
    ]

    for table in tables_with_user_id:
        op.drop_constraint(f'fk_{table}_user_id', table, type_='foreignkey')
        op.drop_index(f'ix_{table}_user_id', table)
        op.drop_column(table, 'user_id')
