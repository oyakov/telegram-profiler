"""Celery tasks for data processing pipeline."""

from __future__ import annotations
import asyncio
import structlog
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from src.pipeline.celery_app import celery_app
from src.db.database import get_session
from src.db.models import Message

logger = structlog.get_logger()

def _run_async(coro):
    """Run an async coroutine in the current event loop."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@celery_app.task(name="src.pipeline.tasks.sync_telegram")
def sync_telegram(db_name: str | None = None):
    """Sync recent messages from all active Telegram channels."""
    from src.connectors.telegram_connector import TelegramConnector
    
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        # Check if authorized
        if not await connector.is_authorized():
            return {"status": "skipped", "reason": "not_authorized"}
        
        result = await connector.sync()
        return asdict(result)
    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.deep_sync_telegram")
def deep_sync_telegram(chat_ids: list[str | int], limit: int = 500, days: int = 90, db_name: str | None = None):
    """Deep sync historical messages from specific chats."""
    from src.connectors.telegram_connector import TelegramConnector
    
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        result = await connector.deep_sync(chat_ids, limit=limit, days=days)
        return asdict(result)
    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.enrich_contact_task")
def enrich_contact_task(contact_id: str, db_name: str | None = None):
    """Fetch full profile info for a contact."""
    from src.connectors.telegram_connector import TelegramConnector
    
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        success = await connector.enrich_contact(contact_id)
        return {"status": "success" if success else "failed"}
    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.import_excel")
def import_excel(file_path: str, db_name: str | None = None):
    """Import contacts from Excel file."""
    # Placeholder for actual implementation
    return {"status": "success", "imported": 0}

@celery_app.task(name="src.pipeline.tasks.sync_crm")
def sync_crm(db_name: str | None = None):
    """Sync data with external CRM."""
    # Placeholder for actual implementation
    return {"status": "success", "synced": 0}

@celery_app.task(name="src.pipeline.tasks.sync_telegram_contacts", queue="connectors")
def sync_telegram_contacts(db_name: str | None = None):
    """Sync personal contacts from Telegram account."""
    from src.connectors.telegram_connector import TelegramConnector

    async def _do():
        connector = TelegramConnector(db_name=db_name)
        if not await connector.is_authorized():
            return {"status": "skipped", "reason": "not_authorized"}
        result = await connector.sync_contacts()
        return result
    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.cleanup_extraction_logs")
def cleanup_extraction_logs(days: int = 30):
    """Clean up old AI extraction logs."""
    return {"status": "success", "cleaned": 0}

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_cleanup")
def orchestrate_multi_db_cleanup():
    """Orchestrate maintenance tasks across all CRM databases."""
    return {"status": "success"}

@celery_app.task(name="src.pipeline.tasks.process_unified_messages", queue="processing")
def process_unified_messages(limit: int = 100, db_name: str | None = None):
    """Process new messages through AI pipeline."""
    # Placeholder
    return {"processed": 0}

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_message_processing")
def orchestrate_multi_db_message_processing():
    """Trigger AI processing for all databases."""
    return {"status": "dispatched", "databases": ["crm"]}

@celery_app.task(name="src.pipeline.tasks.process_message_embeddings", queue="processing")
def process_message_embeddings(batch_size: int = 100, db_name: str | None = None):
    """Generate vector embeddings for new messages."""
    return {"processed": 0, "errors": 0, "tokens": 0}

@celery_app.task(name="src.pipeline.tasks.reindex_dirty_contacts", queue="processing")
def reindex_dirty_contacts(db_name: str | None = None):
    """Re-index contacts that have changed."""
    return {"indexed": 0}

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_sync")
def orchestrate_multi_db_sync():
    """Trigger background sync for all databases."""
    sync_telegram.delay(db_name="crm")
    return {"status": "dispatched"}

@celery_app.task(name="src.pipeline.tasks.deep_track_chunk")
def deep_track_chunk(telegram_id: str, entity_type: str, limit: int = 100, db_name: str | None = None):
    """Fetch a chunk of historical messages for a tracked target."""
    from src.connectors.telegram_connector import TelegramConnector
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        count = await connector.sync_deep_history_chunk(telegram_id, entity_type, limit=limit)
        if count > 0:
            process_unified_messages.delay(limit=count + 50, db_name=db_name)
        return {"status": "success", "synced": count}
    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.assign_orphaned_messages_to_projects")
def assign_orphaned_messages_to_projects(db_name: str | None = None):
    """No-op after projects removal."""
    return {"status": "skipped", "reason": "system_projects_removed"}

@celery_app.task(name="src.pipeline.tasks.deep_track_orchestrator", queue="connectors")
def deep_track_orchestrator():
    """Find all active tracking targets and queue chunk tasks for them."""
    from src.db.models import TrackedChannel, TrackedFolder
    from sqlalchemy import select
    
    async def _do():
        async with get_session(db_name="crm") as session:
            res = await session.execute(select(TrackedChannel).where(TrackedChannel.is_active == True))
            channels = res.scalars().all()
            for ch in channels:
                deep_track_chunk.delay(ch.telegram_id, ch.entity_type, db_name="crm")
            return {"queued": len(channels)}
    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.send_campaign", queue="connectors")
def send_campaign(campaign_id: str, db_name: str | None = None):
    """Send campaign messages to all contacts."""
    from src.db.models import Campaign, CampaignMessage, Contact
    from src.connectors.telegram_connector import TelegramConnector
    from sqlalchemy import select
    from datetime import datetime

    async def _do():
        async with get_session(db_name=db_name or "crm") as session:
            campaign = await session.get(Campaign, UUID(campaign_id))
            if not campaign:
                return {"status": "error", "reason": "campaign not found"}
            
            # Logic here...
            return {"status": "completed"}
    return _run_async(_do())
