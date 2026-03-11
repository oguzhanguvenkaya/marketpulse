"""Add my_store_products table for CSV-imported web products.

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-03-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6g7h8i9j0k1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "my_store_products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("seo_link", sa.Text(), nullable=True),
        sa.Column("stock_code", sa.String(100), nullable=True),
        sa.Column("barcode", sa.String(50), nullable=True),
        sa.Column("meta_keywords", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.Text(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("supplier", sa.String(255), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("detail_html", sa.Text(), nullable=True),
        sa.Column("hepsiburada_sku", sa.String(100), nullable=True),
        sa.Column("category_path", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("image_url_2", sa.Text(), nullable=True),
        sa.Column("image_list", sa.JSON(), nullable=True),
        sa.Column("web_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "barcode", name="uq_my_store_product_user_barcode"),
    )
    op.create_index("ix_my_store_products_user_id", "my_store_products", ["user_id"])
    op.create_index("ix_my_store_products_barcode", "my_store_products", ["barcode"])
    op.create_index("ix_my_store_products_hepsiburada_sku", "my_store_products", ["hepsiburada_sku"])
    op.create_index("ix_my_store_products_stock_code", "my_store_products", ["stock_code"])
    op.create_index("ix_my_store_products_brand", "my_store_products", ["brand"])
    op.create_index("ix_my_store_products_user_brand", "my_store_products", ["user_id", "brand"])


def downgrade() -> None:
    op.drop_table("my_store_products")
