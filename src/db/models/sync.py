import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, func, ForeignKey, Integer, Float, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import Base

class SyncState(Base):
    __tablename__ = "sync_state"

    connector = Column(String(50), primary_key=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_message_id = Column(String(255), nullable=True)
    status = Column(String(20), default="idle")
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSONB, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ChannelSyncState(Base):
    __tablename__ = "channel_sync_state"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("tracked_channels.id", ondelete="CASCADE"), nullable=False)
    phase = Column(String(50), default="pending")
    earliest_message_date = Column(DateTime(timezone=True), nullable=True)
    estimated_total_messages = Column(Integer, nullable=True)
    messages_synced = Column(Integer, default=0)
    last_message_id = Column(String(255), nullable=True)
    last_message_date = Column(DateTime(timezone=True), nullable=True)
    progress_percent = Column(Float, default=0.0)
    eta_minutes = Column(Integer, nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_batch_id = Column(UUID(as_uuid=True), nullable=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    channel = relationship("TrackedChannel", back_populates="sync_state")
    batches = relationship("SyncBatchLog", back_populates="sync_state", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ChannelSyncState {self.channel_id} phase={self.phase}>"

class SyncBatchLog(Base):
    __tablename__ = "sync_batch_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_state_id = Column(UUID(as_uuid=True), ForeignKey("channel_sync_state.id", ondelete="CASCADE"), nullable=False)
    batch_number = Column(Integer, nullable=False)
    requested_offset = Column(Integer, nullable=False)
    messages_in_batch = Column(Integer, default=0)
    oldest_message_id = Column(String(255), nullable=True)
    newest_message_id = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    retry_attempt = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sync_state = relationship("ChannelSyncState", back_populates="batches")

    def __repr__(self) -> str:
        return f"<SyncBatchLog batch={self.batch_number} status={self.status}>"
