"""Telegram connector — Telethon-based sync with listener and polling."""

from __future__ import annotations

import os
import structlog
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.connectors.base import BaseConnector, SyncResult
from src.connectors.whisper_client import WhisperClient
from src.connectors.telethon_postgres_session import PostgresTelegramSession
from src.core.config import get_settings
from src.db.database import get_session
from src.db.models import Contact, Message, SyncState, VoiceNote, MessageContact

from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel, Chat, MessageMediaDocument

logger = structlog.get_logger()


class TelegramConnector(BaseConnector):
    """Telegram data connector using Telethon."""

    name = "telegram"

    def __init__(self, enable_transcription: bool = False, db_name: str | None = None, project_id: str | None = None):
        self.settings = get_settings()
        self.whisper = WhisperClient()
        self.enable_transcription = enable_transcription
        self.db_name = db_name or os.getenv('POSTGRES_DB', 'crm')
        self.project_id = project_id
        self.pg_session = PostgresTelegramSession(session_name=self.settings.telegram_session_name)

    async def _get_client(self):
        """Create a new Telethon client instance with PostgreSQL-backed session."""
        from telethon import TelegramClient
        string_session = await self.pg_session.get_string_session()
        return TelegramClient(
            string_session,
            int(self.settings.telegram_api_id),
            self.settings.telegram_api_hash
        )

    async def _save_session(self, user_id: Optional[str] = None):
        """Save current session to PostgreSQL."""
        await self.pg_session.save_session_data(user_id=user_id)

    async def _cleanup_stale_session(self):
        """Delete session from PostgreSQL."""
        await self.pg_session.delete_session()
        logger.info("telegram_session_deleted_from_postgres")

    async def is_authorized(self) -> bool:
        client = await self._get_client()
        await client.connect()
        try:
            return await client.is_user_authorized()
        finally:
            await client.disconnect()

    async def _post_login_setup(self):
        """Post-login setup: trigger auto-sync of folders and contacts."""
        logger.info("post_login_setup_started")
        try:
            await self.auto_sync_on_login(force=True)
            logger.info("post_login_setup_complete")
        except Exception as e:
            logger.error("post_login_setup_failed", error=str(e))

    async def auto_sync_on_login(self, force: bool = False):
        """Automatically sync folders and contacts after login."""
        from src.core.config import SettingsService
        from src.db.models import TrackedFolder, TrackedChannel

        if not force:
            async with get_session(db_name=self.db_name) as session:
                svc = SettingsService(session)
                is_enabled = await svc.get("telegram_auto_sync_on_login", True)
                if not is_enabled:
                    return

        try:
            await self.sync_contacts()
            folders = await self.list_telegram_folders()
            if folders:
                async with get_session(db_name=self.db_name) as session:
                    for folder_data in folders:
                        res = await session.execute(
                            select(TrackedFolder).where(TrackedFolder.name == folder_data["name"])
                        )
                        db_folder = res.scalar_one_or_none()
                        if not db_folder:
                            db_folder = TrackedFolder(
                                name=folder_data["name"],
                                telegram_folder_id=str(folder_data["id"]),
                                description=f"Imported from Telegram folder {folder_data['id']}"
                            )
                            session.add(db_folder)
                            await session.flush()

                        channels_info = await self.import_folder_channels(folder_data["peer_ids"])
                        for ch in channels_info:
                            res = await session.execute(
                                select(TrackedChannel).where(TrackedChannel.telegram_id == ch["telegram_id"])
                            )
                            existing_chan = res.scalar_one_or_none()
                            if not existing_chan:
                                new_chan = TrackedChannel(
                                    folder_id=db_folder.id,
                                    telegram_id=ch["telegram_id"],
                                    title=ch["title"],
                                    username=ch["username"],
                                    entity_type=ch["entity_type"]
                                )
                                session.add(new_chan)
                            else:
                                existing_chan.folder_id = db_folder.id
                                existing_chan.is_active = True
                    await session.commit()
        except Exception as e:
            logger.error("telegram_auto_sync_failed", error=str(e))

    async def sync(self, chat_ids: list[int] | None = None, limit: int = 100, offset_date: datetime | None = None, **kwargs) -> SyncResult:
        result = SyncResult(connector=self.name, started_at=datetime.now(timezone.utc))
        client = await self._get_client()
        try:
            async with client:
                if not await client.is_user_authorized():
                    result.status = "error"; return result
                
                async with get_session(db_name=self.db_name) as session:
                    sync_state = await self._get_sync_state(session)
                    sync_state.status = "running"
                    await session.commit()
                    
                    from src.db.models import TrackedChannel
                    res = await session.execute(select(TrackedChannel.telegram_id).where(TrackedChannel.is_active == True))
                    target_ids = [int(row[0]) for row in res.all()]

                semaphore = asyncio.Semaphore(3)
                async def _sync_task(tid):
                    async with semaphore:
                        try:
                            async with get_session(db_name=self.db_name) as task_session:
                                return await self._sync_chat(client, task_session, tid, limit, None, offset_date=offset_date)
                        except Exception as e:
                            logger.error("telegram_sync_error", target_id=tid, error=str(e))
                            return 0

                sync_tasks = [_sync_task(tid) for tid in target_ids]
                fetched_counts = await asyncio.gather(*sync_tasks)
                result.messages_fetched = sum(fetched_counts)

                async with get_session(db_name=self.db_name) as session:
                    sync_state = await self._get_sync_state(session)
                    sync_state.last_sync_at = datetime.now(timezone.utc)
                    sync_state.status = "idle"
                    await session.commit()
        except Exception as e:
            result.status = "error"; result.errors.append(str(e))
        result.completed_at = datetime.now(timezone.utc)
        return result

    async def _sync_chat(self, client, session, chat_id, limit, sync_state, offset_date=None, min_date=None) -> int:
        try:
            if isinstance(chat_id, str) and chat_id.lstrip('-').isdigit(): chat_id = int(chat_id)
            entity = await client.get_entity(chat_id)
        except Exception:
            if isinstance(chat_id, int) and chat_id > 0:
                try: entity = await client.get_entity(int(f"-100{chat_id}"))
                except Exception: entity = await client.get_entity(str(chat_id))
            else: raise

        is_channel = isinstance(entity, Channel) and entity.broadcast
        messages_synced = 0
        last_id = (sync_state.metadata_json or {}).get(f"chat_{entity.id}_last_id") if sync_state else 0
        async for msg in client.iter_messages(entity, limit=limit, min_id=last_id or 0, offset_date=offset_date):
            if min_date and msg.date < min_date: break
            existing = await session.execute(select(Message).where(Message.source_message_id == f"{entity.id}_{msg.id}"))
            if existing.scalar_one_or_none(): continue
            sender_entity = msg.sender or entity if not is_channel else entity
            contact = await self._get_or_create_contact(session, sender_entity, is_channel=is_channel)
            message = Message(
                contact_id=contact.id,
                source="telegram",
                source_message_id=f"{entity.id}_{msg.id}",
                direction="outgoing" if msg.out else "incoming",
                content=msg.text or "",
                group_id=str(entity.id),
                group_name=getattr(entity, "title", "Unknown"),
                timestamp=msg.date
            )
            session.add(message)
            session.add(MessageContact(message=message, contact=contact, role="sender"))
            messages_synced += 1
        
        from src.db.models import TrackedChannel
        await session.execute(update(TrackedChannel).where(TrackedChannel.telegram_id == str(entity.id)).values(last_sync_at=datetime.now(timezone.utc)))
        await session.flush()
        return messages_synced

    async def _get_or_create_contact(self, session, sender, is_channel=False) -> Contact:
        if sender is None: return Contact(first_name="System", telegram_id="system", source="telegram")
        tg_id = str(sender.id)
        result = await session.execute(select(Contact).where(Contact.telegram_id == tg_id).limit(1))
        contact = result.scalar_one_or_none()
        if not contact:
            contact = Contact(first_name=getattr(sender, "title", "Unknown") if is_channel else getattr(sender, "first_name", "Unknown"),
                            telegram_id=tg_id, telegram_username=getattr(sender, "username", None), source="telegram")
            session.add(contact); await session.flush()
        return contact

    async def _get_sync_state(self, session) -> SyncState:
        result = await session.execute(select(SyncState).where(SyncState.connector == self.name))
        state = result.scalar_one_or_none()
        if not state: state = SyncState(connector=self.name, status="idle"); session.add(state); await session.flush()
        return state

    async def list_telegram_folders(self) -> list[dict]:
        from telethon.tl.functions.messages import GetDialogFiltersRequest
        from telethon.tl.types import DialogFilter
        from telethon.utils import get_peer_id
        client = await self._get_client()
        try:
            async with client:
                if not await client.is_user_authorized(): return []
                res = await client(GetDialogFiltersRequest())
                filters = res.filters if hasattr(res, 'filters') else res
                result = []
                for f in filters:
                    if not isinstance(f, DialogFilter): continue
                    title = f.title.text if hasattr(f.title, 'text') else str(f.title)
                    peer_ids = [str(abs(get_peer_id(p))) for p in f.include_peers]
                    result.append({"name": title, "id": f.id, "channel_count": len(peer_ids), "peer_ids": peer_ids})
                return result
        except Exception as e: return []

    async def import_folder_channels(self, peer_ids: list[str]) -> list[dict]:
        from telethon.tl.types import Channel, Chat
        client = await self._get_client()
        try:
            async with client:
                if not await client.is_user_authorized(): return []
                channels = []
                for pid in peer_ids:
                    try: entity = await client.get_entity(int(f"-100{pid}"))
                    except Exception:
                        try: entity = await client.get_entity(int(pid))
                        except Exception: continue
                    if not isinstance(entity, (Channel, Chat)): continue
                    is_channel = isinstance(entity, Channel) and entity.broadcast
                    channels.append({"telegram_id": str(entity.id), "title": getattr(entity, "title", "Unknown"),
                                    "username": getattr(entity, "username", None), "entity_type": "channel" if is_channel else "group"})
                return channels
        except Exception: return []

    async def sync_contacts(self) -> dict:
        from telethon.tl.functions.contacts import GetContactsRequest
        client = await self._get_client()
        await client.connect()
        try:
            result = await client(GetContactsRequest(hash=0))
            added = 0; updated = 0
            async with get_session(self.db_name) as session:
                for contact in result.users:
                    if not hasattr(contact, 'id'): continue
                    tg_id = str(contact.id)
                    res = await session.execute(select(Contact).where(Contact.telegram_id == tg_id))
                    existing = res.scalar_one_or_none()
                    if existing:
                        existing.is_personal = True; updated += 1
                    else:
                        session.add(Contact(telegram_id=tg_id, first_name=getattr(contact, 'first_name', 'Unknown') or 'Unknown',
                                           last_name=getattr(contact, 'last_name', None), telegram_username=getattr(contact, 'username', None),
                                           source="telegram", is_personal=True))
                        added += 1
                await session.commit()
            return {"status": "success", "added": added, "updated": updated}
        except Exception as e: return {"status": "error", "error": str(e)}
        finally: await client.disconnect()

    async def sync_deep_history_chunk(self, telegram_id: str, entity_type: str, limit: int = 100) -> int:
        from src.db.models import TrackedChannel, Contact, Message, MessageContact
        client = await self._get_client()
        async with client:
            if not await client.is_user_authorized(): return 0
            try:
                ident = int(telegram_id) if telegram_id.lstrip('-').isdigit() else telegram_id
                entity = await client.get_entity(ident)
            except Exception: return 0
            async with get_session(db_name=self.db_name) as session:
                if entity_type in ["channel", "group"]:
                    res = await session.execute(select(TrackedChannel).where(TrackedChannel.telegram_id == telegram_id))
                else: res = await session.execute(select(Contact).where(Contact.telegram_id == telegram_id))
                target = res.scalar_one_or_none()
                if not target: return 0
                max_id = int(target.oldest_message_id) if target.oldest_message_id else 0
                messages_synced = 0; is_channel = isinstance(entity, Channel) and entity.broadcast
                iter_kwargs = {"limit": limit}
                if max_id > 0: iter_kwargs["max_id"] = max_id
                new_oldest_id = max_id; new_oldest_date = target.oldest_message_date
                async for msg in client.iter_messages(entity, **iter_kwargs):
                    source_msg_id = f"{entity.id}_{msg.id}"
                    existing = await session.execute(select(Message).where(Message.source_message_id == source_msg_id))
                    if not existing.scalar_one_or_none():
                        contact = await self._get_or_create_contact(session, msg.sender or entity if not is_channel else entity, is_channel=is_channel)
                        message = Message(contact_id=contact.id, source="telegram", source_message_id=source_msg_id,
                                        direction="outgoing" if msg.out else "incoming", content=msg.text or "",
                                        group_id=str(entity.id), group_name=getattr(entity, "title", "Unknown"), timestamp=msg.date)
                        session.add(message); session.add(MessageContact(message=message, contact=contact, role="sender"))
                        messages_synced += 1
                    if new_oldest_id == 0 or msg.id < new_oldest_id:
                        new_oldest_id = msg.id; new_oldest_date = msg.date
                if new_oldest_id > 0 and (max_id == 0 or new_oldest_id < max_id):
                    target.oldest_message_id = str(new_oldest_id); target.oldest_message_date = new_oldest_date
                target.total_messages_synced = (target.total_messages_synced or 0) + messages_synced
                target.last_sync_at = datetime.now(timezone.utc)
                await session.commit()
                return messages_synced
