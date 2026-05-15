"""add unique constraint on source_message_id and missing indexes

Revision ID: r2s3t4u5v6
Revises: 4945a0a21a74
Create Date: 2026-05-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "r2s3t4u5v6"
down_revision: Union[str, None] = "4945a0a21a74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove duplicate source_message_id rows before adding the unique constraint.
    # Uses a window function (ROW_NUMBER) which is index-friendly and efficient on large tables.
    op.execute("""
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY source_message_id
                       ORDER BY created_at
                   ) AS rn
            FROM messages
            WHERE source_message_id IS NOT NULL
        )
        DELETE FROM messages
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
    """)

    op.create_unique_constraint(
        "uq_message_source_id", "messages", ["source_message_id"]
    )
    op.create_index("ix_message_group_id", "messages", ["group_id"])
    op.create_index("ix_contact_telegram_id", "contacts", ["telegram_id"])
    op.create_index("ix_contact_embedding_dirty", "contacts", ["embedding_dirty"])
    op.create_index("ix_msg_embedding_message_id", "message_embeddings", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_msg_embedding_message_id", table_name="message_embeddings")
    op.drop_index("ix_contact_embedding_dirty", table_name="contacts")
    op.drop_index("ix_contact_telegram_id", table_name="contacts")
    op.drop_index("ix_message_group_id", table_name="messages")
    op.drop_constraint("uq_message_source_id", "messages", type_="unique")
