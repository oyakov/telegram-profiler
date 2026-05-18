"""Celery tasks for data processing pipeline."""

from __future__ import annotations
import structlog
from dataclasses import asdict
from typing import List, Optional
from uuid import UUID

from src.pipeline.celery_app import celery_app
from src.services.pipeline_service import PipelineService
from src.pipeline.base_task import AsyncDBTask
from src.core.config import get_settings

logger = structlog.get_logger()

@celery_app.task(name="src.pipeline.tasks.sync_telegram", bind=True, base=AsyncDBTask)
def sync_telegram(self, db_name: str | None = None):
    """Sync recent messages from all active Telegram channels."""
    async def _do():
        service = PipelineService(db_name=db_name)
        return await service.run_recent_sync()
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.deep_sync_telegram", bind=True, base=AsyncDBTask)
def deep_sync_telegram(self, chat_ids: list[str | int], limit: int = 500, days: int = 90, db_name: str | None = None):
    """Deep sync historical messages from specific chats."""
    async def _do():
        service = PipelineService(db_name=db_name)
        return await service.run_historical_sync(chat_ids, limit=limit, days=days)
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.enrich_contact_task", bind=True, base=AsyncDBTask)
def enrich_contact_task(self, contact_id: str, db_name: str | None = None):
    """Fetch full profile info for a contact."""
    from src.services.telegram.client_factory import TelegramClientFactory
    from src.services.telegram.entity_service import TelegramEntityService
    async def _do():
        factory = TelegramClientFactory(db_name=db_name)
        entity_svc = TelegramEntityService(factory)
        # Note: update_user_profile is for current user. 
        # For a specific contact, we need a method that takes contact_id.
        # Connector had 'enrich_contact'. We should ensure EntityService has it.
        # For now, let's keep connector usage or add it to EntityService.
        # Actually, let's just keep the task refactor simple.
        from src.connectors.telegram_connector import TelegramConnector
        connector = TelegramConnector(db_name=db_name)
        success = await connector.enrich_contact(contact_id)
        return {"status": "success" if success else "failed"}
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.sync_telegram_contacts", bind=True, queue="connectors", base=AsyncDBTask)
def sync_telegram_contacts(self, db_name: str | None = None):
    """Sync personal contacts from Telegram account."""
    from src.services.telegram.client_factory import TelegramClientFactory
    from src.services.telegram.auth_service import TelegramAuthService
    async def _do():
        factory = TelegramClientFactory(db_name=db_name)
        auth_svc = TelegramAuthService(factory)
        if not await auth_svc.is_authorized():
            return {"status": "skipped", "reason": "not_authorized"}
            
        # Call the existing sync_contacts on the connector for now, 
        # or move it to a specialized service if ready.
        from src.connectors.telegram_connector import TelegramConnector
        connector = TelegramConnector(db_name=db_name)
        result = await connector.sync_contacts()
        return result
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.process_unified_messages", bind=True, queue="processing", base=AsyncDBTask)
def process_unified_messages(self, limit: int = 100, db_name: str | None = None):
    """Process only new (unprocessed) messages through AI pipeline."""
    from src.pipeline.unified_processor import process_unprocessed_messages
    async def _do():
        return await process_unprocessed_messages(limit=limit, db_name=db_name)
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.process_message_embeddings", bind=True, queue="processing", base=AsyncDBTask)
def process_message_embeddings(self, batch_size: int = 100, db_name: str | None = None):
    """Generate vector embeddings for new messages."""
    from src.pipeline.unified_processor import maintenance_index_messages
    async def _do():
        return await maintenance_index_messages(batch_size=batch_size, db_name=db_name)
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.reindex_dirty_contacts", bind=True, queue="processing", base=AsyncDBTask)
def reindex_dirty_contacts(self, batch_size: int = 50, db_name: str | None = None):
    """Re-index contacts that have changed."""
    from src.pipeline.unified_processor import maintenance_reindex_dirty
    async def _do():
        return await maintenance_reindex_dirty(batch_size=batch_size, db_name=db_name)
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_message_processing", bind=True, base=AsyncDBTask)
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

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_sync", bind=True, base=AsyncDBTask)
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

@celery_app.task(name="src.pipeline.tasks.deep_track_chunk", bind=True, base=AsyncDBTask)
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

@celery_app.task(name="src.pipeline.tasks.deep_track_orchestrator", bind=True, queue="connectors", base=AsyncDBTask)
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

@celery_app.task(name="src.pipeline.tasks.load_complete_history", bind=True, queue="connectors", base=AsyncDBTask)
def load_complete_history(self, db_name: str | None = None):
    """Load COMPLETE message history from all channels."""
    async def _do():
        service = PipelineService(db_name=db_name)
        return await service.run_complete_history_load()
    return self.run_async(_do())

@celery_app.task(name="src.pipeline.tasks.generate_all_embeddings", bind=True, queue="processing", base=AsyncDBTask)
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
        load_complete_history.si(db_name=db_name),
        generate_all_embeddings.si(batch_size=500, db_name=db_name),
        reindex_dirty_contacts.si(batch_size=50, db_name=db_name)
    )
    result = task_chain.apply_async()
    return {"status": "dispatched", "chain_id": str(result.id)}

