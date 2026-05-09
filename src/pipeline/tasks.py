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


# ========== Maintenance Tasks ==========

@celery_app.task(name="src.pipeline.tasks.cleanup_extraction_logs")
def cleanup_extraction_logs(days: int = 30, db_name: str | None = None):
    """Delete old extraction logs to save space."""
    from src.db.models import ExtractionLog
    from sqlalchemy import delete
    from datetime import datetime, timezone, timedelta

    async def _do():
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        async with get_session(db_name=db_name) as session:
            result = await session.execute(
                delete(ExtractionLog).where(ExtractionLog.created_at < cutoff)
            )
            await session.commit()
            return {"status": "success", "deleted": result.rowcount}
    
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_cleanup")
def orchestrate_multi_db_cleanup(days: int = 30):
    """Run cleanup across all CRM databases."""
    async def _do():
        # Using the utility from migrate_all to find all DBs
        from scripts.migrate_all import get_all_crm_databases
        databases = await get_all_crm_databases()
        for db in databases:
            cleanup_extraction_logs.delay(days=days, db_name=db)
        return {"status": "dispatched", "databases": databases}
    
    return _run_async(_do())


# ========== Unified Processing Tasks ==========

@celery_app.task(name="src.pipeline.tasks.process_unified_messages", queue="processing")
def process_unified_messages(limit: int = 50, db_name: str | None = None):
    """Run extraction and lead-detection on unprocessed messages."""
    from src.pipeline.unified_processor import process_unprocessed_messages
    async def _do():
        return await process_unprocessed_messages(limit=limit, db_name=db_name)
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_message_processing")
def orchestrate_multi_db_message_processing(limit: int = 50):
    """Run unified processing across all CRM databases."""
    async def _do():
        from scripts.migrate_all import get_all_crm_databases
        databases = await get_all_crm_databases()
        for db in databases:
            process_unified_messages.delay(limit=limit, db_name=db)
            process_message_embeddings.delay(limit=limit * 2, db_name=db)
        return {"status": "dispatched", "databases": databases}
    
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.process_message_embeddings", queue="processing")
def process_message_embeddings(limit: int = 100, db_name: str | None = None):
    """Generate embeddings for messages that don't have them."""
    from src.pipeline.unified_processor import maintenance_index_messages
    async def _do():
        return await maintenance_index_messages(batch_size=limit, db_name=db_name)
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.reindex_dirty_contacts", queue="processing")
def reindex_dirty_contacts(limit: int = 50, db_name: str | None = None):
    """Update embeddings for contacts marked as dirty."""
    from src.pipeline.unified_processor import maintenance_reindex_dirty
    async def _do():
        return await maintenance_reindex_dirty(batch_size=limit, db_name=db_name)
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.orchestrate_multi_db_sync")
def orchestrate_multi_db_sync():
    """Trigger Telegram sync for all CRM databases."""
    async def _do():
        from scripts.migrate_all import get_all_crm_databases
        databases = await get_all_crm_databases()
        for db in databases:
            sync_telegram.delay(auto=True, db_name=db)
        return {"status": "dispatched", "databases": databases}
    
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.deep_track_chunk")
def deep_track_chunk(telegram_id: str, entity_type: str, limit: int = 100, db_name: str | None = None):
    """Fetch one chunk of history for a tracked target."""
    from src.connectors.telegram_connector import TelegramConnector
    async def _do():
        connector = TelegramConnector(db_name=db_name)
        count = await connector.sync_deep_history_chunk(telegram_id, entity_type, limit=limit)
        if count > 0:
            # Trigger unified processing for the new messages
            process_unified_messages.delay(limit=count + 50, db_name=db_name)
        return {"status": "success", "synced": count}
    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.assign_orphaned_messages_to_projects")
def assign_orphaned_messages_to_projects(db_name: str | None = None):
    """Automatically assign messages without project_id to a default project."""
    from src.db.models import Message, SystemProject
    from sqlalchemy import select, update

    async def _do():
        async with get_session(db_name=db_name) as session:
            # Get the first project (Personal or similar)
            proj_res = await session.execute(
                select(SystemProject).order_by(SystemProject.created_at).limit(1)
            )
            project = proj_res.scalars().first()

            if not project:
                return {"status": "skipped", "reason": "no_projects"}

            # Update orphaned messages
            result = await session.execute(
                update(Message).where(Message.project_id.is_(None)).values(project_id=project.id)
            )
            await session.commit()

            return {
                "status": "success",
                "assigned": result.rowcount,
                "project_id": str(project.id),
                "project_name": project.name
            }

    return _run_async(_do())


