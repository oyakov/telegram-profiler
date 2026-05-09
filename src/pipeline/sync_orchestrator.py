"""
Sync Orchestrator - Automated task manager for Telegram channel synchronization.

Runs every 5 minutes to:
1. Detect new/updated folders
2. Detect new channels
3. Monitor in-flight syncs and update ETA
4. Auto-retry failed batches
5. Trigger folder-wide syncs when needed
"""

import asyncio
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, and_

from src.db.database import get_session
from src.db.models import (
    TrackedFolder, TrackedChannel, ChannelSyncState,
    SyncBatchLog, UserProfile
)
from src.connectors.telegram_connector import TelegramConnector
from src.pipeline.telegram_sync_tasks import (
    sync_channel_batch, scan_channel_metadata, reconcile_channel_sync
)
from src.pipeline.celery_app import celery_app

logger = structlog.get_logger()

BATCH_SIZE = 100
MAX_RETRIES_PER_CYCLE = 10


class SyncOrchestrator:
    """Manages automated sync workflow."""

    def __init__(self):
        self.db_name = "crm"
        self.connector = TelegramConnector(db_name=self.db_name)

    async def run(self):
        """Main orchestration loop - called every 5 minutes."""
        logger.info("sync_orchestrator_cycle_start")

        async with get_session(db_name=self.db_name) as session:
            try:
                # Step 1: Check Telegram auth status
                is_auth = await self.connector.is_authorized()
                if not is_auth:
                    logger.warning("telegram_not_authenticated")
                    return

                # Step 2: Detect and sync new/updated folders
                await self._sync_folders(session)

                # Step 3: Detect and queue new channels
                await self._queue_new_channels(session)

                # Step 4: Monitor active syncs and update ETA
                await self._update_active_syncs(session)

                # Step 5: Auto-retry failed batches
                await self._retry_failed_batches(session)

                # Step 6: Reconcile completed syncs
                await self._reconcile_completed_syncs(session)

                logger.info("sync_orchestrator_cycle_complete")

            except Exception as e:
                logger.error("sync_orchestrator_error", error=str(e), exc_info=True)

    async def _sync_folders(self, session):
        """
        Detect new/updated Telegram folders.
        For each folder, cache the channel list and detect changes.
        """
        logger.info("sync_folders_start")

        try:
            # Get list of Telegram folders (returns folder with peer_ids)
            tg_folders = await self.connector.list_telegram_folders()

            for tg_folder in tg_folders:
                folder_id = tg_folder.get("id")
                folder_name = tg_folder.get("name", f"Folder {folder_id}")

                # Get or create DB folder
                result = await session.execute(
                    select(TrackedFolder).where(
                        TrackedFolder.telegram_folder_id == str(folder_id)
                    )
                )
                db_folder = result.scalar_one_or_none()

                if not db_folder:
                    db_folder = TrackedFolder(
                        name=folder_name,
                        telegram_folder_id=str(folder_id),
                        description=f"Auto-imported from Telegram"
                    )
                    session.add(db_folder)
                    await session.flush()
                    logger.info("new_folder_detected", folder=folder_name)

                # Get full channel info from peer_ids
                peer_ids = tg_folder.get("peer_ids", [])
                if peer_ids:
                    tg_channels = await self.connector.import_folder_channels(peer_ids)
                else:
                    tg_channels = []

                # Cache current channel list (by telegram_id)
                current_channels = set(str(ch.get("telegram_id")) for ch in tg_channels)
                cached_channels = set(db_folder.cached_channels or [])

                # Check for new/removed channels
                new_channels = current_channels - cached_channels
                removed_channels = cached_channels - current_channels

                if new_channels or removed_channels:
                    logger.info(
                        "folder_channels_changed",
                        folder=db_folder.name,
                        new=len(new_channels),
                        removed=len(removed_channels)
                    )

                # Create TrackedChannel records for new channels
                for tg_channel in tg_channels:
                    channel_id = str(tg_channel.get("telegram_id"))
                    if channel_id in new_channels:
                        # Check if channel already exists
                        result = await session.execute(
                            select(TrackedChannel).where(
                                TrackedChannel.telegram_id == channel_id
                            )
                        )
                        existing = result.scalar_one_or_none()

                        if not existing:
                            tracked_channel = TrackedChannel(
                                folder_id=db_folder.id,
                                telegram_id=channel_id,
                                title=tg_channel.get("title", f"Channel {channel_id}"),
                                username=tg_channel.get("username"),
                                entity_type=tg_channel.get("entity_type", "channel")
                            )
                            session.add(tracked_channel)
                            logger.info("new_channel_created", channel=tracked_channel.title, folder=db_folder.name)

                # Update cache
                db_folder.cached_channels = list(current_channels)
                db_folder.last_scan_at = datetime.now(timezone.utc)

            await session.commit()
            logger.info("sync_folders_complete", folder_count=len(tg_folders))

        except Exception as e:
            logger.error("sync_folders_error", error=str(e))

    async def _queue_new_channels(self, session):
        """
        Detect channels without sync_state and queue them for sync.
        """
        from sqlalchemy.orm import selectinload
        logger.info("queue_new_channels_start")

        try:
            # Get all channels with eager loading of sync_state
            result = await session.execute(
                select(TrackedChannel).options(selectinload(TrackedChannel.sync_state))
            )
            all_channels = result.unique().scalars().all()

            queued_count = 0

            for channel in all_channels:
                # Skip if already has sync state in progress
                if channel.sync_state and channel.sync_state.phase in ["metadata", "syncing"]:
                    continue

                # Skip if completed recently (within 7 days)
                if channel.sync_state and channel.sync_state.phase == "complete":
                    if channel.sync_state.completed_at:
                        age = datetime.now(timezone.utc) - channel.sync_state.completed_at
                        if age < timedelta(days=7):
                            continue

                try:
                    # Create new sync state
                    sync_state = ChannelSyncState(
                        channel_id=channel.id,
                        phase="metadata",
                        started_at=datetime.now(timezone.utc)
                    )
                    session.add(sync_state)
                    await session.flush()

                    # Queue metadata scan task
                    logger.info("queuing_metadata_scan", channel=channel.title)
                    scan_channel_metadata.apply_async(
                        args=[channel.telegram_id],
                        task_id=f"metadata_{sync_state.id}"
                    )

                    queued_count += 1

                except Exception as e:
                    logger.error(
                        "queue_channel_error",
                        channel=channel.title,
                        error=str(e)
                    )

            if queued_count > 0:
                await session.commit()

            logger.info("queue_new_channels_complete", queued=queued_count)

        except Exception as e:
            logger.error("queue_new_channels_error", error=str(e))

    async def _update_active_syncs(self, session):
        """
        Monitor active syncs and update progress/ETA.
        Calculate sync rate and estimate remaining time.
        """
        logger.info("update_active_syncs_start")

        try:
            result = await session.execute(
                select(ChannelSyncState).where(
                    ChannelSyncState.phase.in_(["metadata", "syncing"])
                )
            )
            active_syncs = result.scalars().all()

            for sync_state in active_syncs:
                if sync_state.started_at and sync_state.estimated_total_messages:
                    elapsed = datetime.now(timezone.utc) - sync_state.started_at
                    elapsed_seconds = elapsed.total_seconds()

                    if elapsed_seconds > 0:
                        # Calculate rate (messages per second)
                        rate = sync_state.messages_synced / elapsed_seconds

                        if rate > 0:
                            remaining = sync_state.estimated_total_messages - sync_state.messages_synced
                            eta_seconds = remaining / rate

                            sync_state.eta_minutes = int(eta_seconds / 60)
                            sync_state.estimated_completion = (
                                datetime.now(timezone.utc) + timedelta(seconds=eta_seconds)
                            )

            await session.commit()
            logger.info("update_active_syncs_complete", count=len(active_syncs))

        except Exception as e:
            logger.error("update_active_syncs_error", error=str(e))

    async def _retry_failed_batches(self, session):
        """
        Find failed batches and retry them (max 3 retries each).
        Limit retries per cycle to avoid overload.
        """
        logger.info("retry_failed_batches_start")

        try:
            result = await session.execute(
                select(SyncBatchLog).where(
                    and_(
                        SyncBatchLog.status == "failed",
                        SyncBatchLog.retry_attempt < 3
                    )
                ).order_by(SyncBatchLog.updated_at.desc())
                .limit(MAX_RETRIES_PER_CYCLE)
            )
            failed_batches = result.scalars().all()

            for batch in failed_batches:
                try:
                    batch.retry_attempt += 1
                    batch.status = "pending"

                    # Get sync state to find channel
                    sync_state = batch.sync_state
                    channel = sync_state.channel

                    logger.info(
                        "retrying_batch",
                        batch=batch.batch_number,
                        channel=channel.title,
                        attempt=batch.retry_attempt
                    )

                    # Queue retry task with delay
                    sync_channel_batch.apply_async(
                        kwargs={
                            "channel_id": channel.telegram_id,
                            "sync_state_id": str(sync_state.id),
                            "batch_number": batch.batch_number,
                            "offset": batch.requested_offset,
                            "limit": batch.messages_in_batch or BATCH_SIZE
                        },
                        countdown=60 * batch.retry_attempt  # 1m, 2m, 3m delays
                    )

                except Exception as e:
                    logger.error(
                        "retry_batch_error",
                        batch=batch.id,
                        error=str(e)
                    )

            await session.commit()
            logger.info("retry_failed_batches_complete", count=len(failed_batches))

        except Exception as e:
            logger.error("retry_failed_batches_error", error=str(e))

    async def _reconcile_completed_syncs(self, session):
        """
        Find syncs where all batches are complete and trigger reconciliation.
        Detect gaps and orphaned messages.
        """
        logger.info("reconcile_completed_syncs_start")

        try:
            # Get syncs in "syncing" state
            result = await session.execute(
                select(ChannelSyncState).where(
                    ChannelSyncState.phase == "syncing"
                )
            )
            syncing_states = result.scalars().all()

            for sync_state in syncing_states:
                # Count pending/processing batches
                batch_result = await session.execute(
                    select(SyncBatchLog).where(
                        and_(
                            SyncBatchLog.sync_state_id == sync_state.id,
                            SyncBatchLog.status.in_(["pending", "processing"])
                        )
                    )
                )
                pending_batches = batch_result.scalars().all()

                # If no pending batches, trigger reconciliation
                if not pending_batches:
                    logger.info("triggering_reconciliation", sync_state=sync_state.id)

                    sync_state.phase = "reconciling"
                    await session.commit()

                    # Queue reconciliation task
                    reconcile_channel_sync.apply_async(
                        args=[str(sync_state.id)]
                    )

            logger.info("reconcile_completed_syncs_complete")

        except Exception as e:
            logger.error("reconcile_completed_syncs_error", error=str(e))


@celery_app.task(name="sync_orchestrator")
def sync_orchestrator_task():
    """
    Celery task - runs every 5 minutes via beat scheduler.
    """
    orchestrator = SyncOrchestrator()
    asyncio.run(orchestrator.run())


# For direct testing
async def run_orchestrator():
    """Run orchestrator once (for testing)."""
    orchestrator = SyncOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(run_orchestrator())
