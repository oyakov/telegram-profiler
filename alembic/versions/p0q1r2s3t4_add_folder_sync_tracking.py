"""Add folder sync tracking fields for orchestrator

This migration adds columns to tracked_folders for change detection:
- cached_channels: Store current channel list to detect changes
- last_scan_at: Track when we last synced from Telegram

Revision ID: p0q1r2s3t4
Revises: o9p0q1r2s3
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "p0q1r2s3t4"
down_revision: Union[str, None] = "o9p0q1r2s3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tracked_folders', sa.Column('cached_channels', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'))
    op.add_column('tracked_folders', sa.Column('last_scan_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('tracked_folders', 'last_scan_at')
    op.drop_column('tracked_folders', 'cached_channels')