@celery_app.task(name="src.pipeline.tasks.deep_track_orchestrator")
def deep_track_orchestrator():
    """Find all active tracking targets and queue chunk tasks for them."""
    from src.db.models import TrackedChannel, Contact, TrackedFolder
    from sqlalchemy import select, or_
    from scripts.migrate_all import get_all_crm_databases

    async def _do():
        databases = await get_all_crm_databases()
        for db in databases:
            async with get_session(db_name=db) as session:
                # 1. Active Channels (must be active AND their folder must be active if it exists)
                res = await session.execute(
                    select(TrackedChannel.telegram_id)
                    .outerjoin(TrackedFolder, TrackedChannel.folder_id == TrackedFolder.id)
                    .where(TrackedChannel.is_active == True)
                    .where(or_(TrackedFolder.id == None, TrackedFolder.is_active == True))
                )
                for row in res.all():
                    deep_track_chunk.delay(telegram_id=str(row[0]), entity_type="channel", db_name=db)

                # 2. Tracked Contacts
                res = await session.execute(
                    select(Contact.telegram_id).where(Contact.is_tracked == True)
                )
                for row in res.all():
                    if row[0]:
                        deep_track_chunk.delay(telegram_id=str(row[0]), entity_type="user", db_name=db)

        return {"status": "dispatched", "databases": databases}

    return _run_async(_do())


# ========== Campaign Tasks ==========

@celery_app.task(name="src.pipeline.tasks.send_campaign", queue="connectors")
def send_campaign(campaign_id: str, project_id: str, db_name: str | None = None):
    """Send campaign messages to all contacts."""
    from src.db.models import Campaign, CampaignMessage, Contact
    from src.connectors.telegram_connector import TelegramConnector
    from sqlalchemy import select
    from datetime import datetime
    from time import sleep

    async def _do():
        from src.db.database import get_session
        async with get_session(db_name=db_name) as session:
            campaign = await session.get(Campaign, campaign_id)
            if not campaign:
                logger.error("campaign_not_found", campaign_id=campaign_id)
                return {"status": "error", "reason": "campaign not found"}

            # Get all pending messages
            msg_result = await session.execute(
                select(CampaignMessage).where(
                    (CampaignMessage.campaign_id == campaign_id) &
                    (CampaignMessage.status == "pending")
                )
            )
            messages = msg_result.scalars().all()

            if not messages:
                logger.info("no_pending_messages", campaign_id=campaign_id)
                campaign.status = "completed"
                campaign.completed_at = datetime.utcnow()
                await session.commit()
                return {"status": "completed", "sent": 0}

            # Initialize Telegram connector
            try:
                connector = TelegramConnector(db_name=db_name)
                await connector.init_client()
            except Exception as e:
                logger.error("telegram_init_error", error=str(e), campaign_id=campaign_id)
                campaign.status = "failed"
                await session.commit()
                return {"status": "error", "reason": "telegram init failed"}

            sent_count = 0
            failed_count = 0

            # Send messages with rate limiting (1 message per 500ms = 120/min)
            for msg in messages:
                contact = await session.get(Contact, msg.contact_id)
                if not contact:
                    msg.status = "failed"
                    msg.error_message = "contact not found"
                    failed_count += 1
                    continue

                try:
                    # Render message with contact variables
                    rendered_message = campaign.message.format(
                        first_name=contact.first_name or "",
                        last_name=contact.last_name or "",
                        email=contact.email or "",
                        phone=contact.phone or "",
                        company=contact.company or "",
                        position=contact.position or "",
                    )

                    # Send via Telegram (via Telethon)
                    if contact.telegram_id:
                        try:
                            await connector.client.send_message(
                                int(contact.telegram_id),
                                rendered_message
                            )
                            msg.status = "sent"
                            msg.sent_at = datetime.utcnow()
                            sent_count += 1
                        except Exception as e:
                            msg.status = "failed"
                            msg.error_message = str(e)[:255]
                            failed_count += 1
                    else:
                        msg.status = "failed"
                        msg.error_message = "no telegram_id"
                        failed_count += 1

                except Exception as e:
                    msg.status = "failed"
                    msg.error_message = str(e)[:255]
                    failed_count += 1

                # Rate limiting: wait 500ms between messages
                sleep(0.5)

            # Update campaign status
            campaign.sent_count = sent_count
            campaign.failed_count = failed_count
            campaign.status = "completed" if failed_count == 0 else "completed"
            campaign.completed_at = datetime.utcnow()

            await session.commit()

            logger.info(
                "campaign_sent",
                campaign_id=campaign_id,
                sent=sent_count,
                failed=failed_count,
                total=len(messages)
            )

            return {
                "status": "completed",
                "sent": sent_count,
                "failed": failed_count,
                "total": len(messages)
            }

    return _run_async(_do())
