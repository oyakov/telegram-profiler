"""Application configuration — loads from .env, overridden by DB settings table."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AppSettings(BaseSettings):
    """Core application settings loaded from environment variables."""

    # --- LLM ---
    llm_provider: str = Field("google", description="google | lmstudio")
    google_api_key: str = Field("", description="Google AI Studio API key")
    google_llm_model: str = Field("gemini-2.5-flash")
    lmstudio_base_url: str = Field("http://host.docker.internal:1234/v1")
    lmstudio_llm_model: str = Field("qwen3.5-3b")
    llm_temperature: float = Field(0.1)
    llm_max_tokens: int = Field(4096)

    # --- Embeddings ---
    embed_provider: str = Field("google", description="google | lmstudio")
    google_embed_model: str = Field("text-embedding-004")
    lmstudio_embed_model: str = Field("mxbai-embed-large-v1")
    embed_dimensions: int = Field(1024)

    # --- PostgreSQL ---
    postgres_host: str = Field("postgres")
    postgres_port: int = Field(5432)
    postgres_db: str = Field("crm")
    postgres_user: str = Field("crm")
    postgres_password: str = Field("changeme")

    # --- Redis ---
    redis_url: str = Field("redis://redis:6379/0")

    # --- Whisper ---
    whisper_url: str = Field("http://whisper:9000")
    whisper_model: str = Field("small")
    whisper_language: str = Field("auto")

    # --- Telegram ---
    telegram_api_id: str = Field("")
    telegram_api_hash: str = Field("")
    telegram_session_name: str = Field("crm_session")

    # --- Application ---
    app_port: int = Field(8000)
    log_level: str = Field("INFO")
    secret_key: str = Field("change-me-to-a-random-string")

    # --- Observability ---
    enable_metrics: bool = Field(True)
    prometheus_dir: str = Field("/tmp/prometheus_multiproc_dir")
    enable_json_logging: bool = Field(True)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> AppSettings:
    """Cached settings singleton."""
    return AppSettings()


class SettingsService:
    """CRUD operations for the settings table. DB values override .env."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value, cast to its declared type."""
        from src.db.models import Setting

        result = await self.session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting is None:
            return default
        return setting.get_typed_value()

    async def set(
        self,
        key: str,
        value: Any,
        value_type: str = "string",
        description: str | None = None,
        category: str = "general",
    ) -> Any:
        """Set a setting value (upsert)."""
        from src.db.models import Setting

        result = await self.session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()

        str_value = json.dumps(value) if value_type == "json" else str(value)

        if setting:
            setting.value = str_value
            setting.value_type = value_type
            if description:
                setting.description = description
        else:
            setting = Setting(
                key=key,
                value=str_value,
                value_type=value_type,
                description=description or "",
                category=category,
            )
            self.session.add(setting)

        await self.session.flush()
        return setting

    async def get_all(self, category: Optional[str] = None) -> list[dict]:
        """Get all settings, optionally filtered by category."""
        from src.db.models import Setting

        query = select(Setting)
        if category:
            query = query.where(Setting.category == category)
        query = query.order_by(Setting.category, Setting.key)

        result = await self.session.execute(query)
        settings = result.scalars().all()

        return [
            {
                "key": s.key,
                "value": s.get_typed_value(),
                "raw_value": s.value,
                "value_type": s.value_type,
                "description": s.description,
                "category": s.category,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in settings
        ]

    async def delete(self, key: str) -> bool:
        """Delete a setting. Returns True if it existed."""
        from src.db.models import Setting

        result = await self.session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            await self.session.delete(setting)
            await self.session.flush()
            return True
        return False
