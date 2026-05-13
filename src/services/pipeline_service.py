"""Pipeline service — orchestrates sync, historical loading, and maintenance across databases."""

import structlog
from dataclasses import asdict
from typing import List, Optional
from sqlalchemy import select, func
from src.db.database import get_session
from src.db.models import TrackedChannel, Message
from src.connectors.telegram_connector import TelegramConnector

logger = structlog.get_logger()

class PipelineService:
    """Service for high-level pipeline orchestration."""

    def __init__(self, db_name: str | None = None):
        self.db_name = db_name or "crm"

    async def run_recent_sync(self) -> dict:
        """Sync recent messages from all active Telegram channels."""
        connector = TelegramConnector(db_name=self.db_name)
        if not await connector.is_authorized():
            return {"status": "skipped", "reason": "not_authorized"}
        
        result = await connector.sync()
        return asdict(result)

    async def run_historical_sync(self, chat_ids: List[str | int], limit: int = 500, days: int = 90) -> dict:
        """Deep sync historical messages from specific chats."""
        connector = TelegramConnector(db_name=self.db_name)
        result = await connector.deep_sync(chat_ids, limit=limit, days=days)
        return asdict(result)

    async def run_complete_history_load(self) -> dict:
        """Load COMPLETE message history from all channels."""
        connector = TelegramConnector(db_name=self.db_name)
        if not await connector.is_authorized():
            return {"status": "error", "reason": "not_authorized"}

        async with get_session(db_name=self.db_name) as session:
            before = await session.execute(select(func.count(Message.id)))
            before_count = before.scalar() or 0
            
            res = await session.execute(
                select(TrackedChannel).where(TrackedChannel.is_active == True)
            )
            channels = res.scalars().all()

        logger.info("load_complete_history_start", 
                   channels_count=len(channels), 
                   messages_before=before_count, 
                   db_name=self.db_name)

        result = await connector.sync(
            chat_ids=[int(ch.telegram_id) for ch in channels],
            limit=1000000,
            offset_date=None,
            complete=True
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
            "messages_loaded": result.messages_fetched,
            "before": before_count,
            "after": after_count,
            "new": new_messages
        }
