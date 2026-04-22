"""rename_ad_buyer_to_lead

Revision ID: 4c2be852e89a
Revises: ebc77584c4a1
Create Date: 2026-04-21 03:02:12.424040
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '4c2be852e89a'
down_revision: Union[str, None] = 'ebc77584c4a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename columns in contacts table
    op.alter_column('contacts', 'is_ad_buyer', new_column_name='is_lead')
    op.alter_column('contacts', 'ad_buyer_score', new_column_name='lead_score')
    op.alter_column('contacts', 'ad_context', new_column_name='lead_context')
    
    # Update roles in message_contacts table
    op.execute("UPDATE message_contacts SET role = 'lead' WHERE role = 'ad_buyer'")


def downgrade() -> None:
    # Revert roles in message_contacts table
    op.execute("UPDATE message_contacts SET role = 'ad_buyer' WHERE role = 'lead'")
    
    # Rename columns back
    op.alter_column('contacts', 'is_lead', new_column_name='is_ad_buyer')
    op.alter_column('contacts', 'lead_score', new_column_name='ad_buyer_score')
    op.alter_column('contacts', 'lead_context', new_column_name='ad_context')
