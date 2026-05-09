"""Backfill project_id for all messages without project assignment

This migration assigns all existing messages to the first project (Personal)
since they were created before the single-database architecture.

Revision ID: k6l7m8n9o0
Revises: j5k6l7m8n9
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "k6l7m8n9o0"
down_revision: Union[str, None] = "j5k6l7m8n9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # Get the first project (Personal)
    result = connection.execute(text("""
        SELECT id FROM system_projects ORDER BY created_at LIMIT 1
    """))
    project = result.fetchone()
    
    if project:
        project_id = project[0]
        # Assign all messages without a project to the first project
        connection.execute(text(f"""
            UPDATE messages
            SET project_id = '{project_id}'
            WHERE project_id IS NULL
        """))


def downgrade() -> None:
    # Reset project_id to NULL for all messages
    connection = op.get_bind()
    connection.execute(text("""
        UPDATE messages
        SET project_id = NULL
    """))
