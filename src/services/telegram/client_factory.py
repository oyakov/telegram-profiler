"""Factory for creating Telethon client instances with PostgreSQL-backed sessions."""

from __future__ import annotations
import structlog
from typing import Optional
from telethon import TelegramClient
from src.core.config import get_settings
from src.connectors.telethon_postgres_session import PostgresTelegramSession

logger = structlog.get_logger()

class TelegramClientFactory:
    """Creates Telethon client instances with correct session and config."""

    def __init__(self, db_name: str | None = None):
        self.settings = get_settings()
        self.db_name = db_name or self.settings.postgres_db
        self.pg_session = PostgresTelegramSession(
            session_name=self.settings.telegram_session_name, 
            db_name=self.db_name
        )

    async def get_client(self) -> TelegramClient:
        """Create a new Telethon client instance."""
        string_session = await self.pg_session.get_string_session()
        return TelegramClient(
            string_session,
            int(self.settings.telegram_api_id),
            self.settings.telegram_api_hash
        )

    async def save_session(self, user_id: Optional[str] = None):
        """Save current session to PostgreSQL."""
        await self.pg_session.save_session_data(user_id=user_id)

    async def delete_session(self):
        """Delete session from PostgreSQL."""
        await self.pg_session.delete_session()

    def clear_cache(self):
        """Clear session cache."""
        self.pg_session.clear_cache()
