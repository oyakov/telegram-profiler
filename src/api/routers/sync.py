"""API endpoints for Telegram channel synchronization."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, timezone

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
    1. Create sync state in 'metadata' phase
    2. Queue metadata scan task which will later queue batches
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

    # Create new sync state
    sync_state = ChannelSyncState(
        channel_id=UUID(channel_id),
        phase="metadata",
        started_at=datetime.now(timezone.utc)
    )
    db.add(sync_state)
    await db.flush()

    # Queue metadata scan task
    scan_channel_metadata.apply_async(
        args=[channel.telegram_id, str(sync_state.id)],
        task_id=f"metadata_{sync_state.id}"
    )

    await db.commit()

    return {
        "status": "queued",
        "sync_state_id": str(sync_state.id),
        "phase": "metadata"
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
    import structlog
    logger = structlog.get_logger()
    logger.info("start_folder_sync_request", folder_id=folder_id)

    result = await db.execute(
        select(TrackedFolder).where(TrackedFolder.id == UUID(folder_id)).options(
            selectinload(TrackedFolder.channels).selectinload(TrackedChannel.sync_state)
        )
    )
    folder = result.scalar_one_or_none()
    if not folder:
        logger.warning("folder_not_found", folder_id=folder_id)
        raise HTTPException(404, "Folder not found")

    logger.info("folder_found", folder_name=folder.name, channels_count=len(folder.channels))
    queued_count = 0

    for channel in folder.channels:
        if channel.sync_state and channel.sync_state.phase in ["metadata", "syncing"]:
            logger.info("skipping_channel_already_syncing", channel_id=str(channel.id), phase=channel.sync_state.phase)
            continue

        try:
            # Create new sync state
            sync_state = ChannelSyncState(
                channel_id=channel.id,
                phase="metadata",
                progress_percent=0.1, # Set small progress so UI immediately reacts
                started_at=datetime.now(timezone.utc)
            )
            db.add(sync_state)
            await db.flush()

            # Queue metadata scan task
            logger.info("queuing_metadata_scan", channel_id=str(channel.id), telegram_id=channel.telegram_id, sync_state_id=str(sync_state.id))
            scan_channel_metadata.apply_async(
                args=[channel.telegram_id, str(sync_state.id)],
                task_id=f"metadata_{sync_state.id}",
                queue="connectors"
            )

            queued_count += 1

        except Exception as e:
            logger.error("queue_folder_channel_error", channel_id=str(channel.id), error=str(e))

    await db.commit()
    logger.info("start_folder_sync_committed", folder_id=folder_id, queued_count=queued_count)

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
