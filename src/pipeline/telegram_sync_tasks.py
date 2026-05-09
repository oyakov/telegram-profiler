"""Celery tasks for Telegram channel history synchronization."""

import asyncio
import structlog
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from celery import shared_task
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import GetHistoryRequest

from src.db.database import get_session
from src.db.models import ChannelSyncState, SyncBatchLog, Message, Contact, MessageContact, TrackedChannel
from src.connectors.telegram_connector import TelegramConnector

logger = structlog.get_logger()

# Rate limiting constants
BATCH_SIZE = 100
MESSAGES_PER_SECOND = 30  # Conservative: Telegram allows 30-60
BATCH_DELAY_SECONDS = (BATCH_SIZE / MESSAGES_PER_SECOND) + 0.1
MAX_RETRIES = 3


@shared_task(bind=True, max_retries=MAX_RETRIES, autoretry_for=(FloodWaitError,))
def sync_channel_batch(
    self,
    channel_id: str,
    sync_state_id: str,
    batch_number: int,
    offset: int,
    limit: int = BATCH_SIZE
):
    """
    Download one batch of messages from a Telegram channel.

    Args:
        channel_id: Telegram channel ID (string)
        sync_state_id: UUID of ChannelSyncState record
        batch_number: Sequential batch number
        offset: Message offset (pagination)
        limit: Messages to fetch (default 100)
    """

    async def _sync_batch():
        async with get_session(db_name="crm") as session:
            # Get sync state
            sync_state = await session.get(ChannelSyncState, UUID(sync_state_id))
            if not sync_state:
                logger.error("sync_state_not_found", sync_state_id=sync_state_id)
                raise ValueError(f"SyncState {sync_state_id} not found")

            # Create batch log entry
            batch_log = SyncBatchLog(
                sync_state_id=UUID(sync_state_id),
                batch_number=batch_number,
                requested_offset=offset,
                status="processing",
                started_at=datetime.now(timezone.utc)
            )
            session.add(batch_log)
            await session.flush()

            try:
                # Get Telethon connector
                connector = TelegramConnector(db_name="crm")
                client = connector._get_client()
                await client.connect()

                # Fetch messages
                logger.info(
                    "batch_download_start",
                    channel_id=channel_id,
                    batch=batch_number,
                    offset=offset,
                    limit=limit
                )

                result = await client(GetHistoryRequest(
                    peer=int(channel_id),
                    offset=offset,
                    limit=limit,
                    add_offset=0,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))

                messages = result.messages if result.messages else []

                if not messages:
                    logger.info("batch_empty", batch=batch_number, offset=offset)
                    batch_log.status = "success"
                    batch_log.messages_in_batch = 0
                    batch_log.completed_at = datetime.now(timezone.utc)
                    await session.commit()
                    await client.disconnect()
                    return

                # Process and insert messages
                message_count = 0
                for msg in messages:
                    if not msg or not hasattr(msg, 'id'):
                        continue

                    # Extract sender contact
                    sender_id = None
                    if msg.from_id:
                        if hasattr(msg.from_id, 'user_id'):
                            sender_id = str(msg.from_id.user_id)
                        elif isinstance(msg.from_id, int):
                            sender_id = str(msg.from_id)

                    # Get or create contact for sender
                    contact = None
                    if sender_id:
                        from sqlalchemy import select
                        result = await session.execute(
                            select(Contact).where(Contact.telegram_id == sender_id)
                        )
                        contact = result.scalar_one_or_none()

                        if not contact:
                            contact = Contact(
                                telegram_id=sender_id,
                                first_name=getattr(msg.sender, 'first_name', 'Unknown') if hasattr(msg, 'sender') else 'Unknown',
                                source="telegram"
                            )
                            session.add(contact)
                            await session.flush()

                    # Create message record
                    message = Message(
                        contact_id=contact.id if contact else None,
                        source="telegram",
                        source_message_id=str(msg.id),
                        content=msg.text if hasattr(msg, 'text') else None,
                        direction="incoming",
                        group_id=channel_id,
                        timestamp=msg.date if hasattr(msg, 'date') else datetime.now(timezone.utc),
                        raw_json={
                            "msg_id": msg.id,
                            "from_id": sender_id,
                            "date": str(msg.date) if hasattr(msg, 'date') else None,
                            "text": msg.text if hasattr(msg, 'text') else None
                        }
                    )
                    session.add(message)
                    message_count += 1

                # Update progress
                sync_state.messages_synced += message_count
                sync_state.last_message_id = str(messages[-1].id) if messages else None
                sync_state.last_message_date = messages[-1].date if messages and hasattr(messages[-1], 'date') else None

                if sync_state.estimated_total_messages:
                    sync_state.progress_percent = (
                        sync_state.messages_synced / sync_state.estimated_total_messages * 100
                    )

                # Update batch log
                batch_log.status = "success"
                batch_log.messages_in_batch = message_count
                batch_log.oldest_message_id = str(messages[-1].id) if messages else None
                batch_log.newest_message_id = str(messages[0].id) if messages else None
                batch_log.completed_at = datetime.now(timezone.utc)

                if batch_log.started_at and batch_log.completed_at:
                    batch_log.duration_ms = int(
                        (batch_log.completed_at - batch_log.started_at).total_seconds() * 1000
                    )

                await session.commit()

                logger.info(
                    "batch_download_complete",
                    batch=batch_number,
                    messages=message_count,
                    progress=sync_state.progress_percent
                )

                await client.disconnect()

            except FloodWaitError as e:
                logger.warning("flood_wait", batch=batch_number, seconds=e.seconds)
                batch_log.status = "failed"
                batch_log.error_message = f"FloodWaitError: {e.seconds} seconds"
                batch_log.retry_attempt = self.request.retries
                batch_log.completed_at = datetime.now(timezone.utc)
                await session.commit()

                # Retry with exponential backoff
                raise self.retry(countdown=min(e.seconds * 2, 3600))

            except Exception as e:
                logger.error(
                    "batch_download_error",
                    batch=batch_number,
                    error=str(e),
                    exc_info=True
                )
                batch_log.status = "failed"
                batch_log.error_message = str(e)
                batch_log.retry_attempt = self.request.retries
                batch_log.completed_at = datetime.now(timezone.utc)
                await session.commit()
                raise

    # Run async function
    asyncio.run(_sync_batch())


