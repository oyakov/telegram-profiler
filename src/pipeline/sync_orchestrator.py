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
from sqlalchemy import select, and_, func

from src.db.database import get_session
from src.db.models import (
    TrackedFolder, TrackedChannel, ChannelSyncState,
    SyncBatchLog, UserProfile
)
from src.connectors.telegram_connector import TelegramConnector
from src.db.repository import MessageRepository, ContactRepository, SyncStateRepository
from src.services.telegram.client_factory import TelegramClientFactory
from src.services.telegram.auth_service import TelegramAuthService
from src.services.telegram.management_service import TelegramManagementService
from src.services.telegram.sync_service import TelegramSyncService
from src.services.telegram.entity_service import TelegramEntityService
from src.pipeline.telegram_sync_tasks import (
    sync_channel_batch, scan_channel_metadata, reconcile_channel_sync
)
from src.pipeline.celery_app import celery_app

logger = structlog.get_logger()

BATCH_SIZE = 100
MAX_RETRIES_PER_CYCLE = 10
# Cap how many batch tasks are queued per orchestrator cycle to avoid flooding the
# connectors queue with thousands of tasks for large channels (e.g. 100k messages).
MAX_BATCHES_PER_CYCLE = 50


class SyncOrchestrator:
    """Manages automated sync workflow."""

    def __init__(self, db_name: str | None = None):
        from src.core.config import get_settings
        self.db_name = db_name or get_settings().postgres_db
        
        # Initialize Telegram Services
        self.factory = TelegramClientFactory(db_name=self.db_name)
        self.auth = TelegramAuthService(self.factory)
        self.entity = TelegramEntityService(self.factory)
        self.sync_svc = TelegramSyncService(self.factory, self.entity)
        self.mgmt = TelegramManagementService(self.factory)
        
        # Keep connector facade for backward compatibility in some tasks if necessary
        self.connector = TelegramConnector(db_name=self.db_name)

    async def run(self):
        """Main orchestration loop - called every 5 minutes."""
        logger.info("sync_orchestrator_cycle_start")

        async with get_session(db_name=self.db_name) as session:
            try:
                self.sync_repo = SyncStateRepository(session)
                # Step 1: Check Telegram auth status
                is_auth = await self.auth.is_authorized()
                if not is_auth:
                    logger.warning("telegram_not_authenticated")
                    return

                # Step 2: Detect and sync new/updated folders
                await self._sync_folders(session)

                # Step 3: Detect and queue metadata scans ONLY (blocks batch task queueing)
                await self._queue_new_channels(session)

                # Step 4: Queue batch tasks for channels with completed metadata
                await self._queue_batch_tasks_for_metadata(session)

                # Step 5: Monitor active syncs and update ETA
                await self._update_active_syncs(session)

                # Step 6: Auto-retry failed batches
                await self._retry_failed_batches(session)

                # Step 7: Reconcile completed syncs
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
            tg_folders = await self.mgmt.list_folders()

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
                    tg_channels = await self.mgmt.import_folder_channels(peer_ids)
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
            await session.rollback()  # Ensure partial writes don't silently persist

    async def _queue_new_channels(self, session):
        """
        Detect channels without sync_state and queue metadata scans ONLY.
        Batch tasks are queued in _queue_batch_tasks_for_metadata after metadata completes.
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
                # Check if stuck in metadata phase for >2 minutes (metadata task lost)
                if channel.sync_state and channel.sync_state.phase == "metadata":
                    if channel.sync_state.started_at:
                        stuck_time = datetime.now(timezone.utc) - channel.sync_state.started_at
                        if stuck_time < timedelta(minutes=2):
                            continue  # Still processing, skip
                    # Re-queue metadata for stuck channels.
                    # Commit the delete first so the subsequent INSERT doesn't
                    # race against a non-deferrable unique constraint on channel_id.
                    await session.delete(channel.sync_state)
                    await session.commit()
                    channel.sync_state = None

                # Skip if in other in-progress phases
                if channel.sync_state and channel.sync_state.phase in ["syncing", "reconciling"]:
                    continue

                # Skip if completed recently (within 7 days)
                if channel.sync_state and channel.sync_state.phase == "complete":
                    if channel.sync_state.completed_at:
                        age = datetime.now(timezone.utc) - channel.sync_state.completed_at
                        if age < timedelta(days=7):
                            continue

                try:
                    # Create new sync state in metadata phase
                    sync_state = ChannelSyncState(
                        channel_id=channel.id,
                        phase="metadata",
                        started_at=datetime.now(timezone.utc)
                    )
                    session.add(sync_state)
                    # Commit BEFORE enqueueing so the Celery task always finds the row.
                    await session.commit()

                    # Queue ONLY metadata scan task — batch tasks queued later.
                    logger.info("queuing_metadata_scan", channel=channel.title)
                    try:
                        scan_channel_metadata.apply_async(
                            args=[channel.telegram_id, str(sync_state.id)],
                            kwargs={"db_name": self.db_name},
                            task_id=f"metadata_{sync_state.id}",
                            queue="connectors",
                            priority=9  # HIGH priority - metadata must complete before batches
                        )
                        queued_count += 1
                    except Exception as enqueue_err:
                        # Broker unavailable after commit — clean up the orphaned row
                        # so the next orchestrator cycle can retry instead of waiting
                        # for the 2-minute stuck-metadata timeout.
                        logger.error(
                            "enqueue_metadata_failed_cleaning_up",
                            channel=channel.title,
                            sync_state_id=str(sync_state.id),
                            error=str(enqueue_err)
                        )
                        try:
                            from sqlalchemy import delete as _sa_delete
                            # Reuse the already-open session; commit required because
                            # the previous commit (for the sync_state insert) already
                            # closed the prior transaction — we need a new one here.
                            await session.execute(
                                _sa_delete(ChannelSyncState).where(
                                    ChannelSyncState.id == sync_state.id
                                )
                            )
                            await session.commit()
                        except Exception as cleanup_err:
                            logger.error(
                                "sync_state_cleanup_failed",
                                sync_state_id=str(sync_state.id),
                                error=str(cleanup_err)
                            )
                            await session.rollback()

                except Exception as e:
                    logger.error(
                        "queue_channel_error",
                        channel=channel.title,
                        error=str(e)
                    )

            # Each channel commits individually inside the loop above (commit-before-enqueue pattern)

            logger.info("queue_new_channels_complete", queued=queued_count)

        except Exception as e:
            logger.error("queue_new_channels_error", error=str(e))

    async def _queue_batch_tasks_for_metadata(self, session):
        """
        Check for completed metadata scans and queue batch tasks.
        This ensures batches are only queued AFTER metadata completes.
        """
        from sqlalchemy.orm import joinedload
        logger.info("queue_batch_tasks_for_metadata_start")

        try:
            # Find sync states with completed metadata (phase="syncing" + estimated_total_messages set)
            result = await session.execute(
                select(ChannelSyncState)
                .options(joinedload(ChannelSyncState.channel))
                .where(
                    and_(
                        ChannelSyncState.phase == "syncing",
                        ChannelSyncState.estimated_total_messages > 0
                    )
                )
            )
            ready_syncs = result.unique().scalars().all()

            queued_count = 0

            for sync_state in ready_syncs:
                try:
                    # Check if batches already queued for this sync
                    batch_result = await session.execute(
                        select(func.count(SyncBatchLog.id)).where(
                            SyncBatchLog.sync_state_id == sync_state.id
                        )
                    )
                    batch_count_in_db = batch_result.scalar() or 0

                    if batch_count_in_db > 0:
                        # Batches already queued for this sync
                        continue

                    # Calculate batches needed based on estimated total
                    channel = sync_state.channel
                    batch_count = (sync_state.estimated_total_messages + BATCH_SIZE - 1) // BATCH_SIZE

                    logger.info(
                        "queueing_batch_tasks",
                        channel=channel.title if channel else "Unknown",
                        sync_state=sync_state.id,
                        batch_count=batch_count
                    )

                    # Queue batch tasks — capped per cycle to prevent queue flooding
                    dispatched = 0
                    for batch_num in range(min(batch_count, MAX_BATCHES_PER_CYCLE)):
                        offset = batch_num * BATCH_SIZE
                        try:
                            sync_channel_batch.apply_async(
                                kwargs={
                                    "channel_id": channel.telegram_id,
                                    "sync_state_id": str(sync_state.id),
                                    "batch_number": batch_num,
                                    "offset": offset,
                                    "limit": BATCH_SIZE,
                                    "db_name": self.db_name
                                },
                                countdown=batch_num * 1,  # 1s delay per batch
                                queue="connectors",
                                priority=0  # LOW priority - only after metadata completes
                            )
                            dispatched += 1
                        except Exception as enqueue_err:
                            logger.error(
                                "batch_task_enqueue_failed",
                                sync_state=sync_state.id,
                                batch_num=batch_num,
                                error=str(enqueue_err)
                            )
                            break  # Stop queueing on broker failure

                    queued_count += dispatched

                except Exception as e:
                    logger.error(
                        "queue_batches_error",
                        sync_state=sync_state.id,
                        error=str(e)
                    )

            if queued_count > 0:
                await session.commit()

            logger.info("queue_batch_tasks_for_metadata_complete", queued_batches=queued_count)

        except Exception as e:
            logger.error("queue_batch_tasks_for_metadata_error", error=str(e))

    async def _update_active_syncs(self, session):
        """
        Monitor active syncs and update progress/ETA.
        Calculate sync rate and estimate remaining time.
        """
        logger.info("update_active_syncs_start")

        try:
            active_syncs = await self.sync_repo.get_active_syncs()

            for sync_state in active_syncs:
                await self.sync_repo.update_eta(sync_state)

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
            failed_batches = await self.sync_repo.get_failed_batches(limit=MAX_RETRIES_PER_CYCLE)

            for batch in failed_batches:
                try:
                    batch.retry_attempt += 1
                    # Keep status as "failed" — the new task execution will create its own log

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
                            # Use the fixed BATCH_SIZE, not messages_in_batch (which
                            # records how many were *saved*, not how many were requested).
                            "limit": BATCH_SIZE,
                            "db_name": self.db_name
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
                pending_batches = await self.sync_repo.get_pending_batches(sync_state.id)

                # If no pending batches trigger reconciliation
                if not pending_batches:
                    # Also ensure at least one batch exists so we don't reconcile
                    # a sync that hasn't even queued its batches yet.
                    total_batch_result = await session.execute(
                        select(func.count(SyncBatchLog.id)).where(
                            SyncBatchLog.sync_state_id == sync_state.id
                        )
                    )
                    if (total_batch_result.scalar() or 0) > 0:
                        logger.info("triggering_reconciliation", sync_state=sync_state.id)

                        sync_state.phase = "reconciling"
                        await session.commit()

                        # Queue reconciliation task; roll back phase on broker failure.
                        try:
                            reconcile_channel_sync.apply_async(
                                args=[str(sync_state.id)],
                                kwargs={"db_name": self.db_name}
                            )
                        except Exception as enqueue_err:
                            logger.error(
                                "reconcile_enqueue_failed",
                                sync_state=sync_state.id,
                                error=str(enqueue_err)
                            )
                            # Revert phase so the next cycle can retry.
                            sync_state.phase = "syncing"
                            await session.commit()

            logger.info("reconcile_completed_syncs_complete")

        except Exception as e:
            logger.error("reconcile_completed_syncs_error", error=str(e))


from src.pipeline.base_task import AsyncDBTask

@celery_app.task(name="sync_orchestrator", bind=True, base=AsyncDBTask)
def sync_orchestrator_task(self):
    """
    Celery task - runs every 5 minutes via beat scheduler.
    Uses run_async (fresh loop per execution) to avoid RuntimeError when
    asyncio.run() is called inside an already-running loop.
    """
    orchestrator = SyncOrchestrator()
    return self.run_async(orchestrator.run())


# For direct testing
async def run_orchestrator():
    """Run orchestrator once (for testing)."""
    orchestrator = SyncOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(run_orchestrator())
