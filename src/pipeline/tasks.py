"""Celery task definitions — orchestrates the processing pipeline."""

from __future__ import annotations

import asyncio
import structlog

from src.pipeline.celery_app import celery_app

logger = structlog.get_logger()


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ========== Connector Tasks ==========

@celery_app.task(name="src.pipeline.tasks.sync_telegram")
def sync_telegram(auto: bool = False, chat_ids: list[int] | None = None, limit: int = 100, 
                  offset_date_iso: str | None = None, enable_transcription: bool = False,
                  db_name: str | None = None):
    """Sync messages from Telegram."""
    from src.connectors.telegram_connector import TelegramConnector
    from src.core.config import SettingsService
    from src.db.database import get_session
    from datetime import datetime, timezone

    async def _do():
        if auto:
            async with get_session(db_name=db_name) as session:
                svc = SettingsService(session)
                enabled = await svc.get("telegram_sync_enabled", False)
                if not enabled:
                    return {"status": "skipped", "reason": "disabled"}

        offset_date = None
        if offset_date_iso:
            try:
                offset_date = datetime.fromisoformat(offset_date_iso).replace(tzinfo=timezone.utc)
            except ValueError: pass

        connector = TelegramConnector(enable_transcription=enable_transcription, db_name=db_name)
        from dataclasses import asdict
        try:
            result = await connector.sync(chat_ids=chat_ids, limit=limit, offset_date=offset_date)
            # After sync, trigger unified processing for this specific DB
            process_unified_messages.delay(db_name=db_name)
            return asdict(result)
        except Exception as e:
            logger.error("telegram_sync_task_failed", error=str(e), db=db_name)
            return {"status": "error", "message": str(e)}

    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.deep_sync_telegram")
def deep_sync_telegram(chat_ids: list[str | int], limit: int = 500, days: int = 90, db_name: str | None = None):
    """Deep sync historical messages from Telegram channels."""
    from src.connectors.telegram_connector import TelegramConnector
    
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        from dataclasses import asdict
        try:
            result = await connector.deep_sync(chat_ids=chat_ids, limit=limit, days=days)
            # Trigger unified processing for this DB
            process_unified_messages.delay(limit=limit + 500, db_name=db_name)
            return asdict(result)
        except Exception as e:
            logger.error("telegram_deep_sync_task_failed", error=str(e), db=db_name)
            return {"status": "error", "message": str(e)}

    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.enrich_contact_task")
def enrich_contact_task(contact_id: str, db_name: str | None = None):
    """Fetch profile info for a contact."""
    from src.connectors.telegram_connector import TelegramConnector
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        success = await connector.enrich_contact(contact_id)
        return {"status": "success" if success else "error"}
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.import_excel")
def import_excel(file_path: str | None = None, db_name: str | None = None):
    """Import contacts from Excel/CSV file."""
    from src.connectors.excel_connector import ExcelConnector
    from dataclasses import asdict
    async def _do():
        connector = ExcelConnector(db_name=db_name)
        result = await connector.sync(file_path=file_path)
        return asdict(result)
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.sync_crm")
def sync_crm(db_name: str | None = None):
    """Sync contacts from external CRM."""
    from src.connectors.external import ExternalConnector
    from dataclasses import asdict
    async def _do():
        connector = ExternalConnector(connector_type="crm", db_name=db_name)
        result = await connector.sync()
        return asdict(result)
    return _run_async(_do())


# ========== Unified Processing Tasks ==========

