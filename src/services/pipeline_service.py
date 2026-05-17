"""Pipeline service — orchestrates sync, historical loading, and maintenance across databases."""

import structlog
from dataclasses import asdict
from typing import List, Optional
from sqlalchemy import select, func
from src.db.database import get_session
from src.db.models import TrackedChannel, Message
from src.services.telegram.client_factory import TelegramClientFactory
from src.services.telegram.auth_service import TelegramAuthService
from src.services.telegram.sync_service import TelegramSyncService
from src.services.telegram.entity_service import TelegramEntityService

logger = structlog.get_logger()

class PipelineService:
    """Service for high-level pipeline orchestration."""

    def __init__(self, db_name: str | None = None):
        from src.core.config import get_settings
        self.db_name = db_name or get_settings().postgres_db
        
        # Initialize Telegram Services
        self.factory = TelegramClientFactory(db_name=self.db_name)
        self.auth = TelegramAuthService(self.factory)
        self.entity = TelegramEntityService(self.factory)
        self.sync_svc = TelegramSyncService(self.factory, self.entity)

    async def run_recent_sync(self) -> dict:
        """Sync recent messages from all active Telegram channels."""
        if not await self.auth.is_authorized():
            return {"status": "skipped", "reason": "not_authorized"}
        
        result = await self.sync_svc.sync_recent()
        return result

    async def run_historical_sync(self, chat_ids: List[str | int], limit: int = 500, days: int = 90) -> dict:
        """Deep sync historical messages from specific chats."""
        if not await self.auth.is_authorized():
            return {"status": "skipped", "reason": "not_authorized"}
        
        # Note: sync_historical returns total synced count. 
        # We wrap it in a dict for backward compatibility with PipelineService consumer expectations.
        total_synced = 0
        for cid in chat_ids:
            total_synced += await self.sync_svc.sync_historical(chat_id=int(cid), limit=limit)
            
        return {"status": "success", "fetched": total_synced}

    async def run_complete_history_load(self) -> dict:
        """Load COMPLETE message history from all channels."""
        if not await self.auth.is_authorized():
            return {"status": "error", "reason": "not_authorized"}

        async with get_session(db_name=self.db_name) as session:
            before = await session.execute(select(func.count(Message.id)))
            before_count = before.scalar() or 0
            
            res = await session.execute(
                select(TrackedChannel.telegram_id).where(TrackedChannel.is_active == True)
            )
            target_ids = [int(row[0]) for row in res.all()]

        logger.info("load_complete_history_start", 
                   channels_count=len(target_ids), 
                   messages_before=before_count, 
                   db_name=self.db_name)

        # Iterate all channels and fetch massive chunks
        total_fetched = 0
        for tid in target_ids:
            total_fetched += await self.sync_svc.sync_historical(
                chat_id=tid,
                limit=1000000,
                ignore_last_id=True
            )

        async with get_session(db_name=self.db_name) as session:
            after = await session.execute(select(func.count(Message.id)))
            after_count = after.scalar() or 0

        new_messages = after_count - before_count
        logger.info("load_complete_history_complete", 
                   new_messages=new_messages, 
                   db_name=self.db_name)

        return {
            "status": "success",
            "messages_loaded": total_fetched,
            "before": before_count,
            "after": after_count,
            "new": new_messages
        }

    async def orchestrate_message_processing(self) -> dict:
        """Trigger AI processing tasks."""
        from src.pipeline.tasks import process_unified_messages, process_message_embeddings, reindex_dirty_contacts
        
        process_unified_messages.delay(limit=100, db_name=self.db_name)
        process_message_embeddings.delay(batch_size=100, db_name=self.db_name)
        reindex_dirty_contacts.delay(batch_size=50, db_name=self.db_name)
        
        return {"status": "dispatched", "db_name": self.db_name}

    async def orchestrate_sync(self) -> dict:
        """Trigger background sync."""
        from src.pipeline.tasks import sync_telegram
        sync_telegram.delay(db_name=self.db_name)
        return {"status": "dispatched", "db_name": self.db_name}
