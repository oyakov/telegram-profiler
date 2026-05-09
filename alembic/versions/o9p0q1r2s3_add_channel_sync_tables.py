"""Add channel sync state and batch log tables

This migration adds tables for tracking Telegram channel history download progress:
- channel_sync_state: Tracks overall sync progress per channel
- sync_batch_log: Audit trail for each batch download

Revision ID: o9p0q1r2s3
Revises: n9o0p1q2r3
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "o9p0q1r2s3"
down_revision: Union[str, None] = "n9o0p1q2r3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create channel_sync_state table
    op.create_table(
        'channel_sync_state',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phase', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('earliest_message_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_total_messages', sa.Integer(), nullable=True),
        sa.Column('messages_synced', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_message_id', sa.String(255), nullable=True),
        sa.Column('last_message_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('eta_minutes', sa.Integer(), nullable=True),
        sa.Column('estimated_completion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_batch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['tracked_channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_channel_sync_channel_id', 'channel_sync_state', ['channel_id'])
    op.create_index('idx_channel_sync_phase', 'channel_sync_state', ['phase'])
    op.create_index('idx_channel_sync_updated', 'channel_sync_state', ['updated_at'])

    # Create sync_batch_log table
    op.create_table(
        'sync_batch_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_state_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('batch_number', sa.Integer(), nullable=False),
        sa.Column('requested_offset', sa.Integer(), nullable=False),
        sa.Column('messages_in_batch', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('oldest_message_id', sa.String(255), nullable=True),
        sa.Column('newest_message_id', sa.String(255), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_attempt', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['sync_state_id'], ['channel_sync_state.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch_sync_state_id', 'sync_batch_log', ['sync_state_id'])
    op.create_index('idx_batch_status', 'sync_batch_log', ['status'])
    op.create_index('idx_batch_number', 'sync_batch_log', ['sync_state_id', 'batch_number'])


def downgrade() -> None:
    op.drop_index('idx_batch_number', table_name='sync_batch_log')
    op.drop_index('idx_batch_status', table_name='sync_batch_log')
    op.drop_index('idx_batch_sync_state_id', table_name='sync_batch_log')
    op.drop_table('sync_batch_log')

    op.drop_index('idx_channel_sync_updated', table_name='channel_sync_state')
    op.drop_index('idx_channel_sync_phase', table_name='channel_sync_state')
    op.drop_index('idx_channel_sync_channel_id', table_name='channel_sync_state')
    op.drop_table('channel_sync_state')
