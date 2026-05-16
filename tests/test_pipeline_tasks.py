"""Tests for Celery pipeline tasks in src/pipeline/tasks.py.

All tasks use AsyncDBTask.run_async() — we patch the async helpers and
PipelineService so no real DB or Celery broker is required.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_pipeline_mock(**overrides):
    """Return an AsyncMock that behaves like PipelineService."""
    svc = AsyncMock()
    for attr, val in overrides.items():
        setattr(svc, attr, AsyncMock(return_value=val))
    return svc


# ── sync_telegram ─────────────────────────────────────────────────────────────

def test_sync_telegram_delegates_to_pipeline_service():
    from src.pipeline.tasks import sync_telegram

    mock_svc = _make_pipeline_mock(run_recent_sync={"synced": 3})

    with patch("src.pipeline.tasks.PipelineService", return_value=mock_svc):
        result = sync_telegram.apply(kwargs={"db_name": "crm_test"}).get()

    assert result == {"synced": 3}
    mock_svc.run_recent_sync.assert_awaited_once()


# ── deep_sync_telegram ────────────────────────────────────────────────────────

def test_deep_sync_telegram_delegates_to_pipeline_service():
    from src.pipeline.tasks import deep_sync_telegram

    mock_svc = _make_pipeline_mock(run_historical_sync={"synced": 10})

    with patch("src.pipeline.tasks.PipelineService", return_value=mock_svc):
        result = deep_sync_telegram.apply(
            kwargs={"chat_ids": ["111", "222"], "limit": 200, "db_name": "crm_test"}
        ).get()

    assert result == {"synced": 10}
    mock_svc.run_historical_sync.assert_awaited_once()


# ── enrich_contact_task ───────────────────────────────────────────────────────

def test_enrich_contact_task_success():
    from src.pipeline.tasks import enrich_contact_task

    # The class is imported locally inside _do(), so patch at the source module.
    # Use MagicMock as the class so TelegramConnector(...) returns a plain instance,
    # not a coroutine (which AsyncMock would do when called).
    mock_instance = AsyncMock()
    mock_instance.enrich_contact = AsyncMock(return_value=True)
    mock_cls = MagicMock(return_value=mock_instance)

    with patch("src.connectors.telegram_connector.TelegramConnector", mock_cls):
        result = enrich_contact_task.apply(
            kwargs={"contact_id": "abc-123", "db_name": "crm_test"}
        ).get()

    assert result["status"] == "success"


def test_enrich_contact_task_failure_reported():
    from src.pipeline.tasks import enrich_contact_task

    mock_instance = AsyncMock()
    mock_instance.enrich_contact = AsyncMock(return_value=False)
    mock_cls = MagicMock(return_value=mock_instance)

    with patch("src.connectors.telegram_connector.TelegramConnector", mock_cls):
        result = enrich_contact_task.apply(
            kwargs={"contact_id": "abc-123", "db_name": "crm_test"}
        ).get()

    assert result["status"] == "failed"


# ── orchestrate_multi_db_sync ─────────────────────────────────────────────────

def test_orchestrate_multi_db_sync_dispatches_to_all_dbs():
    from src.pipeline.tasks import orchestrate_multi_db_sync

    dbs = ["crm_db1", "crm_db2"]
    mock_svc = _make_pipeline_mock(orchestrate_sync={"status": "ok"})

    with patch("src.db.database.list_tenant_databases", AsyncMock(return_value=dbs)), \
         patch("src.pipeline.tasks.PipelineService", return_value=mock_svc):
        result = orchestrate_multi_db_sync.apply().get()

    assert result["status"] == "dispatched"
    assert result["databases"] == dbs
    assert mock_svc.orchestrate_sync.await_count == 2


# ── orchestrate_multi_db_message_processing ───────────────────────────────────

def test_orchestrate_multi_db_message_processing_dispatches_to_all_dbs():
    from src.pipeline.tasks import orchestrate_multi_db_message_processing

    dbs = ["crm_db1"]
    mock_svc = _make_pipeline_mock(orchestrate_message_processing={"status": "ok"})

    with patch("src.db.database.list_tenant_databases", AsyncMock(return_value=dbs)), \
         patch("src.pipeline.tasks.PipelineService", return_value=mock_svc):
        result = orchestrate_multi_db_message_processing.apply().get()

    assert result["status"] == "dispatched"
    assert "crm_db1" in result["databases"]
    mock_svc.orchestrate_message_processing.assert_awaited_once()


# ── process_unified_messages ──────────────────────────────────────────────────

def test_process_unified_messages_calls_processor():
    from src.pipeline.tasks import process_unified_messages

    with patch(
        "src.pipeline.unified_processor.process_unprocessed_messages",
        AsyncMock(return_value={"processed": 5}),
    ):
        result = process_unified_messages.apply(
            kwargs={"limit": 50, "db_name": "crm_test"}
        ).get()

    assert result == {"processed": 5}
