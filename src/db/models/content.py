import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, func, ForeignKey, ARRAY, Integer, Float, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .base import Base

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(255))
    last_name = Column(String(255))
    company = Column(String(255))
    position = Column(String(255))
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    telegram_id = Column(String(100), nullable=True)
    telegram_username = Column(String(100), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    source = Column(String(50), nullable=False, default="manual")
    interests = Column(ARRAY(Text), default=list)
    skills = Column(ARRAY(Text), default=list)
    notes = Column(Text, nullable=True)
    context = Column(Text, nullable=True)
    facts_json = Column(JSONB, default=dict)

    is_lead = Column(Boolean, default=False)
    lead_score = Column(Float, default=0.0)
    our_channel_ratio = Column(Float, default=0.0)
    lead_context = Column(JSONB, default=dict)

    bio = Column(Text, nullable=True)
    profile_photo_path = Column(String(500), nullable=True)
    is_bot = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    last_enriched_at = Column(DateTime(timezone=True), nullable=True)
    telegram_metadata = Column(JSONB, default=dict)

    is_tracked = Column(Boolean, default=False)
    total_messages_synced = Column(Integer, default=0)
    oldest_message_id = Column(String(255), nullable=True)
    oldest_message_date = Column(DateTime(timezone=True), nullable=True)

    is_personal = Column(Boolean, default=False, index=True)
    saved_at = Column(DateTime(timezone=True), nullable=True)

    embedding = Column(Vector(1024), nullable=True)
    embedding_dirty = Column(Boolean, default=True)
    last_interaction = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")
    voice_notes = relationship("VoiceNote", back_populates="contact", cascade="all, delete-orphan")
    associated_messages = relationship("MessageContact", back_populates="contact", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Contact {self.first_name} {self.last_name} ({self.source})>"

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("tracked_folders.id", ondelete="SET NULL"), nullable=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(50), nullable=False)
    source_message_id = Column(String(255), nullable=True)
    direction = Column(String(10), default="incoming")
    content = Column(Text, nullable=True)
    media_type = Column(String(50), nullable=True)
    group_id = Column(String(100), nullable=True)
    group_name = Column(String(255), nullable=True)
    raw_json = Column(JSONB, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contact = relationship("Contact", back_populates="messages")
    embeddings = relationship("MessageEmbedding", back_populates="message", cascade="all, delete-orphan")
    associated_contacts = relationship("MessageContact", back_populates="message", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Message {self.id} from {self.source}>"

class MessageContact(Base):
    __tablename__ = "message_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="associated_contacts")
    contact = relationship("Contact", back_populates="associated_messages")

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

    message = relationship("Message", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<MessageEmbedding msg={self.message_id} chunk={self.chunk_index}>"

class VoiceNote(Base):
    __tablename__ = "voice_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True)
    file_path = Column(String(500), nullable=False)
    duration_seconds = Column(Float, nullable=True)
    transcript = Column(Text, nullable=True)
    source = Column(String(50), default="telegram")
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contact = relationship("Contact", back_populates="voice_notes")
