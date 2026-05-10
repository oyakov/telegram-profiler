"""Celery tasks for Telegram channel history synchronization."""

import asyncio
import structlog
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from celery import shared_task
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.errors import FloodWaitError

from src.db.database import get_session
from src.connectors.telegram_connector import TelegramConnector

logger = structlog.get_logger()

# Config
BATCH_SIZE = 100
MESSAGES_PER_SECOND = 30  # Conservative: Telegram allows 30-60
BATCH_DELAY_SECONDS = (BATCH_SIZE / MESSAGES_PER_SECOND) + 0.1
MAX_RETRIES = 3


@shared_task(bind=True, max_retries=MAX_RETRIES, autoretry_for=(FloodWaitError,), queue="connectors")
def sync_channel_batch(
    self,
    channel_id: str,
    sync_state_id: str,
    batch_number: int,
    offset: int,
    limit: int = BATCH_SIZE
):
    """
    Download a single batch of messages for a channel.
    Targeted as a small, idempotent unit of work.
    """

    async def _sync_batch():
        from sqlalchemy import select, update, func
        from sqlalchemy.orm import joinedload
        from src.db.models import ChannelSyncState, SyncBatchLog, Message, MessageContact, Contact
        from src.connectors.telegram_connector import TelegramConnector
        from datetime import datetime, timezone
        from uuid import UUID

        batch_log = None
        async with get_session(db_name="crm") as session:
            try:
                # 1. Get sync state and channel
                result = await session.execute(
                    select(ChannelSyncState)
                    .options(joinedload(ChannelSyncState.channel))
                    .where(ChannelSyncState.id == UUID(sync_state_id))
                )
                sync_state = result.scalar_one_or_none()

                if not sync_state:
                    logger.error("sync_state_not_found", sync_state_id=sync_state_id)
                    raise ValueError(f"SyncState {sync_state_id} not found")

                # 2. Create batch log
                batch_log = SyncBatchLog(
                    sync_state_id=UUID(sync_state_id),
                    batch_number=batch_number,
                    requested_offset=offset,
                    status="running",
                    started_at=datetime.now(timezone.utc)
                )
                session.add(batch_log)
                await session.flush()

                # 3. Get Telethon client
                connector = TelegramConnector(db_name="crm")
                client = await connector._get_client()
                await client.connect()

                # 4. Resolve entity
                peer_id = int(channel_id)
                try:
                    entity = await client.get_entity(peer_id)
                except Exception:
                    entity = await client.get_entity(int(f"-100{abs(peer_id)}"))

                # 5. Fetch messages
                messages = []
                async for msg in client.iter_messages(entity, offset_id=0, add_offset=offset, limit=limit):
                    messages.append(msg)

                # 6. Process and save
                message_count = 0
                for msg in messages:
                    source_msg_id = f"{entity.id}_{msg.id}"
                    
                    # Deduplication
                    exists_stmt = select(func.count(Message.id)).where(Message.source_message_id == source_msg_id)
                    exists = await session.execute(exists_stmt)
                    if exists.scalar() > 0:
                        continue

                    # Sender resolution
                    sender_entity = msg.sender or entity
                    contact = await connector._get_or_create_contact(session, sender_entity)
                    
                    # Create message
                    message = Message(
                        contact_id=contact.id,
                        source="telegram",
                        source_message_id=source_msg_id,
                        direction="outgoing" if msg.out else "incoming",
                        content=msg.text or "",
                        group_id=str(entity.id),
                        group_name=getattr(entity, "title", "Unknown"),
                        timestamp=msg.date
                    )
                    session.add(message)
                    await session.flush()
                    
                    # Create association
                    session.add(MessageContact(message_id=message.id, contact_id=contact.id, role="sender"))
                    message_count += 1

                # 7. Update progress
                sync_state.messages_synced += message_count
                if sync_state.estimated_total_messages:
                    sync_state.progress_percent = (
                        sync_state.messages_synced / sync_state.estimated_total_messages * 100
                    )
                if sync_state.channel:
                    sync_state.channel.last_sync_at = datetime.now(timezone.utc)

                # 8. Mark batch success
                batch_log.status = "success"
                batch_log.messages_in_batch = message_count
                batch_log.completed_at = datetime.now(timezone.utc)

                await session.commit()
                logger.info("batch_complete", channel=channel_id, batch=batch_number, synced=message_count)
                await client.disconnect()

            except FloodWaitError as e:
                logger.warning("flood_wait", batch=batch_number, seconds=e.seconds)
                batch_log.status = "failed"
                batch_log.error_message = f"FloodWait: {e.seconds}s"
                await session.commit()
                raise self.retry(countdown=min(e.seconds * 2, 3600))

            except Exception as e:
                logger.error("batch_error", batch=batch_number, error=str(e), exc_info=True)
                if batch_log:
                    batch_log.status = "failed"
                    batch_log.error_message = str(e)
                await session.commit()
                raise e

    asyncio.run(_sync_batch())


