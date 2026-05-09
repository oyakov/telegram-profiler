"""Add is_personal and saved_at fields to contacts table

This migration adds support for tracking user-saved personal contacts
separately from automatically extracted contacts.

Revision ID: n9o0p1q2r3
Revises: m9n0o1p2q3
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n9o0p1q2r3"
down_revision: Union[str, None] = "m9n0o1p2q3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_personal column
    op.add_column('contacts', sa.Column('is_personal', sa.Boolean(), nullable=False, server_default='false'))

    # Add saved_at column
    op.add_column('contacts', sa.Column('saved_at', sa.DateTime(timezone=True), nullable=True))

    # Create index on is_personal for efficient filtering
    op.create_index('idx_contacts_is_personal', 'contacts', ['is_personal'])


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_contacts_is_personal', table_name='contacts')

    # Drop columns
    op.drop_column('contacts', 'saved_at')
    op.drop_column('contacts', 'is_personal')
