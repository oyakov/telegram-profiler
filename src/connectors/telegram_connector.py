"""Telegram connector — Thin facade over specialized Telegram services."""

from __future__ import annotations

import structlog
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional, List

from src.connectors.base import BaseConnector, SyncResult
from src.connectors.whisper_client import WhisperClient
from src.core.config import get_settings
from src.services.telegram.client_factory import TelegramClientFactory
from src.services.telegram.auth_service import TelegramAuthService
from src.services.telegram.entity_service import TelegramEntityService
from src.services.telegram.sync_service import TelegramSyncService
from src.services.telegram.management_service import TelegramManagementService

logger = structlog.get_logger()

class TelegramConnector(BaseConnector):
    """
    Telegram data connector. 
    Refactored to delegate work to specialized services.
    """

    name = "telegram"

    def __init__(self, enable_transcription: bool = False, db_name: str | None = None, project_id: str | None = None):
        self.settings = get_settings()
        self.whisper = WhisperClient()
        self.enable_transcription = enable_transcription
        self.db_name = db_name or self.settings.postgres_db
        self.project_id = project_id
        
        # Initialize Services
        self.factory = TelegramClientFactory(db_name=self.db_name)
        self.auth = TelegramAuthService(self.factory)
        self.entity = TelegramEntityService(self.factory)
        self.sync_svc = TelegramSyncService(self.factory, self.entity)
        self.mgmt = TelegramManagementService(self.factory)

    # --- Authentication Proxy ---

    async def is_authorized(self) -> bool:
        return await self.auth.is_authorized()

    async def send_code_request(self, phone: str) -> str:
        return await self.auth.send_code_request(phone)

    async def sign_in(self, phone: str, code: str, phone_code_hash: str) -> dict:
        result = await self.auth.sign_in(phone, code, phone_code_hash)
        if result["status"] == "success":
            # Post-login tasks
            await self.entity.update_user_profile()
            task = asyncio.create_task(self.auto_sync_on_login(force=True))
            task.add_done_callback(
                lambda t: logger.error("auto_sync_on_login_failed", error=str(t.exception()))
                if not t.cancelled() and t.exception() is not None else None
            )
        return result

    async def sign_in_2fa(self, password: str) -> dict:
        result = await self.auth.sign_in_2fa(password)
        if result["status"] == "success":
            await self.entity.update_user_profile()
            task = asyncio.create_task(self.auto_sync_on_login(force=True))
            task.add_done_callback(
                lambda t: logger.error("auto_sync_on_login_failed", error=str(t.exception()))
                if not t.cancelled() and t.exception() is not None else None
            )
        return result

    async def logout(self):
        await self.auth.logout()

    async def send_message(self, recipient_id: str, text: str) -> bool:
        """Send a message to a Telegram user/chat."""
        client = await self.factory.get_client()
        try:
            async with client:
                await client.send_message(recipient_id, text)
                return True
        except Exception as e:
            logger.error("telegram_send_message_error", recipient=recipient_id, error=str(e))
            return False

    # --- Sync Proxy ---

    async def sync(self, chat_ids: list[int] | None = None, limit: int = 100, **kwargs) -> SyncResult:
        result = SyncResult(connector=self.name, started_at=datetime.now(timezone.utc))
        try:
            res = await self.sync_svc.sync_recent(chat_ids=chat_ids, limit=limit)
            if res["status"] == "success":
                result.messages_fetched = res["fetched"]
            else:
                result.status = "error"
                result.errors.append(res.get("reason", "Unknown error"))
        except Exception as e:
            result.status = "error"
            result.errors.append(str(e))
        
        result.completed_at = datetime.now(timezone.utc)
        return result

    # --- Management Proxy ---

    async def list_telegram_folders(self) -> List[dict]:
        return await self.mgmt.list_folders()

    async def import_folder_channels(self, peer_ids: List[str]) -> List[dict]:
        return await self.mgmt.import_folder_channels(peer_ids)

    # --- Helper methods kept for backward compatibility or orchestration ---

    async def auto_sync_on_login(self, force: bool = False):
        """Orchestrate auto-sync after login."""
        from src.core.config import SettingsService
        from src.db.database import get_session
        from src.db.models import TrackedFolder, TrackedChannel
        from sqlalchemy import select

        if not force:
            async with get_session(db_name=self.db_name) as session:
                svc = SettingsService(session)
                if not await svc.get("telegram_auto_sync_on_login", True):
                    return

        logger.info("auto_sync_on_login_started")
        try:
            # Sync contacts
            await self.sync_contacts()
            
            # Sync folders
            folders = await self.list_telegram_folders()
            async with get_session(db_name=self.db_name) as session:
                for f_data in folders:
                    res = await session.execute(select(TrackedFolder).where(TrackedFolder.name == f_data["name"]))
                    db_folder = res.scalar_one_or_none()
                    if not db_folder:
                        db_folder = TrackedFolder(name=f_data["name"], telegram_folder_id=str(f_data["id"]))
                        session.add(db_folder)
                        await session.flush()

                    channels = await self.import_folder_channels(f_data["peer_ids"])
                    for ch in channels:
                        res = await session.execute(select(TrackedChannel).where(TrackedChannel.telegram_id == ch["telegram_id"]))
                        if not res.scalar_one_or_none():
                            session.add(TrackedChannel(
                                folder_id=db_folder.id,
                                telegram_id=ch["telegram_id"],
                                title=ch["title"],
                                entity_type=ch["entity_type"],
                                is_active=True
                            ))
                await session.commit()
            logger.info("auto_sync_on_login_complete")
        except Exception as e:
            logger.error("auto_sync_on_login_failed", error=str(e))

    async def sync_contacts(self) -> dict:
        """Fetch Telegram contacts and sync to DB."""
        from telethon.tl.functions.contacts import GetContactsRequest
        from src.db.database import get_session
        from src.db.models import Contact
        from sqlalchemy import select

        client = await self.factory.get_client()
        async with client:
            try:
                result = await client(GetContactsRequest(hash=0))
                async with get_session(db_name=self.db_name) as session:
                    for tg_user in result.users:
                        if not hasattr(tg_user, 'id'): continue
                        tg_id = str(tg_user.id)
                        res = await session.execute(select(Contact).where(Contact.telegram_id == tg_id))
                        contact = res.scalar_one_or_none()
                        if contact:
                            contact.is_personal = True
                        else:
                            session.add(Contact(
                                telegram_id=tg_id,
                                first_name=getattr(tg_user, 'first_name', 'Unknown') or 'Unknown',
                                last_name=getattr(tg_user, 'last_name', None),
                                telegram_username=getattr(tg_user, 'username', None),
                                source="telegram",
                                is_personal=True
                            ))
                    await session.commit()
                return {"status": "success"}
            except Exception as e:
                logger.error("sync_contacts_failed", error_type=type(e).__name__, error=str(e))
                return {"status": "error", "message": "Contact sync failed. Please try again."}

    async def enrich_contact(self, contact_id: str) -> bool:
        """Fetch fresh Telegram entity data for a contact and update the DB record.

        Returns True on success, False if the contact has no telegram_id or the
        entity cannot be resolved.
        """
        from src.db.database import get_session
        from src.db.models import Contact
        from sqlalchemy import select

        async with get_session(db_name=self.db_name) as session:
            try:
                from uuid import UUID
                contact_uuid = UUID(contact_id)
            except (ValueError, AttributeError):
                logger.warning("enrich_contact_invalid_uuid", contact_id=str(contact_id)[:64])
                return False

            res = await session.execute(select(Contact).where(Contact.id == contact_uuid))
            contact = res.scalar_one_or_none()
            if not contact or not contact.telegram_id:
                return False

            client = await self.factory.get_client()
            try:
                async with client:
                    entity = await client.get_entity(int(contact.telegram_id))
                    if hasattr(entity, "first_name"):
                        contact.first_name = entity.first_name or contact.first_name
                        contact.last_name = getattr(entity, "last_name", None) or contact.last_name
                    if hasattr(entity, "username"):
                        contact.telegram_username = entity.username or contact.telegram_username
                    contact.embedding_dirty = True
                    await session.commit()
                return True
            except Exception as e:
                logger.error("enrich_contact_fetch_failed", contact_id=contact_id, error_type=type(e).__name__)
                return False

    async def sync_deep_history_chunk(self, telegram_id: str, entity_type: str, limit: int = 100) -> int:
        """Sync a chunk of historical messages for a tracked entity.

        Delegates to TelegramSyncService.sync_historical so the two implementations
        stay in sync.  Returns the number of messages synced.
        """
        try:
            chat_id = int(telegram_id)
        except (ValueError, TypeError):
            logger.warning("sync_deep_history_chunk_invalid_id", telegram_id=str(telegram_id)[:64])
            return 0

        try:
            return await self.sync_svc.sync_historical(chat_id, limit=limit)
        except Exception as e:
            logger.error("sync_deep_history_chunk_failed", telegram_id=telegram_id, error_type=type(e).__name__)
            return 0

    # Legacy method stubs or pending refactor
    async def _get_client(self):
        return await self.factory.get_client()

    async def test_connection(self) -> bool:
        """Test if the connector can reach Telegram and is authorized."""
        try:
            return await self.is_authorized()
        except Exception as e:
            logger.error("telegram_connection_test_failed", error=str(e))
            return False

    async def get_status(self) -> dict:
        from src.db.database import get_session
        from src.db.models import SyncState
        from sqlalchemy import select
        async with get_session(db_name=self.db_name) as session:
            res = await session.execute(select(SyncState).where(SyncState.connector == "telegram"))
            state = res.scalar_one_or_none()
            return {
                "status": state.status if state else "idle",
                "last_sync_at": state.last_sync_at.isoformat() if state and state.last_sync_at else None
            }