@shared_task(queue="connectors")
def scan_channel_metadata(channel_id: str, sync_state_id: Optional[str] = None) -> dict:
    """
    Scan channel metadata to determine:
    - Earliest message date
    - Estimated total message count
    - Batch count and ETA
    """

    async def _scan():
        from src.db.models import ChannelSyncState
        from sqlalchemy import update
        from telethon.tl.functions.messages import GetHistoryRequest

        # Get Telethon client
        connector = TelegramConnector(db_name="crm")
        client = await connector._get_client()

        try:
            await client.connect()

            # Resolve entity (handling -100 prefix and type conversion)
            peer_id = int(channel_id)
            try:
                entity = await client.get_entity(peer_id)
            except Exception:
                try:
                    # Try with -100 prefix for channels
                    entity = await client.get_entity(int(f"-100{abs(peer_id)}"))
                except Exception as e:
                    logger.error("entity_resolution_failed", channel_id=channel_id, error=str(e))
                    raise e

            # Get first (oldest) message to get total count
            result = await client(GetHistoryRequest(
                peer=entity,
                offset_id=0,
                offset_date=None,
                add_offset=0,
                limit=1,
                max_id=0,
                min_id=0,
                hash=0
            ))

            earliest_date = None
            total_count = getattr(result, 'count', 0)

            if result.messages:
                msg = result.messages[0]
                if hasattr(msg, 'date'):
                    earliest_date = msg.date

            batch_count = (total_count + BATCH_SIZE - 1) // BATCH_SIZE
            eta_seconds = batch_count * BATCH_DELAY_SECONDS

            logger.info(
                "channel_metadata_scanned",
                channel_id=channel_id,
                total_messages=total_count,
                batches=batch_count,
                sync_state_id=sync_state_id
            )

            res_data = {
                "earliest_date": earliest_date.isoformat() if earliest_date else None,
                "total_messages": total_count,
                "batch_count": batch_count,
                "eta_seconds": eta_seconds
            }

            # If sync_state_id provided, update DB and queue batches
            if sync_state_id:
                async with get_session(db_name="crm") as session:
                    sync_state = await session.get(ChannelSyncState, UUID(sync_state_id))
                    if sync_state:
                        sync_state.phase = "syncing"
                        sync_state.earliest_message_date = earliest_date
                        sync_state.estimated_total_messages = total_count
                        sync_state.eta_minutes = int(eta_seconds / 60)
                        sync_state.started_at = datetime.now(timezone.utc)
                        await session.commit()

                        # Queue batch tasks
                        for batch_num in range(batch_count):
                            offset = batch_num * BATCH_SIZE
                            sync_channel_batch.apply_async(
                                kwargs={
                                    "channel_id": channel_id,
                                    "sync_state_id": sync_state_id,
                                    "batch_number": batch_num,
                                    "offset": offset,
                                    "limit": BATCH_SIZE
                                },
                                countdown=batch_num * 1  # 1s delay per batch
                            )
            
            return res_data

        except Exception as e:
            logger.error("metadata_scan_error", channel_id=channel_id, error=str(e))
            if sync_state_id:
                async with get_session(db_name="crm") as session:
                    sync_state = await session.get(ChannelSyncState, UUID(sync_state_id))
                    if sync_state:
                        sync_state.phase = "error"
                        sync_state.error_message = str(e)
                        await session.commit()
            raise e

        finally:
            try:
                await client.disconnect()
            except Exception: pass

    return asyncio.run(_scan())


@shared_task(queue="connectors")
def reconcile_channel_sync(sync_state_id: str):
    """
    Post-sync reconciliation:
    1. Detect gaps in message sequence
    2. Re-download gap ranges
    3. Mark sync complete
    """

    async def _reconcile():
        async with get_session(db_name="crm") as session:
            from sqlalchemy import select

            sync_state = await session.get(ChannelSyncState, UUID(sync_state_id))
            if not sync_state: return

            # Placeholder for actual reconciliation logic
            sync_state.phase = "complete"
            sync_state.completed_at = datetime.now(timezone.utc)
            await session.commit()

            logger.info("sync_reconcile_complete", sync_state=sync_state_id)

    asyncio.run(_reconcile())
