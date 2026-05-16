"""Celery application and configuration."""

from __future__ import annotations
from celery import Celery
from celery.schedules import crontab
from src.core.config import get_settings

settings = get_settings()
redis_url = settings.redis_url

celery_app = Celery(
    "networking_brain",
    broker=redis_url,
    backend=redis_url,
    include=[
        "src.pipeline.tasks",
        "src.pipeline.telegram_sync_tasks",
        "src.pipeline.sync_orchestrator"
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "src.pipeline.tasks.sync_telegram": {"queue": "connectors"},
        "src.pipeline.tasks.deep_sync_telegram": {"queue": "connectors"},
        "src.pipeline.tasks.import_excel": {"queue": "connectors"},
        "src.pipeline.tasks.sync_crm": {"queue": "connectors"},
        "src.pipeline.tasks.load_complete_history": {"queue": "connectors"},
        "src.pipeline.tasks.deep_track_chunk": {"queue": "connectors"},
        "src.pipeline.tasks.deep_track_orchestrator": {"queue": "connectors"},
        "src.pipeline.tasks.sync_telegram_contacts": {"queue": "connectors"},
        "src.pipeline.telegram_sync_tasks.sync_channel_batch": {"queue": "connectors"},
        "src.pipeline.telegram_sync_tasks.scan_channel_metadata": {"queue": "connectors"},
        "src.pipeline.telegram_sync_tasks.reconcile_channel_sync": {"queue": "connectors"},
        "sync_orchestrator": {"queue": "processing"},
        "src.pipeline.tasks.orchestrate_multi_db_sync": {"queue": "processing"},
        "src.pipeline.tasks.orchestrate_multi_db_message_processing": {"queue": "processing"},
        "src.pipeline.tasks.process_message_embeddings": {"queue": "processing"},
        "src.pipeline.tasks.generate_all_embeddings": {"queue": "processing"},
        "src.pipeline.tasks.reindex_dirty_contacts": {"queue": "processing"},
    },
    beat_schedule={
        "sync-orchestrator": {
            "task": "sync_orchestrator",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "multi-db-sync-orchestrator": {
            "task": "src.pipeline.tasks.orchestrate_multi_db_sync",
            "schedule": crontab(
                minute="*/30"  # Default to 30 mins, could be moved to settings if needed
            ),
        },
        "deep-track-orchestrator": {
            "task": "src.pipeline.tasks.deep_track_orchestrator",
            "schedule": crontab(minute="*/15"),
        },
        "process-messages": {
            "task": "src.pipeline.tasks.orchestrate_multi_db_message_processing",
            "schedule": crontab(minute="*"),
        },
    },
)
