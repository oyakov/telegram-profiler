"""Assign tracked folders to their corresponding projects

This migration matches folders to projects by name and updates
all messages in those folders to have the correct project_id.

Revision ID: l8m9n0o1p2
Revises: k6l7m8n9o0
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "l8m9n0o1p2"
down_revision: Union[str, None] = "k6l7m8n9o0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # For each folder, find the matching project and update the folder's project_id
    # Also update all messages in that folder to have the correct project_id

    # Get all folders with their names
    folders = connection.execute(text("""
        SELECT id, name FROM tracked_folders WHERE project_id IS NULL
    """)).fetchall()

    for folder_id, folder_name in folders:
        # Find the project with matching name
        project = connection.execute(text("""
            SELECT id FROM system_projects WHERE name = %s
        """), [folder_name]).fetchone()

        if project:
            project_id = project[0]

            # Update the folder to assign it to this project
            connection.execute(text("""
                UPDATE tracked_folders
                SET project_id = :project_id
                WHERE id = :folder_id
            """), {"project_id": project_id, "folder_id": folder_id})

            # Update all messages with this folder_id to have the correct project_id
            connection.execute(text("""
                UPDATE messages
                SET project_id = :project_id
                WHERE folder_id = :folder_id
            """), {"project_id": project_id, "folder_id": folder_id})


def downgrade() -> None:
    # Reset project_id for folders and messages
    connection = op.get_bind()
    connection.execute(text("""
        UPDATE tracked_folders SET project_id = NULL
    """))
    connection.execute(text("""
        UPDATE messages SET project_id = NULL WHERE folder_id IN (SELECT id FROM tracked_folders)
    """))
