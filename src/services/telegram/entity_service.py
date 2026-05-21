"""Telegram entity and contact service implementation."""

import structlog
import asyncio
from typing import Any
from sqlalchemy import select
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from telethon.errors import RPCError

from src.db.database import get_session
from src.db.models import Contact, UserProfile
from src.services.telegram.base import TelegramEntityInterface
from src.services.telegram.client_factory import TelegramClientFactory

logger = structlog.get_logger()

# Common retry decorator for Telegram network/RPC operations
telegram_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, asyncio.TimeoutError, RPCError)),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        "telegram_operation_retry",
        attempt=retry_state.attempt_number,
        exception=str(retry_state.outcome.exception()),
    )
)

class TelegramEntityService(TelegramEntityInterface):
    """Handles resolution and persistence of Telegram entities (users, channels)."""

    def __init__(self, client_factory: TelegramClientFactory):
        self.factory = client_factory
        self.db_name = client_factory.db_name

    async def get_or_create_contact(self, session: Any, sender: Any, is_channel: bool = False) -> Contact:
        """Resolve a Telethon sender entity to a DB Contact."""
        if sender is None:
            result = await session.execute(select(Contact).where(Contact.telegram_id == "system").limit(1))
            contact = result.scalar_one_or_none()
            if not contact:
                contact = Contact(first_name="System", telegram_id="system", source="telegram")
                session.add(contact)
                await session.flush()
            return contact

        tg_id = str(sender.id)
        username = getattr(sender, "username", None) or None

        # 1. Lookup by telegram_id (primary identifier)
        result = await session.execute(select(Contact).where(Contact.telegram_id == tg_id).limit(1))
        contact = result.scalar_one_or_none()

        # 2. Fallback: lookup by telegram_username to avoid hitting uq_contact_telegram_username
        if not contact and username:
            result2 = await session.execute(
                select(Contact).where(Contact.telegram_username == username).limit(1)
            )
            contact = result2.scalar_one_or_none()
            if contact:
                # Sync the telegram_id now that we know it
                contact.telegram_id = tg_id

        if not contact:
            contact = Contact(
                first_name=getattr(sender, "title", "Unknown") if is_channel else getattr(sender, "first_name", "Unknown") or "Unknown",
                telegram_id=tg_id,
                telegram_username=username,
                source="telegram"
            )
            session.add(contact)

        try:
            await session.flush()
        except Exception:
            # Last-resort: another concurrent insert won the race — look up the winner
            await session.rollback()
            res = await session.execute(
                select(Contact).where(
                    (Contact.telegram_id == tg_id) | (Contact.telegram_username == username)
                    if username else Contact.telegram_id == tg_id
                ).limit(1)
            )
            contact = res.scalar_one_or_none()
            if not contact:
                raise

        return contact

    async def update_user_profile(self) -> None:
        """Fetch current user info and update UserProfile in DB.

        Photos are NOT stored locally — fetched on demand via /api/telegram/media/avatar/{id}.
        """
        client = await self.factory.get_client()

        @telegram_retry
        async def _fetch_me():
            if not client.is_connected():
                await client.connect()
            return await client.get_me()

        @telegram_retry
        async def _fetch_full_user(me):
            from telethon.tl.functions.users import GetFullUserRequest
            return await client(GetFullUserRequest(id=me))

        try:
            async with client:
                me = await _fetch_me()
                if not me: return

                async with get_session(db_name=self.db_name) as session:
                    res = await session.execute(
                        select(UserProfile).where(UserProfile.telegram_id == str(me.id))
                    )
                    profile = res.scalar_one_or_none()

                    if not profile:
                        profile = UserProfile(telegram_id=str(me.id))
                        session.add(profile)

                    profile.first_name = me.first_name
                    profile.last_name = me.last_name
                    profile.username = me.username
                    profile.phone = me.phone

                    try:
                        full = await _fetch_full_user(me)
                        profile.bio = full.full_user.about
                    except Exception as e:
                        logger.warning("bio_fetch_failed", error=str(e))

                    await session.commit()
                    logger.info("user_profile_updated", telegram_id=me.id)
        except Exception as e:
            logger.error("user_profile_update_failed", error=str(e))
