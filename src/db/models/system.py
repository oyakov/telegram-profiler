import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, func, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base


class SystemProject(Base):
    """Top-level project/workspace (replaces removed projects table)."""
    __tablename__ = "system_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    telegram_folder_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<SystemProject {self.name!r}>"


class ExtractionLog(Base):
    __tablename__ = "extraction_log"
    __table_args__ = (
        # Composite index used by the already-processed correlated subquery
        Index("ix_extraction_log_source", "source_type", "source_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(255), nullable=False)
    model_used = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    extracted_data = Column(JSONB, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default="string")
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
