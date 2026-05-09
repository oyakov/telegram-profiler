"""Add campaigns and campaign_messages tables for bulk messaging feature

This migration adds support for creating and managing bulk message campaigns
with contact selection from files or database.

Revision ID: o0p1q2r3s4
Revises: n9o0p1q2r3
Create Date: 2026-05-09 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "o0p1q2r3s4"
down_revision: Union[str, None] = "n9o0p1q2r3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)
    existing_tables = inspector.get_table_names()

    # Create campaigns table if it doesn't exist
    if 'campaigns' not in existing_tables:
        op.create_table(
            'campaigns',
            sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.func.gen_random_uuid()),
            sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
            sa.Column('total_contacts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('sent_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['project_id'], ['system_projects.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('project_id', 'name', name='uq_campaign_project_name'),
        )
        op.create_index('idx_campaigns_project_id', 'campaigns', ['project_id'])
        op.create_index('idx_campaigns_status', 'campaigns', ['status'])
        op.create_index('idx_campaigns_created', 'campaigns', ['created_at'])

    # Create campaign_messages table if it doesn't exist
    if 'campaign_messages' not in existing_tables:
        op.create_table(
            'campaign_messages',
            sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.func.gen_random_uuid()),
            sa.Column('campaign_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('contact_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('campaign_id', 'contact_id', name='uq_campaign_contact'),
        )
        op.create_index('idx_campaign_messages_campaign_id', 'campaign_messages', ['campaign_id'])
        op.create_index('idx_campaign_messages_contact_id', 'campaign_messages', ['contact_id'])
        op.create_index('idx_campaign_messages_status', 'campaign_messages', ['status'])


def downgrade() -> None:
    # Drop campaign_messages table
    op.drop_table('campaign_messages')

    # Drop campaigns table
    op.drop_table('campaigns')
