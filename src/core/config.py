"""Application configuration — loads from .env, overridden by DB settings table."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


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
    dashboard_port: int = Field(8501)
    log_level: str = Field("INFO")
    secret_key: str = Field("change-me-to-a-random-string")

    # --- Observability ---
    enable_metrics: bool = Field(True)
    prometheus_dir: str = Field("/tmp/prometheus_multiproc_dir")
    opensearch_url: str = Field("http://opensearch:9200")
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
