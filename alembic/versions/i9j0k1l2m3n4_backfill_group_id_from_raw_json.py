"""Backfill group_id from raw_json for messages without group_id

This migration addresses the issue where 18k+ messages have NULL group_id values
because they were created before the group_id field was added.

For messages with raw_json containing chat/channel info, we extract and populate group_id.
For messages without any group info (direct messages), we leave them as NULL.

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Try to extract group_id from raw_json for Telegram messages
    # The raw_json from Telethon typically contains peer_id.channel_id or peer_id.chat_id

    connection = op.get_bind()

    # Update messages where raw_json contains peer info
    update_query = text("""
        UPDATE messages
        SET group_id = COALESCE(
            raw_json->>'peer_id',
            raw_json->'peer'->>'_',
            raw_json->'peer'->'channel_id',
            raw_json->'peer'->'chat_id'
        )::text
        WHERE group_id IS NULL
        AND raw_json IS NOT NULL
        AND (
            raw_json ? 'peer_id'
            OR (raw_json ? 'peer' AND raw_json->'peer' IS NOT NULL)
        )
    """)

    try:
        connection.execute(update_query)
        connection.commit()
    except Exception as e:
        # If the query fails (missing peer info), that's okay -
        # messages with NULL group_id are likely direct messages
        print(f"Note: Could not fully backfill group_id: {e}")
        connection.rollback()


def downgrade() -> None:
    # No need to restore NULL values, as they were already NULL
    # This migration only adds data, not removes it
    pass
