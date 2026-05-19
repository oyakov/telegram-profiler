"""Security and performance fixes from code review

- Add system_projects table (SystemProject model was missing)
- Add partial unique indexes on contacts(telegram_id) and contacts(telegram_username)
- Add is_extracted boolean column to messages (replaces expensive ExtractionLog subquery)
- Add composite index on extraction_log(source_type, source_id)
- Add pg_trgm extension + trigram indexes for fast keyword search on contacts
- Backfill messages.is_extracted = true where an ExtractionLog row already exists

Revision ID: s3t4u5v6w7
Revises: r2s3t4u5v6
Create Date: 2026-05-16 20:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "s3t4u5v6w7"
down_revision: Union[str, None] = "r2s3t4u5v6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. system_projects table ─────────────────────────────────────────────
    # Use raw SQL so the CREATE is idempotent if the table already exists
    # (can happen when a previous session created it outside Alembic).
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS system_projects (
            id UUID DEFAULT gen_random_uuid() NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            telegram_folder_id VARCHAR(255),
            is_active BOOLEAN DEFAULT true NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            PRIMARY KEY (id),
            CONSTRAINT uq_system_project_name UNIQUE (name)
        )
    """))

    # ── 2. Deduplicate contacts before adding unique indexes ─────────────────
    # Keep the oldest row for each non-NULL telegram_id duplicate.
    op.execute(sa.text("""
        DELETE FROM contacts c
        WHERE telegram_id IS NOT NULL
          AND c.id NOT IN (
            SELECT DISTINCT ON (telegram_id) id
            FROM contacts
            WHERE telegram_id IS NOT NULL
            ORDER BY telegram_id, created_at ASC
          )
    """))

    op.execute(sa.text("""
        DELETE FROM contacts c
        WHERE telegram_username IS NOT NULL
          AND c.id NOT IN (
            SELECT DISTINCT ON (telegram_username) id
            FROM contacts
            WHERE telegram_username IS NOT NULL
            ORDER BY telegram_username, created_at ASC
          )
    """))

    # ── 3. Partial unique indexes on contacts ────────────────────────────────
    op.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_contact_telegram_id
        ON contacts (telegram_id)
        WHERE telegram_id IS NOT NULL
    """))

    op.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_contact_telegram_username
        ON contacts (telegram_username)
        WHERE telegram_username IS NOT NULL
    """))

    # ── 4. messages.is_extracted column ──────────────────────────────────────
    op.execute(sa.text("""
        ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS is_extracted BOOLEAN NOT NULL DEFAULT false
    """))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_message_is_extracted ON messages (is_extracted)
    """))

    # Backfill: mark messages that already have an ExtractionLog entry as extracted
    op.execute(sa.text("""
        UPDATE messages m
        SET is_extracted = true
        WHERE EXISTS (
            SELECT 1 FROM extraction_log el
            WHERE el.source_type = 'unified_message'
              AND el.source_id = m.id::text
        )
    """))

    # ── 5. ExtractionLog composite index ─────────────────────────────────────
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_extraction_log_source
        ON extraction_log (source_type, source_id)
    """))

    # ── 6. Trigram indexes for fast keyword search ────────────────────────────
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_contact_firstname_trgm
        ON contacts USING GIN (first_name gin_trgm_ops)
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_contact_lastname_trgm
        ON contacts USING GIN (last_name gin_trgm_ops)
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_contact_company_trgm
        ON contacts USING GIN (company gin_trgm_ops)
    """))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_contact_company_trgm"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_contact_lastname_trgm"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_contact_firstname_trgm"))

    op.drop_index("ix_extraction_log_source", table_name="extraction_log")

    op.drop_index("ix_message_is_extracted", table_name="messages")
    op.drop_column("messages", "is_extracted")

    op.execute(sa.text("DROP INDEX IF EXISTS uq_contact_telegram_username"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_contact_telegram_id"))

    op.drop_table("system_projects")
