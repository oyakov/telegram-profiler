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
    from src.pipeline.unified_processor import MessageProcessor

    async def _do():
        async with get_session(db_name=db_name) as session:
            from sqlalchemy import select
            from src.db.models import Message

            # Get unprocessed messages
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

            logger.info("process_unified_messages_complete",
                       processed=stats["processed"],
                       contacts_found=stats["contacts_found"],
                       leads_found=stats["leads_found"],
                       errors=stats["errors"],
                       db_name=db_name)
            return stats

    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_message_processing")
def orchestrate_multi_db_message_processing():
    """Trigger AI processing for all databases."""
    databases = ["crm"]
    for db_name in databases:
        process_unified_messages.delay(limit=100, db_name=db_name)
        process_message_embeddings.delay(batch_size=100, db_name=db_name)
        reindex_dirty_contacts.delay(batch_size=50, db_name=db_name)

    logger.info("orchestrate_multi_db_message_processing_dispatched", databases=databases)
    return {"status": "dispatched", "databases": databases}

@celery_app.task(name="src.pipeline.tasks.process_message_embeddings", queue="processing")
def process_message_embeddings(batch_size: int = 100, db_name: str | None = None):
    """Generate vector embeddings for new messages."""
    from src.pipeline.unified_processor import maintenance_index_messages

    async def _do():
        try:
            result = await maintenance_index_messages(batch_size=batch_size, db_name=db_name)
            logger.info("process_message_embeddings_complete",
                       processed=result["processed"],
                       errors=result["errors"],
                       tokens=result["tokens"],
                       db_name=db_name)
            return result
        except Exception as e:
            logger.error("process_message_embeddings_failed", error=str(e), exc_info=True)
            raise

    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.reindex_dirty_contacts", queue="processing")
def reindex_dirty_contacts(batch_size: int = 50, db_name: str | None = None):
    """Re-index contacts that have changed."""
    from src.pipeline.unified_processor import maintenance_reindex_dirty

    async def _do():
        try:
            result = await maintenance_reindex_dirty(batch_size=batch_size, db_name=db_name)
            logger.info("reindex_dirty_contacts_complete",
                       processed=result["processed"],
                       errors=result["errors"],
                       skipped=result["skipped"],
                       db_name=db_name)
            return result
        except Exception as e:
            logger.error("reindex_dirty_contacts_failed", error=str(e), exc_info=True)
            raise

    return _run_async(_do())

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

@celery_app.task(name="src.pipeline.tasks.load_complete_history", queue="connectors")
def load_complete_history(db_name: str | None = None):
    """Load COMPLETE message history from all channels - no time limits."""
    from src.connectors.telegram_connector import TelegramConnector
    from src.db.models import TrackedChannel, Message
    from sqlalchemy import select, func

    async def _do():
        connector = TelegramConnector(db_name=db_name or "crm")

        # Check auth
        if not await connector.is_authorized():
            return {"status": "error", "reason": "not_authorized"}

        # Count messages before
        async with get_session(db_name=db_name or "crm") as session:
            before = await session.execute(select(func.count(Message.id)))
            before_count = before.scalar() or 0

        # Get all active channels
        async with get_session(db_name=db_name or "crm") as session:
            res = await session.execute(
                select(TrackedChannel).where(TrackedChannel.is_active == True)
            )
            channels = res.scalars().all()

        logger.info("load_complete_history_start",
                   channels_count=len(channels),
                   messages_before=before_count,
                   db_name=db_name)

        # Load with massive limit (no time restriction)
        result = await connector.sync(
            chat_ids=[int(ch.telegram_id) for ch in channels],
            limit=1000000,  # Load all available
            offset_date=None  # No time restriction
        )

        # Count after
        async with get_session(db_name=db_name or "crm") as session:
            after = await session.execute(select(func.count(Message.id)))
            after_count = after.scalar() or 0

        new_messages = after_count - before_count

        logger.info("load_complete_history_complete",
                   messages_loaded=result.messages_fetched,
                   messages_before=before_count,
                   messages_after=after_count,
                   new_messages=new_messages,
                   db_name=db_name)

        return {
            "status": "success",
            "messages_loaded": result.messages_fetched,
            "before": before_count,
            "after": after_count,
            "new": new_messages
        }

    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.generate_all_embeddings", queue="processing")
def generate_all_embeddings(batch_size: int = 500, db_name: str | None = None):
    """Generate embeddings for all messages without embeddings."""
    from src.pipeline.unified_processor import maintenance_index_messages

    async def _do():
        try:
            result = await maintenance_index_messages(batch_size=batch_size, db_name=db_name)
            logger.info("generate_all_embeddings_complete",
                       processed=result["processed"],
                       errors=result["errors"],
                       tokens=result["tokens"],
                       db_name=db_name)
            return result
        except Exception as e:
            logger.error("generate_all_embeddings_failed", error=str(e), exc_info=True)
            raise

    return _run_async(_do())

@celery_app.task(name="src.pipeline.tasks.orchestrate_complete_sync", queue="connectors")
def orchestrate_complete_sync():
    """
    Orchestrate complete data sync pipeline:
    1. Load complete history from all channels
    2. Generate embeddings for all messages
    3. Reindex contact profiles
    """
    logger.info("orchestrate_complete_sync_start")

    # Chain tasks: load history → embeddings → reindex
    from celery import chain

    task_chain = chain(
        load_complete_history.s(db_name="crm"),
        generate_all_embeddings.s(batch_size=500, db_name="crm"),
        reindex_dirty_contacts.s(batch_size=50, db_name="crm")
    )

    result = task_chain.apply_async()

    logger.info("orchestrate_complete_sync_dispatched", chain_id=str(result.id))

    return {
        "status": "dispatched",
        "chain_id": str(result.id),
        "steps": ["load_complete_history", "generate_all_embeddings", "reindex_dirty_contacts"]
    }

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