@shared_task
def scan_channel_metadata(channel_id: str) -> dict:
    """
    Scan channel metadata to determine:
    - Earliest message date
    - Estimated total message count
    - Batch count and ETA

    Args:
        channel_id: Telegram channel ID

    Returns:
        Dictionary with metadata
    """

    async def _scan():
        connector = TelegramConnector(db_name="crm")
        client = connector._get_client()

        try:
            await client.connect()

            # Get first (oldest) message
            result = await client(GetHistoryRequest(
                peer=int(channel_id),
                offset=0,
                limit=1,
                add_offset=0,
                max_id=0,
                min_id=0,
                hash=0
            ))

            earliest_date = None
            total_count = result.count if hasattr(result, 'count') else 0

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
                eta_seconds=eta_seconds
            )

            return {
                "earliest_date": earliest_date.isoformat() if earliest_date else None,
                "total_messages": total_count,
                "batch_count": batch_count,
                "eta_seconds": eta_seconds
            }

        finally:
            await client.disconnect()

    return asyncio.run(_scan())


@shared_task
def reconcile_channel_sync(sync_state_id: str):
    """
    Post-sync reconciliation:
    1. Detect gaps in message sequence
    2. Re-download gap ranges
    3. Mark sync complete

    Args:
        sync_state_id: UUID of ChannelSyncState
    """

    async def _reconcile():
        async with get_session(db_name="crm") as session:
            from sqlalchemy import select

            sync_state = await session.get(ChannelSyncState, UUID(sync_state_id))
            if not sync_state:
                logger.error("sync_state_not_found", sync_state_id=sync_state_id)
                return

            # Get all batch logs
            result = await session.execute(
                select(SyncBatchLog)
                .where(SyncBatchLog.sync_state_id == UUID(sync_state_id))
                .order_by(SyncBatchLog.batch_number)
            )
            batches = result.scalars().all()

            # Detect gaps
            gaps = []
            for i, batch in enumerate(batches):
                if i == 0:
                    continue
                prev = batches[i - 1]

                expected_offset = prev.requested_offset + (prev.messages_in_batch or BATCH_SIZE)
                if batch.requested_offset > expected_offset:
                    gaps.append({
                        "start": expected_offset,
                        "end": batch.requested_offset
                    })

            # Queue gap-fill tasks
            for gap in gaps:
                logger.info("gap_detected", sync_state=sync_state_id, gap=gap)
                sync_channel_batch.delay(
                    channel_id=str(sync_state.channel_id),
                    sync_state_id=sync_state_id,
                    batch_number=-1,  # Marker for gap-fill
                    offset=gap['start'],
                    limit=gap['end'] - gap['start']
                )

            # Mark complete
            sync_state.phase = "complete"
            sync_state.completed_at = datetime.now(timezone.utc)
            await session.commit()

            logger.info("sync_reconcile_complete", sync_state=sync_state_id, gaps=len(gaps))

    asyncio.run(_reconcile())
