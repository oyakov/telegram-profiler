"""Initial schema — all tables + pgvector

Revision ID: 001_initial
Revises: None
Create Date: 2026-03-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- contacts ---
    op.create_table(
        "contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("first_name", sa.String(255)),
        sa.Column("last_name", sa.String(255)),
        sa.Column("company", sa.String(255)),
        sa.Column("position", sa.String(255)),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("telegram_id", sa.String(100), unique=True, nullable=True),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("interests", ARRAY(sa.Text), server_default="{}"),
        sa.Column("skills", ARRAY(sa.Text), server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("context", sa.Text, nullable=True),
        sa.Column("facts_json", JSONB, server_default="{}"),
        sa.Column("embedding_dirty", sa.Boolean, server_default="true"),
        sa.Column("last_interaction", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Add vector column (can't use sa.Column for vector type easily)
    op.execute("ALTER TABLE contacts ADD COLUMN embedding vector(768)")
    op.create_index("idx_contacts_source", "contacts", ["source"])
    op.create_index("idx_contacts_embedding_dirty", "contacts", ["embedding_dirty"])
    op.create_index("idx_contacts_last_interaction", "contacts", ["last_interaction"])

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_message_id", sa.String(255), nullable=True),
        sa.Column("direction", sa.String(10), server_default="incoming"),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("media_type", sa.String(50), nullable=True),
        sa.Column("raw_json", JSONB, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_messages_contact_id", "messages", ["contact_id"])
    op.create_index("idx_messages_timestamp", "messages", ["timestamp"])
    op.create_index("idx_messages_source", "messages", ["source"])
    op.create_index("idx_messages_source_message_id", "messages", ["source_message_id"], unique=True)

    # --- message_embeddings ---
    op.create_table(
        "message_embeddings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, server_default="0"),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE message_embeddings ADD COLUMN embedding vector(768) NOT NULL")
    op.create_index("idx_msg_embed_message_id", "message_embeddings", ["message_id"])

    # --- voice_notes ---
    op.create_table(
        "voice_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("source", sa.String(50), server_default="telegram"),
        sa.Column("processed", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_voice_notes_contact_id", "voice_notes", ["contact_id"])
    op.create_index("idx_voice_notes_processed", "voice_notes", ["processed"])

    # --- extraction_log ---
    op.create_table(
        "extraction_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=True),
        sa.Column("completion_tokens", sa.Integer, nullable=True),
        sa.Column("extracted_data", JSONB, nullable=True),
        sa.Column("success", sa.Boolean, server_default="true"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("processing_time_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_extraction_log_source", "extraction_log", ["source_type", "source_id"])
    op.create_index("idx_extraction_log_created", "extraction_log", ["created_at"])

    # --- settings ---
    op.create_table(
        "settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("value_type", sa.String(20), server_default="string"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), server_default="general"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- sync_state ---
    op.create_table(
        "sync_state",
        sa.Column("connector", sa.String(50), primary_key=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), server_default="idle"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- HNSW indexes for vector search (work on empty tables unlike IVFFlat) ---
    op.execute("""
        CREATE INDEX idx_contacts_embedding_hnsw
        ON contacts USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX idx_msg_embed_embedding_hnsw
        ON message_embeddings USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Seed default settings
    op.execute("""
        INSERT INTO settings (key, value, value_type, description, category) VALUES
        ('telegram_sync_enabled', 'false', 'bool', 'Enable Telegram connector', 'connectors'),
        ('telegram_chat_whitelist', '[]', 'json', 'List of Telegram chat IDs to sync', 'connectors'),
        ('telegram_initial_limit', '100', 'int', 'Messages to fetch on initial sync per chat', 'connectors'),
        ('excel_auto_import', 'false', 'bool', 'Auto-import new Excel files from uploads/', 'connectors'),
        ('crm_sync_enabled', 'false', 'bool', 'Enable CRM REST API connector', 'connectors'),
        ('crm_api_url', '', 'string', 'CRM API base URL', 'connectors'),
        ('crm_api_key', '', 'string', 'CRM API key', 'connectors'),
        ('social_sync_enabled', 'false', 'bool', 'Enable social media scraping', 'connectors'),
        ('dedup_cosine_threshold', '0.85', 'float', 'Cosine similarity threshold for deduplication', 'processing'),
        ('embedding_batch_size', '50', 'int', 'Batch size for embedding generation', 'processing'),
        ('llm_extraction_enabled', 'true', 'bool', 'Enable LLM-based fact extraction', 'processing'),
        ('sync_interval_minutes', '30', 'int', 'Interval between automatic syncs', 'scheduling')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("sync_state")
    op.drop_table("settings")
    op.drop_table("extraction_log")
    op.drop_table("voice_notes")
    op.drop_table("message_embeddings")
    op.drop_table("messages")
    op.drop_table("contacts")
    op.execute("DROP EXTENSION IF EXISTS vector")
