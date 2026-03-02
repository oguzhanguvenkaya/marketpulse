"""Add chat_conversations and chat_messages tables.

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_conversations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), server_default='Yeni Sohbet'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_chat_conversations_user_id', 'chat_conversations', ['user_id'])

    op.create_table(
        'chat_messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('chat_conversations.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('tool_calls', sa.JSON, nullable=True),
        sa.Column('tool_call_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_chat_messages_conversation_id', 'chat_messages', ['conversation_id'])


def downgrade() -> None:
    op.drop_index('ix_chat_messages_conversation_id', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index('ix_chat_conversations_user_id', table_name='chat_conversations')
    op.drop_table('chat_conversations')
