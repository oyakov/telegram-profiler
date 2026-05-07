"""Add system_projects table and folder tags.

Revision ID: f3a1d9c2e5b8
Revises: ebc77584c4a1
Create Date: 2026-05-08 01:20:00.000000

"""
from typing import Sequence, Optional
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f3a1d9c2e5b8'
down_revision: Optional[str] = '4c2be852e89a'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. Create system_projects table (if it doesn't exist)
    # Note: Using checkfirst=True via op or raw SQL
    op.execute("""
        CREATE TABLE IF NOT EXISTS system_projects (
            id UUID NOT NULL, 
            name VARCHAR(255) NOT NULL, 
            db_name VARCHAR(255) NOT NULL, 
            description TEXT, 
            is_active BOOLEAN, 
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
            PRIMARY KEY (id), 
            UNIQUE (db_name)
        )
    """)

    # 2. Add 'tags' column to tracked_folders
    # We use a try-except pattern in SQL to avoid errors if column already exists
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name='tracked_folders' AND column_name='tags') THEN
                ALTER TABLE tracked_folders ADD COLUMN tags VARCHAR(255)[] DEFAULT '{}';
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.drop_column('tracked_folders', 'tags')
    op.drop_table('system_projects')
