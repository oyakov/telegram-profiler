"""Assign messages to folders based on their channel/group_id

This migration:
1. Finds messages by their group_id (matching channel telegram_id)
2. Assigns them to the correct folder and project

Revision ID: m9n0o1p2q3
Revises: l8m9n0o1p2
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "m9n0o1p2q3"
down_revision: Union[str, None] = "l8m9n0o1p2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # Update messages with folder_id and project_id based on their group_id matching channel telegram_id
    update_query = text("""
        UPDATE messages m
        SET 
            folder_id = tc.folder_id,
            project_id = tf.project_id
        FROM tracked_channels tc
        JOIN tracked_folders tf ON tc.folder_id = tf.id
        WHERE m.group_id = tc.telegram_id::text
        AND m.folder_id IS NULL
        AND tc.folder_id IS NOT NULL
    """)
    
    try:
        result = connection.execute(update_query)
        connection.commit()
        print(f"Updated {result.rowcount} messages with folder and project assignments")
    except Exception as e:
        print(f"Error updating messages: {e}")
        connection.rollback()


def downgrade() -> None:
    # Reset folder_id to NULL for messages that were assigned in this migration
    # We keep project_id since it should remain
    connection = op.get_bind()
    connection.execute(text("""
        UPDATE messages
        SET folder_id = NULL
        WHERE folder_id IN (SELECT id FROM tracked_folders)
    """))
    connection.commit()
