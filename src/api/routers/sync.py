"""API endpoints for Telegram channel synchronization."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.db.database import get_db
from src.db.models import ChannelSyncState, SyncBatchLog, TrackedChannel, TrackedFolder
from src.pipeline.telegram_sync_tasks import scan_channel_metadata, sync_channel_batch, reconcile_channel_sync
from src.pipeline.sync_orchestrator import SyncOrchestrator

router = APIRouter(prefix="/sync", tags=["Sync"])

BATCH_SIZE = 100


@router.get("/status")
async def get_sync_status(db: AsyncSession = Depends(get_db)):
    """Get sync status for all folders and channels."""

    # Get all folders with their channels (eager load relationships)
    result = await db.execute(
        select(TrackedFolder).options(
            selectinload(TrackedFolder.channels).selectinload(TrackedChannel.sync_state)
        )
    )
    folders = result.unique().scalars().all()

    folders_data = []
    for folder in folders:
        channels_data = []
        total_progress = 0
        channel_count = 0

        for channel in folder.channels:
            sync_state = channel.sync_state
            channel_count += 1

            if sync_state:
                total_progress += sync_state.progress_percent

                channels_data.append({
                    "id": str(channel.id),
                    "title": channel.title,
                    "telegram_id": channel.telegram_id,
                    "phase": sync_state.phase,
                    "progress_percent": sync_state.progress_percent,
                    "messages_synced": sync_state.messages_synced,
                    "estimated_total": sync_state.estimated_total_messages,
                    "eta_minutes": sync_state.eta_minutes,
                    "error": sync_state.error_message,
                    "started_at": sync_state.started_at.isoformat() if sync_state.started_at else None,
                    "completed_at": sync_state.completed_at.isoformat() if sync_state.completed_at else None
                })
            else:
                channels_data.append({
                    "id": str(channel.id),
                    "title": channel.title,
                    "telegram_id": channel.telegram_id,
                    "phase": "pending",
                    "progress_percent": 0,
                    "messages_synced": 0,
                    "estimated_total": None,
                    "eta_minutes": None,
                    "error": None,
                    "started_at": None,
                    "completed_at": None
                })

        folder_progress = (total_progress / channel_count * 100) if channel_count > 0 else 0

        folders_data.append({
            "id": str(folder.id),
            "name": folder.name,
            "progress_percent": folder_progress,
            "channel_count": channel_count,
            "channels": channels_data
        })

    return {
        "status": "ok",
        "folders": folders_data
    }


@router.post("/channel/{channel_id}/start")
async def start_channel_sync(channel_id: str, db: AsyncSession = Depends(get_db)):
    """
    Start sync for a channel:
    1. Scan metadata
    2. Create sync state
    3. Queue batch tasks
    """

    # Get channel
    result = await db.execute(
        select(TrackedChannel).where(TrackedChannel.id == UUID(channel_id))
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(404, "Channel not found")

    # Check if already syncing
    if channel.sync_state and channel.sync_state.phase in ["metadata", "syncing"]:
        raise HTTPException(400, "Sync already in progress for this channel")

    # Scan metadata
    try:
        metadata = scan_channel_metadata(channel.telegram_id)
        metadata_result = metadata.get() if hasattr(metadata, 'get') else metadata
    except Exception as e:
        raise HTTPException(400, f"Failed to scan metadata: {str(e)}")

    # Create sync state
    sync_state = ChannelSyncState(
        channel_id=UUID(channel_id),
        phase="syncing",
        earliest_message_date=metadata_result.get("earliest_date"),
        estimated_total_messages=metadata_result.get("total_messages"),
        eta_minutes=int(metadata_result.get("eta_seconds", 0) / 60) if metadata_result.get("eta_seconds") else None
    )
    db.add(sync_state)
    await db.flush()

    # Queue batch tasks
    batch_count = metadata_result.get("batch_count", 0)
    for batch_num in range(batch_count):
        offset = batch_num * BATCH_SIZE

        sync_channel_batch.apply_async(
            kwargs={
                "channel_id": channel.telegram_id,
                "sync_state_id": str(sync_state.id),
                "batch_number": batch_num,
                "offset": offset,
                "limit": BATCH_SIZE
            },
            countdown=batch_num * 1  # 1 second delay between batches
        )

    await db.commit()

    return {
        "status": "queued",
        "sync_state_id": str(sync_state.id),
        "estimated_batches": batch_count,
        "eta_minutes": sync_state.eta_minutes
    }


@router.get("/channel/{channel_id}/status")
async def get_channel_sync_status(channel_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed sync status for a channel."""

    result = await db.execute(
        select(TrackedChannel).where(TrackedChannel.id == UUID(channel_id))
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(404, "Channel not found")

    if not channel.sync_state:
        return {
            "id": channel_id,
            "title": channel.title,
            "status": "not_started",
            "sync_state": None
        }

    sync_state = channel.sync_state

    # Get batch logs
    batch_result = await db.execute(
        select(SyncBatchLog)
        .where(SyncBatchLog.sync_state_id == sync_state.id)
        .order_by(SyncBatchLog.batch_number)
    )
    batches = batch_result.scalars().all()

    return {
        "id": channel_id,
        "title": channel.title,
        "sync_state": {
            "id": str(sync_state.id),
            "phase": sync_state.phase,
            "progress_percent": sync_state.progress_percent,
            "messages_synced": sync_state.messages_synced,
            "estimated_total": sync_state.estimated_total_messages,
            "eta_minutes": sync_state.eta_minutes,
            "started_at": sync_state.started_at.isoformat() if sync_state.started_at else None,
            "completed_at": sync_state.completed_at.isoformat() if sync_state.completed_at else None,
            "error": sync_state.error_message
        },
        "batches": [
            {
                "batch_number": b.batch_number,
                "status": b.status,
                "messages": b.messages_in_batch,
                "offset": b.requested_offset,
                "duration_ms": b.duration_ms,
                "error": b.error_message,
                "retry_attempt": b.retry_attempt
            }
            for b in batches
        ]
    }


@router.post("/folder/{folder_id}/start")
async def start_folder_sync(folder_id: str, db: AsyncSession = Depends(get_db)):
    """Start sync for all channels in a folder."""

    result = await db.execute(
        select(TrackedFolder).where(TrackedFolder.id == UUID(folder_id)).options(
            selectinload(TrackedFolder.channels).selectinload(TrackedChannel.sync_state)
        )
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(404, "Folder not found")

    queued_count = 0
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    for channel in folder.channels:
        if channel.sync_state and channel.sync_state.phase in ["metadata", "syncing"]:
            continue

        try:
            # Run the blocking scan_channel_metadata in a thread pool
            metadata_result = await loop.run_in_executor(executor, scan_channel_metadata, channel.telegram_id)

            sync_state = ChannelSyncState(
                channel_id=channel.id,
                phase="syncing",
                earliest_message_date=metadata_result.get("earliest_date"),
                estimated_total_messages=metadata_result.get("total_messages"),
                eta_minutes=int(metadata_result.get("eta_seconds", 0) / 60) if metadata_result.get("eta_seconds") else None
            )
            db.add(sync_state)
            await db.flush()

            batch_count = metadata_result.get("batch_count", 0)
            for batch_num in range(batch_count):
                offset = batch_num * BATCH_SIZE
                sync_channel_batch.apply_async(
                    kwargs={
                        "channel_id": channel.telegram_id,
                        "sync_state_id": str(sync_state.id),
                        "batch_number": batch_num,
                        "offset": offset,
                        "limit": BATCH_SIZE
                    },
                    countdown=batch_num * 1
                )

            queued_count += 1

        except Exception as e:
            print(f"Error queuing sync for channel {channel.id}: {e}")

    await db.commit()

    return {
        "status": "queued",
        "folder_id": folder_id,
        "channels_queued": queued_count,
        "total_channels": len(folder.channels)
    }


@router.post("/manual")
async def trigger_manual_sync(db: AsyncSession = Depends(get_db)):
    """Trigger manual sync of folders and personal contacts."""
    try:
        orchestrator = SyncOrchestrator()
        await orchestrator.run()

        return {
            "status": "synced",
            "message": "Folders and personal contacts synchronized"
        }
    except Exception as e:
        raise HTTPException(500, f"Sync failed: {str(e)}")
