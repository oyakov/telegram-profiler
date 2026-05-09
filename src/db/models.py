"""SQLAlchemy models for Networking Brain CRM."""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class SystemProject(Base):
    """Project — represents a folder/category of messages and contacts."""
    __tablename__ = "system_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    telegram_folder_id = Column(String(100), nullable=True)  # Telegram folder ID if auto-created
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    folders = relationship("TrackedFolder", back_populates="project")

    __table_args__ = (
        Index("idx_project_telegram_folder_id", "telegram_folder_id"),
    )

    def __repr__(self) -> str:
        return f"<SystemProject {self.name}>"


class UserProfile(Base):
    """The profile of the currently logged-in Telegram user."""
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(String(100), unique=True, nullable=False)
    first_name = Column(String(255))
    last_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    profile_photo_path = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserProfile {self.first_name} ({self.telegram_id})>"


class TrackedFolder(Base):
    """A Telegram folder/label within a project."""
    __tablename__ = "tracked_folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("system_projects.id", ondelete="CASCADE"), nullable=False)
    telegram_folder_id = Column(String(100), nullable=True)  # Telegram folder ID
    name = Column(String(255), nullable=False)  # e.g., "BG Intel" or "Crypto"
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(String), default=list) # Keywords/tags
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("SystemProject", back_populates="folders")
    channels = relationship("TrackedChannel", back_populates="folder", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_folder_project_id", "project_id"),
        Index("idx_folder_telegram_folder_id", "telegram_folder_id"),
    )

    def __repr__(self) -> str:
        return f"<TrackedFolder {self.name}>"


class TrackedChannel(Base):
    """A formal concept of a tracked Telegram channel or group."""
    __tablename__ = "tracked_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("tracked_folders.id", ondelete="CASCADE"), nullable=True)
    telegram_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    entity_type = Column(String(50), nullable=False)  # channel|group
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    
    # Tracking Stats
    total_messages_synced = Column(Integer, default=0)
    oldest_message_id = Column(String(255), nullable=True)
    oldest_message_date = Column(DateTime(timezone=True), nullable=True)
    
    metadata_json = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    folder = relationship("TrackedFolder", back_populates="channels")

    __table_args__ = (
        Index("idx_tracked_channels_telegram_id", "telegram_id"),
        Index("idx_tracked_channels_folder_id", "folder_id"),
    )

    def __repr__(self) -> str:
        return f"<TrackedChannel {self.title or self.telegram_id}>"


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("system_projects.id", ondelete="CASCADE"), nullable=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    company = Column(String(255))
    position = Column(String(255))
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    telegram_id = Column(String(100), nullable=True)
    telegram_username = Column(String(100), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    source = Column(String(50), nullable=False, default="manual")  # telegram|excel|crm|social|manual
    interests = Column(ARRAY(Text), default=list)
    skills = Column(ARRAY(Text), default=list)
    notes = Column(Text, nullable=True)
    context = Column(Text, nullable=True)  # meeting context, how we met, etc.
    facts_json = Column(JSONB, default=dict)  # arbitrary structured facts from LLM

    # Lead Specific Fields
    is_lead = Column(Boolean, default=False)
    lead_score = Column(Float, default=0.0)
    our_channel_ratio = Column(Float, default=0.0)  # % of ads in "our" channel
    lead_context = Column(JSONB, default=dict)  # Metadata about lead/ad purchases

    # User Profiling Fields
    bio = Column(Text, nullable=True)
    profile_photo_path = Column(String(500), nullable=True)
    is_bot = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    last_enriched_at = Column(DateTime(timezone=True), nullable=True)
    telegram_metadata = Column(JSONB, default=dict)

    # Tracking Stats
    is_tracked = Column(Boolean, default=False)
    total_messages_synced = Column(Integer, default=0)
    oldest_message_id = Column(String(255), nullable=True)
    oldest_message_date = Column(DateTime(timezone=True), nullable=True)

    embedding = Column(Vector(1024), nullable=True)
    embedding_dirty = Column(Boolean, default=True)
    last_interaction = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")
    voice_notes = relationship("VoiceNote", back_populates="contact", cascade="all, delete-orphan")
    associated_messages = relationship("MessageContact", back_populates="contact", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_contacts_project_id", "project_id"),
        Index("idx_contacts_source", "source"),
        Index("idx_contacts_embedding_dirty", "embedding_dirty"),
        Index("idx_contacts_last_interaction", "last_interaction"),
    )

    def __repr__(self) -> str:
        return f"<Contact {self.first_name} {self.last_name} ({self.source})>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("system_projects.id", ondelete="CASCADE"), nullable=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("tracked_folders.id", ondelete="SET NULL"), nullable=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(50), nullable=False)  # telegram|crm|social
    source_message_id = Column(String(255), nullable=True)  # external ID
    direction = Column(String(10), default="incoming")  # incoming|outgoing
    content = Column(Text, nullable=True)
    media_type = Column(String(50), nullable=True)  # text|voice|image|video|document
    group_id = Column(String(100), nullable=True)  # Telegram channel/group ID
    group_name = Column(String(255), nullable=True)
    raw_json = Column(JSONB, nullable=True)  # original API payload
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    contact = relationship("Contact", back_populates="messages")
    embeddings = relationship("MessageEmbedding", back_populates="message", cascade="all, delete-orphan")
    associated_contacts = relationship("MessageContact", back_populates="message", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_messages_project_id", "project_id"),
        Index("idx_messages_folder_id", "folder_id"),
        Index("idx_messages_contact_id", "contact_id"),
        Index("idx_messages_timestamp", "timestamp"),
        Index("idx_messages_source", "source"),
        Index("idx_messages_source_message_id", "source_message_id", unique=True),
        Index("idx_messages_group_id", "group_id"),
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} from {self.source}>"


class MessageContact(Base):
    """Association table linking messages to multiple contacts with roles."""
    __tablename__ = "message_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # sender|lead|mention
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="associated_contacts")
    contact = relationship("Contact", back_populates="associated_messages")

    __table_args__ = (
        Index("idx_msg_contact_message_id", "message_id"),
        Index("idx_msg_contact_contact_id", "contact_id"),
        Index("idx_msg_contact_role", "role"),
        # Unique constraint to prevent duplicate links of same role
        sa.UniqueConstraint("message_id", "contact_id", "role", name="uq_message_contact_role"),
    )

    def __repr__(self) -> str:
        return f"<MessageContact msg={self.message_id} contact={self.contact_id} role={self.role}>"



