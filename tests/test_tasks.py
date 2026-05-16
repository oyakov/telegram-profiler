"""Tests for high-level Celery tasks (orchestrate, sync_telegram).

Tasks use AsyncDBTask.run_async() — we patch the async functions they
call so no real DB or broker is required.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ── orchestrate_multi_db_sync ────────────────────────────────────────────────

def test_orchestrate_multi_db_sync_calls_each_db():
    """orchestrate_multi_db_sync should call PipelineService.orchestrate_sync for each DB."""
    from src.pipeline.tasks import orchestrate_multi_db_sync

    mock_svc = AsyncMock()
    mock_svc.orchestrate_sync = AsyncMock(return_value={"status": "ok"})

    # list_tenant_databases is imported locally inside _do(), so patch at source module.
    with patch("src.db.database.list_tenant_databases", AsyncMock(return_value=["crm_test1", "crm_test2"])), \
         patch("src.pipeline.tasks.PipelineService", return_value=mock_svc):
        result = orchestrate_multi_db_sync.apply().get()

    assert result["status"] == "dispatched"
    assert mock_svc.orchestrate_sync.await_count == 2


# ── sync_telegram ────────────────────────────────────────────────────────────

def test_sync_telegram_task_delegates_to_pipeline():
    """sync_telegram should delegate to PipelineService.run_recent_sync."""
    from src.pipeline.tasks import sync_telegram

    mock_svc = AsyncMock()
    mock_svc.run_recent_sync = AsyncMock(return_value={"synced": 5})

    with patch("src.pipeline.tasks.PipelineService", return_value=mock_svc):
        result = sync_telegram.apply(kwargs={"db_name": "crm_test"}).get()

    assert result == {"synced": 5}
    mock_svc.run_recent_sync.assert_awaited_once()