@celery_app.task(name="src.pipeline.tasks.import_excel", bind=True, queue="connectors", base=AsyncDBTask)
def import_excel(self, file_path: str, db_name: str | None = None):
    """Import contacts/messages from an Excel or CSV file."""
    from src.db.database import get_session
    async def _do():
        import asyncio
        import pandas as pd
        from pathlib import Path
        from src.db.models import Contact
        # Validate that the path is under the permitted uploads directory.
        # The file_path value comes from the Redis broker (potentially tampered).
        _uploads_root = Path("/app/uploads").resolve()
        path = Path(file_path).resolve()
        if not str(path).startswith(str(_uploads_root) + "/"):
            logger.error("import_excel_path_rejected", file_path=file_path)
            return {"status": "error", "reason": "invalid_path"}
        if not path.exists():
            return {"status": "error", "reason": "file_not_found"}
        try:
            # Run blocking pandas I/O in a thread to avoid stalling the event loop
            loop = asyncio.get_running_loop()
            if path.suffix in {".xlsx", ".xls"}:
                df = await loop.run_in_executor(None, pd.read_excel, path)
            else:
                df = await loop.run_in_executor(None, pd.read_csv, path)
        except Exception as e:
            logger.error("import_excel_read_failed", error_type=type(e).__name__, error=str(e))
            return {"status": "error", "reason": "file_read_error"}
        imported = 0
        async with get_session(db_name=db_name) as session:
            for _, row in df.iterrows():
                first_name = str(row.get("first_name") or row.get("name") or "").strip()
                if not first_name:
                    continue
                contact = Contact(
                    first_name=first_name,
                    last_name=str(row.get("last_name") or "").strip() or None,
                    email=str(row.get("email") or "").strip() or None,
                    phone=str(row.get("phone") or "").strip() or None,
                    source="excel_import",
                )
                session.add(contact)
                imported += 1
                # Flush every 500 rows to avoid accumulating all objects in memory
                # and issuing a single enormous commit at the end.
                if imported % 500 == 0:
                    await session.flush()
            # Final commit is issued by the get_session context manager on clean exit.
            # Only delete the file AFTER the session exits successfully so the file
            # is still available for retry if the commit fails.
        try:
            path.unlink()
        except Exception:
            pass
        return {"status": "success", "imported": imported}
    return self.run_async(_do())


@celery_app.task(name="src.pipeline.tasks.sync_crm", bind=True, queue="connectors", base=AsyncDBTask)
def sync_crm(self, db_name: str | None = None):
    """Placeholder for external CRM sync (not yet implemented)."""
    logger.warning("sync_crm_not_implemented", db_name=db_name)
    return {"status": "skipped", "reason": "not_implemented"}


@celery_app.task(name="src.pipeline.tasks.purge_extraction_log", bind=True, base=AsyncDBTask)
def purge_extraction_log(self, days: int = 30):
    """Delete ExtractionLog rows older than `days` days across all tenant databases."""
    from src.db.database import get_session, list_tenant_databases
    from src.db.models import ExtractionLog
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import delete

    async def _do():
        databases = await list_tenant_databases()
        total_deleted = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        for db_name in databases:
            try:
                async with get_session(db_name=db_name) as session:
                    result = await session.execute(
                        delete(ExtractionLog).where(ExtractionLog.created_at < cutoff)
                    )
                    deleted = result.rowcount
                    total_deleted += deleted
                    logger.info("purge_extraction_log", db_name=db_name, deleted=deleted, cutoff=cutoff.isoformat())
            except Exception as e:
                logger.error("purge_extraction_log_error", db_name=db_name, error=str(e))
        return {"deleted": total_deleted, "databases": len(databases), "cutoff_days": days}

    return self.run_async(_do())


@celery_app.task(name="src.pipeline.tasks.send_campaign", bind=True, queue="connectors", base=AsyncDBTask)
def send_campaign(self, campaign_id: str, db_name: str | None = None):
    """Send campaign messages to all contacts."""
    from src.db.database import get_session
    from src.services.campaign_service import CampaignService
    from uuid import UUID
    async def _do():
        async with get_session(db_name=db_name) as session:
            service = CampaignService(session)
            return await service.run_campaign(UUID(campaign_id))
    return self.run_async(_do())


@celery_app.task(name="src.pipeline.tasks.log_extraction_task", bind=True, queue="processing", base=AsyncDBTask)
def log_extraction_task(self, source_type: str, source_id: str, model_used: str, extracted_data: dict, db_name: str | None = None):
    """Background task to log AI extraction results."""
    from src.db.database import get_session
    from src.db.repository import ExtractionRepository
    async def _do():
        async with get_session(db_name=db_name) as session:
            repo = ExtractionRepository(session)
            await repo.log_extraction(
                source_type=source_type,
                source_id=source_id,
                model_used=model_used,
                extracted_data=extracted_data
            )
            return {"status": "logged"}
    return self.run_async(_do())
