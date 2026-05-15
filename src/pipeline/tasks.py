"""Celery tasks for data processing pipeline."""

from __future__ import annotations
import structlog
from dataclasses import asdict
from typing import List, Optional
from uuid import UUID

from src.pipeline.celery_app import celery_app
from src.services.pipeline_service import PipelineService
from src.pipeline.base_task import AsyncDBTask

logger = structlog.get_logger()

@celery_app.task(name="src.pipeline.tasks.sync_telegram", base=AsyncDBTask)
def sync_telegram(self, db_name: str | None = None):
    """Sync recent messages from all active Telegram channels."""
    async def _do():
        service = PipelineService(db_name=db_name)
        return await service.run_recent_sync()
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.deep_sync_telegram", base=AsyncDBTask)
def deep_sync_telegram(self, chat_ids: list[str | int], limit: int = 500, days: int = 90, db_name: str | None = None):
    """Deep sync historical messages from specific chats."""
    async def _do():
        service = PipelineService(db_name=db_name)
        return await service.run_historical_sync(chat_ids, limit=limit, days=days)
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.enrich_contact_task", base=AsyncDBTask)
def enrich_contact_task(self, contact_id: str, db_name: str | None = None):
    """Fetch full profile info for a contact."""
    from src.connectors.telegram_connector import TelegramConnector
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        success = await connector.enrich_contact(contact_id)
        return {"status": "success" if success else "failed"}
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.sync_telegram_contacts", queue="connectors", base=AsyncDBTask)
def sync_telegram_contacts(self, db_name: str | None = None):
    """Sync personal contacts from Telegram account."""
    from src.connectors.telegram_connector import TelegramConnector
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        if not await connector.is_authorized():
            return {"status": "skipped", "reason": "not_authorized"}
        result = await connector.sync_contacts()
        return result
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.process_unified_messages", queue="processing", base=AsyncDBTask)
def process_unified_messages(self, limit: int = 100, db_name: str | None = None):
    """Process new messages through AI pipeline."""
    from src.pipeline.unified_processor import MessageProcessor
    from src.db.database import get_session
    from sqlalchemy import select
    from src.db.models import Message

    async def _do():
        async with get_session(db_name=db_name) as session:
            query = (
                select(Message)
                .where(Message.content.isnot(None))
                .order_by(Message.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            messages = result.scalars().all()

            if not messages:
                logger.info("no_messages_to_process", db_name=db_name)
                return {"processed": 0, "contacts_found": 0, "leads_found": 0, "errors": 0}

            processor = MessageProcessor(session)
            stats = await processor.process_batch(messages)
            await session.commit()
            return stats
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.process_message_embeddings", queue="processing", base=AsyncDBTask)
def process_message_embeddings(self, batch_size: int = 100, db_name: str | None = None):
    """Generate vector embeddings for new messages."""
    from src.pipeline.unified_processor import maintenance_index_messages
    async def _do():
        return await maintenance_index_messages(batch_size=batch_size, db_name=db_name)
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.reindex_dirty_contacts", queue="processing", base=AsyncDBTask)
def reindex_dirty_contacts(self, batch_size: int = 50, db_name: str | None = None):
    """Re-index contacts that have changed."""
    from src.pipeline.unified_processor import maintenance_reindex_dirty
    async def _do():
        return await maintenance_reindex_dirty(batch_size=batch_size, db_name=db_name)
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_message_processing", base=AsyncDBTask)
def orchestrate_multi_db_message_processing(self):
    """Trigger AI processing for all databases."""
    from src.db.database import list_tenant_databases
    async def _do():
        databases = await list_tenant_databases()
        for db_name in databases:
            service = PipelineService(db_name=db_name)
            await service.orchestrate_message_processing()
        return {"status": "dispatched", "databases": databases}
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_sync", base=AsyncDBTask)
def orchestrate_multi_db_sync(self):
    """Trigger background sync for all databases."""
    from src.db.database import list_tenant_databases
    async def _do():
        databases = await list_tenant_databases()
        for db_name in databases:
            service = PipelineService(db_name=db_name)
            await service.orchestrate_sync()
        return {"status": "dispatched", "databases": databases}
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.deep_track_chunk", base=AsyncDBTask)
def deep_track_chunk(self, telegram_id: str, entity_type: str, limit: int = 100, db_name: str | None = None):
    """Fetch a chunk of historical messages for a tracked target."""
    from src.connectors.telegram_connector import TelegramConnector
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        count = await connector.sync_deep_history_chunk(telegram_id, entity_type, limit=limit)
        if count > 0:
            process_unified_messages.delay(limit=count + 50, db_name=db_name)
        return {"status": "success", "synced": count}
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.deep_track_orchestrator", queue="connectors", base=AsyncDBTask)
def deep_track_orchestrator(self):
    """Find all active tracking targets and queue chunk tasks for them across all databases."""
    from src.db.models import TrackedChannel
    from src.db.database import get_session, list_tenant_databases
    from sqlalchemy import select
    async def _do():
        databases = await list_tenant_databases()
        total_queued = 0
        for db_name in databases:
            async with get_session(db_name=db_name) as session:
                res = await session.execute(select(TrackedChannel).where(TrackedChannel.is_active == True))
                channels = res.scalars().all()
                for ch in channels:
                    deep_track_chunk.delay(ch.telegram_id, ch.entity_type, db_name=db_name)
                total_queued += len(channels)
        return {"status": "success", "total_queued": total_queued, "databases": len(databases)}
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.load_complete_history", queue="connectors", base=AsyncDBTask)
def load_complete_history(self, db_name: str | None = None):
    """Load COMPLETE message history from all channels."""
    async def _do():
        service = PipelineService(db_name=db_name)
        return await service.run_complete_history_load()
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.generate_all_embeddings", queue="processing", base=AsyncDBTask)
def generate_all_embeddings(self, batch_size: int = 500, db_name: str | None = None):
    """Generate embeddings for all messages without embeddings."""
    from src.pipeline.unified_processor import maintenance_index_messages
    async def _do():
        return await maintenance_index_messages(batch_size=batch_size, db_name=db_name)
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.orchestrate_massive_sync")
def orchestrate_massive_sync():
    """Trigger a full system re-sync and re-index."""
    from celery import chain
    settings = get_settings()
    db_name = settings.postgres_db
    task_chain = chain(
        load_complete_history.s(db_name=db_name),
        generate_all_embeddings.s(batch_size=500, db_name=db_name),
        reindex_dirty_contacts.s(batch_size=50, db_name=db_name)
    )
    result = task_chain.apply_async()
    return {"status": "dispatched", "chain_id": str(result.id)}

@celery_app.task(name="src.pipeline.tasks.send_campaign", queue="connectors", base=AsyncDBTask)
def send_campaign(self, campaign_id: str, db_name: str | None = None):
    """Send campaign messages to all contacts."""
    from src.db.database import get_session
    from src.services.campaign_service import CampaignService
    from uuid import UUID
    async def _do():
        async with get_session(db_name=db_name) as session:
            service = CampaignService(session, db_name=db_name)
            return await service.run_campaign(UUID(campaign_id))
    return self.run_async(_do())
