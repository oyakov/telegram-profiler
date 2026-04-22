"""add group fields to messages

Revision ID: 6707bc82e388
Revises: b2507f0a251d
Create Date: 2026-04-15 15:51:46.244136
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6707bc82e388"
down_revision: Union[str, None] = "b2507f0a251d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("messages", sa.Column("group_id", sa.String(length=100), nullable=True))
    op.add_column("messages", sa.Column("group_name", sa.String(length=255), nullable=True))
    op.create_index("idx_messages_group_id", "messages", ["group_id"])

def downgrade() -> None:
    op.drop_index("idx_messages_group_id", table_name="messages")
    op.drop_column("messages", "group_name")
    op.drop_column("messages", "group_id")
