"""Telegram synchronization service implementation."""

import asyncio
import structlog
from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlalchemy import select, update
from telethon.tl.types import Channel
from src.db.database import get_session
from src.db.models import Message, MessageContact, TrackedChannel, SyncState
from src.db.repository import SyncStateRepository
from src.services.telegram.base import TelegramSyncInterface
from src.services.telegram.client_factory import TelegramClientFactory
from src.services.telegram.entity_service import TelegramEntityService

logger = structlog.get_logger()

class TelegramSyncService(TelegramSyncInterface):
    """Handles Telegram message synchronization."""

    def __init__(self, client_factory: TelegramClientFactory, entity_service: TelegramEntityService):
        self.factory = client_factory
        self.entity_service = entity_service
        self.db_name = client_factory.db_name

    async def sync_recent(self, chat_ids: Optional[List[int]] = None, limit: int = 100) -> dict:
        """Sync recent messages from active channels."""
        client = await self.factory.get_client()
        async with client:
            if not await client.is_user_authorized():
                return {"status": "error", "reason": "unauthorized"}

            async with get_session(db_name=self.db_name) as session:
                repo = SyncStateRepository(session)
                state = await repo.get_or_create_connector_state("telegram")
                state.status = "running"
                await session.commit()

                if chat_ids:
                    target_ids = chat_ids
                else:
                    res = await session.execute(
                        select(TrackedChannel.telegram_id).where(TrackedChannel.is_active == True)
                    )
                    target_ids = [int(row[0]) for row in res.all()]

            semaphore = asyncio.Semaphore(3)
            async def _sync_task(tid):
                async with semaphore:
                    try:
                        async with get_session(db_name=self.db_name) as task_session:
                            return await self.sync_historical(tid, limit=limit, session=task_session)
                    except Exception as e:
                        logger.error("sync_task_error", target_id=tid, error=str(e))
                        return 0

            total_fetched = 0
            try:
                results = await asyncio.gather(*[_sync_task(tid) for tid in target_ids])
                total_fetched = sum(results)
                final_status = "idle"
            except Exception as e:
                logger.error("sync_recent_gather_failed", error=str(e))
                final_status = "idle"  # Always reset to idle so the connector isn't stuck

            async with get_session(db_name=self.db_name) as session:
                repo = SyncStateRepository(session)
                state = await repo.get_or_create_connector_state("telegram")
                state.last_sync_at = datetime.now(timezone.utc)
                state.status = final_status
                await session.commit()

            return {"status": "success", "fetched": total_fetched}

    async def sync_historical(
        self, 
        chat_id: int, 
        limit: int = 1000, 
        offset_date: Optional[datetime] = None,
        session: Optional[Any] = None,
        ignore_last_id: bool = False
    ) -> int:
        """Sync historical messages for a specific chat."""
        # Use provided session or create new one
        if session:
            return await self._sync_chat_impl(chat_id, limit, offset_date, session, ignore_last_id)
        else:
            async with get_session(db_name=self.db_name) as new_session:
                return await self._sync_chat_impl(chat_id, limit, offset_date, new_session, ignore_last_id)

    async def _sync_chat_impl(self, chat_id, limit, offset_date, session, ignore_last_id) -> int:
        client = await self.factory.get_client()
        # connect() is inside the try block so the finally clause always runs and
        # the session file is never left in a locked state on unexpected errors.
        try:
            if not client.is_connected():
                await client.connect()
            try:
                entity = await client.get_entity(chat_id)
            except Exception:
                # Handle common Telegram ID quirks
                if isinstance(chat_id, int) and chat_id > 0:
                    try: entity = await client.get_entity(int(f"-100{chat_id}"))
                    except Exception: entity = await client.get_entity(str(chat_id))
                else: raise

            is_channel = isinstance(entity, Channel) and entity.broadcast
            messages_synced = 0
            batch_size = 1000

            # Get last_id from TrackedChannel or similar if available
            last_id = 0
            if not ignore_last_id:
                # Check if this is a tracked channel
                res = await session.execute(select(TrackedChannel).where(TrackedChannel.telegram_id == str(entity.id)))
                tracked = res.scalar_one_or_none()

                repo = SyncStateRepository(session)
                state = await repo.get_or_create_connector_state("telegram")
                last_id = (state.metadata_json or {}).get(f"chat_{entity.id}_last_id", 0)

            # Load all known source_message_ids for this entity into a Python set for
            # O(1) dedup during the iter_messages loop.  Each ID is ~25 bytes; even a
            # 500k-message channel adds only ~12 MB — well within the container limit.
            existing_rows = await session.execute(
                select(Message.source_message_id)
                .where(Message.group_id == str(entity.id))
            )
            existing_ids = {r[0] for r in existing_rows if r[0]}

            async for msg in client.iter_messages(entity, limit=limit, min_id=last_id, offset_date=offset_date):
                source_id = f"{entity.id}_{msg.id}"
                if source_id in existing_ids: continue

                sender_entity = msg.sender or entity if not is_channel else entity
                contact = await self.entity_service.get_or_create_contact(session, sender_entity, is_channel=is_channel)

                message = Message(
                    contact_id=contact.id,
                    source="telegram",
                    source_message_id=source_id,
                    direction="outgoing" if msg.out else "incoming",
                    content=msg.text or "",
                    group_id=str(entity.id),
                    group_name=getattr(entity, "title", "Unknown"),
                    timestamp=msg.date
                )
                session.add(message)
                session.add(MessageContact(message=message, contact=contact, role="sender"))
                existing_ids.add(source_id)
                messages_synced += 1

                if messages_synced % batch_size == 0:
                    await session.commit()

            # Update last sync timestamp for channel
            await session.execute(
                update(TrackedChannel)
                .where(TrackedChannel.telegram_id == str(entity.id))
                .values(last_sync_at=datetime.now(timezone.utc))
            )
            await session.commit()
            return messages_synced
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
