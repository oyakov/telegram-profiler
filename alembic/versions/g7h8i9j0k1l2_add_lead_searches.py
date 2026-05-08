"""Add lead_searches table for tracked lead searches.

Revision ID: g7h8i9j0k1l2
Revises: f3a1d9c2e5b8
Create Date: 2026-05-08 12:00:00.000000

"""
from typing import Sequence, Optional
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: Optional[str] = 'f3a1d9c2e5b8'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # Create lead_searches table
    op.execute("""
        CREATE TABLE IF NOT EXISTS lead_searches (
            id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            profile_filter JSONB NOT NULL,
            is_active BOOLEAN DEFAULT true,
            last_run_at TIMESTAMP WITH TIME ZONE,
            last_result_count INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            PRIMARY KEY (id)
        )
    """)

    # Add indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_lead_searches_is_active
        ON lead_searches (is_active)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_lead_searches_created
        ON lead_searches (created_at)
    """)


def downgrade() -> None:
    op.drop_table('lead_searches')