class MessageEmbedding(Base):
    __tablename__ = "message_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, default=0)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="embeddings")

    __table_args__ = (
        Index("idx_msg_embed_message_id", "message_id"),
    )

    def __repr__(self) -> str:
        return f"<MessageEmbedding msg={self.message_id} chunk={self.chunk_index}>"


class VoiceNote(Base):
    __tablename__ = "voice_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("system_projects.id", ondelete="CASCADE"), nullable=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True)
    file_path = Column(String(500), nullable=False)
    duration_seconds = Column(Float, nullable=True)
    transcript = Column(Text, nullable=True)
    source = Column(String(50), default="telegram")  # telegram|upload
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    contact = relationship("Contact", back_populates="voice_notes")

    __table_args__ = (
        Index("idx_voice_notes_project_id", "project_id"),
        Index("idx_voice_notes_contact_id", "contact_id"),
        Index("idx_voice_notes_processed", "processed"),
    )


class ExtractionLog(Base):
    __tablename__ = "extraction_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50), nullable=False)  # message|voice|excel_row|social
    source_id = Column(String(255), nullable=False)
    model_used = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    extracted_data = Column(JSONB, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_extraction_log_source", "source_type", "source_id"),
        Index("idx_extraction_log_created", "created_at"),
    )


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default="string")  # string|int|float|bool|json
    description = Column(Text, nullable=True)
    category = Column(String(50), default="general")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def get_typed_value(self):
        """Return value cast to the appropriate Python type."""
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        return self.value


class SyncState(Base):
    __tablename__ = "sync_state"

    connector = Column(String(50), primary_key=True)  # telegram|excel|crm|social
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_message_id = Column(String(255), nullable=True)
    status = Column(String(20), default="idle")  # idle|running|error
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSONB, default=dict)  # connector-specific state
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LeadSearch(Base):
    """Saved lead search/profile tracker."""
    __tablename__ = "lead_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    profile_filter = Column(JSONB, nullable=False)  # Serialized LeadProfileFilter
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_result_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_lead_searches_is_active", "is_active"),
        Index("idx_lead_searches_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<LeadSearch {self.name}>"
