"""PostgreSQL-backed Telethon session storage."""

from __future__ import annotations

import asyncio
import structlog
from typing import Optional

from telethon.sessions import StringSession
from sqlalchemy import select
from src.db.database import get_session
from src.db.models import TelegramSession

logger = structlog.get_logger()


class PostgresTelegramSession:
    """
    Manages Telethon StringSession data in PostgreSQL.
    StringSession is lightweight and doesn't require SQLite.
    """

    def __init__(self, session_name: str = "telethon_session", db_name: str | None = None):
        from src.core.config import get_settings
        self.session_name = session_name
        self.db_name = db_name or get_settings().postgres_db
        self._cache: Optional[StringSession] = None
        self._lock = asyncio.Lock()

    async def get_string_session(self) -> StringSession:
        """Load StringSession from PostgreSQL or create new one."""
        async with self._lock:
            # Check cache first
            if self._cache is not None:
                return self._cache

            async with get_session(db_name=self.db_name) as db_session:
                # Query PostgreSQL
                result = await db_session.execute(
                    select(TelegramSession).where(
                        TelegramSession.session_name == self.session_name
                    )
                )
                tg_session = result.scalar_one_or_none()

                if tg_session and tg_session.session_data:
                    # Restore from DB
                    self._cache = StringSession(tg_session.session_data)
                    logger.info(
                        "telegram_session_loaded",
                        session_name=self.session_name,
                        user_id=tg_session.user_id,
                    )
                else:
                    # Create new
                    self._cache = StringSession()
                    logger.info(
                        "telegram_session_created_new",
                        session_name=self.session_name,
                    )

            return self._cache

    async def save_session_data(self, user_id: Optional[str] = None):
        """Save StringSession data to PostgreSQL."""
        if self._cache is None:
            return

        try:
            async with self._lock:
                session_str = self._cache.save()

                async with get_session(db_name=self.db_name) as db_session:
                    # Find or create session record
                    result = await db_session.execute(
                        select(TelegramSession).where(
                            TelegramSession.session_name == self.session_name
                        )
                    )
                    tg_session = result.scalar_one_or_none()

                    if tg_session:
                        # Update existing
                        tg_session.session_data = session_str
                        if user_id:
                            tg_session.user_id = user_id
                        tg_session.is_active = True
                    else:
                        # Create new record
                        tg_session = TelegramSession(
                            session_name=self.session_name,
                            session_data=session_str,
                            user_id=user_id,
                            is_active=True,
                        )
                        db_session.add(tg_session)

                    await db_session.commit()
                    logger.info(
                        "telegram_session_saved",
                        session_name=self.session_name,
                        user_id=user_id,
                    )
        except Exception as e:
            logger.error(
                "telegram_session_save_failed",
                session_name=self.session_name,
                error=str(e),
            )

    async def delete_session(self):
        """Delete session from PostgreSQL and clear cache."""
        try:
            async with self._lock:
                async with get_session(db_name=self.db_name) as db_session:
                    result = await db_session.execute(
                        select(TelegramSession).where(
                            TelegramSession.session_name == self.session_name
                        )
                    )
                    tg_session = result.scalar_one_or_none()
                    if tg_session:
                        await db_session.delete(tg_session)
                        await db_session.commit()
                        logger.info(
                            "telegram_session_deleted",
                            session_name=self.session_name,
                        )

                self._cache = None
        except Exception as e:
            logger.error(
                "telegram_session_delete_failed",
                session_name=self.session_name,
                error=str(e),
            )

    def clear_cache(self):
        """Clear in-memory cache (session data stays in DB)."""
        self._cache = None
