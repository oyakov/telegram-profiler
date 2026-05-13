import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, func, ForeignKey, ARRAY, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import Base

class TrackedFolder(Base):
    """A Telegram folder/label."""
    __tablename__ = "tracked_folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_folder_id = Column(String(100), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(String), default=list)
    is_active = Column(Boolean, default=True)

    cached_channels = Column(ARRAY(String), default=list)
    last_scan_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    channels = relationship("TrackedChannel", back_populates="folder", cascade="all, delete-orphan")

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
    entity_type = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    total_messages_synced = Column(Integer, default=0)
    oldest_message_id = Column(String(255), nullable=True)
    oldest_message_date = Column(DateTime(timezone=True), nullable=True)

    metadata_json = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    folder = relationship("TrackedFolder", back_populates="channels")
    sync_state = relationship("ChannelSyncState", back_populates="channel", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<TrackedChannel {self.title or self.telegram_id}>"
