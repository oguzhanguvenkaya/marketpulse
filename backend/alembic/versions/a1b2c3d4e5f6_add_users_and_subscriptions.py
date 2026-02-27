"""add users and subscriptions

Revision ID: a1b2c3d4e5f6
Revises: 9b73f8e3f277
Create Date: 2026-02-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9b73f8e3f277'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """users ve subscriptions tablolarını oluştur."""
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('plan_tier', sa.String(20), server_default='free'),
        sa.Column('email_alerts_enabled', sa.Boolean(), server_default='true'),
        sa.Column('alert_frequency', sa.String(20), server_default='instant'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('plan_tier', sa.String(20), server_default='free'),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('sku_limit', sa.Integer(), server_default='10'),
        sa.Column('scan_frequency', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """users ve subscriptions tablolarını kaldır."""
    op.drop_table('subscriptions')
    op.drop_table('users')
