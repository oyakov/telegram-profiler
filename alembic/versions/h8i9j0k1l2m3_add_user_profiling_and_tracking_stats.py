"""Add user_profiles table and tracking stats to channels and contacts.

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-05-08 14:00:00.000000

"""
from typing import Sequence, Optional
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'h8i9j0k1l2m3'
down_revision: Optional[str] = 'g7h8i9j0k1l2'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. Create user_profiles table
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id UUID NOT NULL,
            telegram_id VARCHAR(100) NOT NULL,
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            username VARCHAR(255),
            phone VARCHAR(50),
            bio TEXT,
            profile_photo_path VARCHAR(500),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            PRIMARY KEY (id),
            UNIQUE (telegram_id)
        )
    """)

    # 2. Add tracking fields to tracked_channels
    op.execute("ALTER TABLE tracked_channels ADD COLUMN IF NOT EXISTS total_messages_synced INTEGER DEFAULT 0")
    op.execute("ALTER TABLE tracked_channels ADD COLUMN IF NOT EXISTS oldest_message_id VARCHAR(255)")
    op.execute("ALTER TABLE tracked_channels ADD COLUMN IF NOT EXISTS oldest_message_date TIMESTAMP WITH TIME ZONE")

    # 3. Add tracking fields to contacts
    op.execute("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS is_tracked BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS total_messages_synced INTEGER DEFAULT 0")
    op.execute("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS oldest_message_id VARCHAR(255)")
    op.execute("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS oldest_message_date TIMESTAMP WITH TIME ZONE")


def downgrade() -> None:
    op.drop_table('user_profiles')
    op.execute("ALTER TABLE tracked_channels DROP COLUMN IF EXISTS total_messages_synced")
    op.execute("ALTER TABLE tracked_channels DROP COLUMN IF EXISTS oldest_message_id")
    op.execute("ALTER TABLE tracked_channels DROP COLUMN IF EXISTS oldest_message_date")
    op.execute("ALTER TABLE contacts DROP COLUMN IF EXISTS is_tracked")
    op.execute("ALTER TABLE contacts DROP COLUMN IF EXISTS total_messages_synced")
    op.execute("ALTER TABLE contacts DROP COLUMN IF EXISTS oldest_message_id")
    op.execute("ALTER TABLE contacts DROP COLUMN IF EXISTS oldest_message_date")
