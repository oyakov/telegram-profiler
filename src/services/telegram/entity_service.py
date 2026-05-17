"""Telegram entity and contact service implementation."""

import structlog
from pathlib import Path
from typing import Any, Optional
from sqlalchemy import select
from src.db.database import get_session
from src.db.models import Contact, UserProfile
from src.services.telegram.base import TelegramEntityInterface
from src.services.telegram.client_factory import TelegramClientFactory

logger = structlog.get_logger()

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
        result = await session.execute(select(Contact).where(Contact.telegram_id == tg_id).limit(1))
        contact = result.scalar_one_or_none()
        
        if not contact:
            contact = Contact(
                first_name=getattr(sender, "title", "Unknown") if is_channel else getattr(sender, "first_name", "Unknown"),
                telegram_id=tg_id, 
                telegram_username=getattr(sender, "username", None), 
                source="telegram"
            )
            session.add(contact)
            await session.flush()
        return contact

    async def update_user_profile(self) -> None:
        """Fetch current user info and update UserProfile in DB."""
        client = await self.factory.get_client()
        try:
            async with client:
                me = await client.get_me()
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

                    # Fetch bio
                    try:
                        from telethon.tl.functions.users import GetFullUserRequest
                        full = await client(GetFullUserRequest(id=me))
                        profile.bio = full.full_user.about
                    except Exception:
                        pass

                    # Download photo
                    photo_path = await self._download_photo(client, me)
                    if photo_path:
                        profile.profile_photo_path = photo_path

                    await session.commit()
                    logger.info("user_profile_updated", telegram_id=me.id)
        except Exception as e:
            logger.error("user_profile_update_failed", error=str(e))

    async def _download_photo(self, client, entity) -> Optional[str]:
        """Download profile photo and return local path."""
        try:
            output_dir = Path("/app/uploads/avatars")
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{entity.id}.jpg"
            file_path = output_dir / filename
            path = await client.download_profile_photo(entity, file=str(file_path))
            if path: return f"/app/uploads/avatars/{filename}"
            return None
        except Exception as e:
            logger.warning("telegram_photo_download_error", entity_id=entity.id, error=str(e))
            return None