@celery_app.task(name="src.pipeline.tasks.process_unified_messages")
def process_unified_messages(limit: int = 50, db_name: str | None = None):
    """Run extraction and lead-detection on unprocessed messages."""
    from src.pipeline.unified_processor import process_unprocessed_messages
    async def _do():
        return await process_unprocessed_messages(limit=limit, db_name=db_name)
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.process_message_embeddings")
def process_message_embeddings(limit: int = 100, db_name: str | None = None):
    """Generate embeddings for messages that don't have them."""
    from src.pipeline.unified_processor import maintenance_index_messages
    logger.info("process_embeddings_task_started", limit=limit, db_name=db_name)
    async def _do():
        result = await maintenance_index_messages(batch_size=limit, db_name=db_name)
        logger.info("process_embeddings_task_result", result=result, db_name=db_name)
        return result
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.process_contact_batch")
def process_contact_batch(batch_size: int = 50, db_name: str | None = None):
    """Process contacts with dirty embeddings."""
    from src.pipeline.unified_processor import maintenance_reindex_dirty
    async def _do():
        return await maintenance_reindex_dirty(batch_size=batch_size, db_name=db_name)
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.update_lead_scores_task")
def update_lead_scores_task(db_name: str | None = None):
    """Recalculate lead scores for all leads."""
    from src.pipeline.unified_processor import update_all_lead_scores
    async def _do():
        return await update_all_lead_scores(db_name=db_name)
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.full_pipeline_run")
def full_pipeline_run(db_name: str | None = None):
    """Run all processing tasks in order for a specific database."""
    chain = (
        process_unified_messages.s(db_name=db_name) | 
        update_lead_scores_task.s(db_name=db_name) | 
        process_contact_batch.s(db_name=db_name)
    )
    return chain.delay()

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_sync")
def orchestrate_multi_db_sync():
    """Master task to trigger sync for all configured folders/databases."""
    import asyncio
    from src.db.database import get_engine
    import sqlalchemy as sa

    async def _get_dbs():
        engine = get_engine("postgres", use_pooling=False)
        async with engine.connect() as conn:
            res = await conn.execute(sa.text("SELECT datname FROM pg_database WHERE datname LIKE 'crm%' ORDER BY datname"))
            return [row[0] for row in res.fetchall()]

    dbs = _run_async(_get_dbs())
    if not dbs:
        dbs = ["crm"]

    for db in dbs:
        sync_telegram.delay(auto=True, db_name=db)

    return {"status": "dispatched", "databases": dbs}

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_maintenance")
def orchestrate_multi_db_maintenance():
    """Master task to trigger maintenance for all configured databases."""
    import asyncio
    from src.db.database import get_engine
    import sqlalchemy as sa

    async def _get_dbs():
        engine = get_engine("postgres", use_pooling=False)
        async with engine.connect() as conn:
            res = await conn.execute(sa.text("SELECT datname FROM pg_database WHERE datname LIKE 'crm%' ORDER BY datname"))
            return [row[0] for row in res.fetchall()]

    dbs = _run_async(_get_dbs())
    if not dbs:
        dbs = ["crm"]

    for db in dbs:
        process_contact_batch.delay(db_name=db)

    return {"status": "dispatched", "databases": dbs}

@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_message_processing")
def orchestrate_multi_db_message_processing():
    """Master task to trigger message processing for all configured databases."""
    import asyncio
    from src.db.database import get_engine
    import sqlalchemy as sa

    async def _get_dbs():
        engine = get_engine("postgres", use_pooling=False)
        async with engine.connect() as conn:
            res = await conn.execute(sa.text("SELECT datname FROM pg_database WHERE datname LIKE 'crm%' ORDER BY datname"))
            return [row[0] for row in res.fetchall()]

    dbs = _run_async(_get_dbs())
    if not dbs:
        dbs = ["crm"]

    for db in dbs:
        logger.info("dispatching_message_processing", db=db)
        process_unified_messages.delay(limit=200, db_name=db)
        process_message_embeddings.delay(limit=5000, db_name=db)

    return {"status": "dispatched", "databases": dbs}



# ========== Legacy/Compatibility Tasks ==========

@celery_app.task(name="src.pipeline.tasks.detect_leads_task")
def detect_leads_task(limit: int = 50):
    """Scan channel messages for leads (Legacy wrapper)."""
    return process_unified_messages(limit=limit)


@celery_app.task(name="src.pipeline.tasks.reindex_embeddings")
def reindex_embeddings():
    """Re-generate all embeddings."""
    from src.pipeline.unified_processor import full_reindex
    async def _do():
        return await full_reindex()
    return _run_async(_do())
