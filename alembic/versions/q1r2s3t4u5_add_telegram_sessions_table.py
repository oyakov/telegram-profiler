"""Add telegram_sessions table for PostgreSQL-backed Telethon sessions

This migration creates a new table to store Telegram session data in PostgreSQL
instead of relying on SQLite, which causes database lock issues.

Revision ID: q1r2s3t4u5
Revises: 5dc186a914dc
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "q1r2s3t4u5"
down_revision: Union[str, None] = "5dc186a914dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'telegram_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_name', sa.String(255), nullable=False, unique=True),
        sa.Column('session_data', sa.Text(), nullable=False),
        sa.Column('auth_key', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_telegram_session_name', 'telegram_sessions', ['session_name'], unique=True)
    op.create_index('idx_telegram_session_active', 'telegram_sessions', ['is_active'])


def downgrade() -> None:
    op.drop_index('idx_telegram_session_active', table_name='telegram_sessions')
    op.drop_index('idx_telegram_session_name', table_name='telegram_sessions')
    op.drop_table('telegram_sessions')
