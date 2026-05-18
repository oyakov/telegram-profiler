"""Unit tests for Celery app configuration — queue routing correctness."""

from __future__ import annotations

import pytest


class TestCeleryRouting:
    """Validate that every task is routed to the appropriate queue."""

    def setup_method(self):
        from src.pipeline.celery_app import celery_app
        self.routes = celery_app.conf.task_routes

    def test_sync_orchestrator_routes_to_connectors_queue(self):
        """sync_orchestrator issues Telegram API calls — must be on 'connectors', not 'processing'."""
        route = self.routes.get("sync_orchestrator", {})
        assert route.get("queue") == "connectors", (
            f"sync_orchestrator must route to 'connectors' queue, got {route.get('queue')!r}"
        )

    def test_connector_tasks_on_connectors_queue(self):
        connector_tasks = [
            "src.pipeline.tasks.sync_telegram",
            "src.pipeline.tasks.deep_sync_telegram",
            "src.pipeline.tasks.import_excel",
            "src.pipeline.tasks.load_complete_history",
            "src.pipeline.tasks.deep_track_chunk",
            "src.pipeline.tasks.deep_track_orchestrator",
            "src.pipeline.tasks.sync_telegram_contacts",
            "src.pipeline.telegram_sync_tasks.sync_channel_batch",
            "src.pipeline.telegram_sync_tasks.scan_channel_metadata",
            "src.pipeline.telegram_sync_tasks.reconcile_channel_sync",
        ]
        for task_name in connector_tasks:
            route = self.routes.get(task_name, {})
            assert route.get("queue") == "connectors", (
                f"Task {task_name!r} must be on 'connectors' queue, got {route.get('queue')!r}"
            )

    def test_processing_tasks_on_processing_queue(self):
        processing_tasks = [
            "src.pipeline.tasks.orchestrate_multi_db_sync",
            "src.pipeline.tasks.orchestrate_multi_db_message_processing",
            "src.pipeline.tasks.process_message_embeddings",
            "src.pipeline.tasks.generate_all_embeddings",
            "src.pipeline.tasks.reindex_dirty_contacts",
            "src.pipeline.tasks.purge_extraction_log",
        ]
        for task_name in processing_tasks:
            route = self.routes.get(task_name, {})
            assert route.get("queue") == "processing", (
                f"Task {task_name!r} must be on 'processing' queue, got {route.get('queue')!r}"
            )

    def test_no_ghost_tasks_in_beat_schedule(self):
        """Every task in the beat schedule must exist in the task routes or be a known task."""
        from src.pipeline.celery_app import celery_app
        beat = celery_app.conf.beat_schedule or {}
        # These are the only tasks registered; ghost tasks should have been removed in a prior fix.
        for entry_name, entry in beat.items():
            task_name = entry.get("task", "")
            assert task_name, f"Beat entry {entry_name!r} has no task name"
            # Must not reference removed tasks
            assert task_name not in (
                "src.pipeline.tasks.orchestrate_multi_db_maintenance",
                "src.pipeline.tasks.assign_orphaned_messages_to_projects",
            ), f"Ghost task {task_name!r} still in beat schedule"
