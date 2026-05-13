import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

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

class TelegramSession(Base):
    """Telegram Telethon session stored in PostgreSQL instead of SQLite."""
    __tablename__ = "telegram_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_name = Column(String(255), unique=True, nullable=False)  # e.g., "telethon_session"
    session_data = Column(Text, nullable=False)  # Serialized StringSession data
    auth_key = Column(Text, nullable=True)  # Raw auth key for session
    user_id = Column(String(100), nullable=True)  # Telegram user ID when authorized
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<TelegramSession {self.session_name} user={self.user_id}>"
