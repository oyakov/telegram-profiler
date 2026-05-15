import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.pipeline.tasks import orchestrate_multi_db_sync, sync_telegram


def test_orchestrate_multi_db_sync_calls():
    """orchestrate_multi_db_sync should call PipelineService.orchestrate_sync for each DB."""
    mock_service = AsyncMock()
    mock_service.orchestrate_sync = AsyncMock(return_value={"status": "ok"})

    with patch("src.db.database.list_tenant_databases", AsyncMock(return_value=["crm_test1", "crm_test2"])), \
         patch("src.pipeline.tasks.PipelineService", return_value=mock_service):
        orchestrate_multi_db_sync.apply()
        assert mock_service.orchestrate_sync.call_count == 2


def test_sync_telegram_task_logic():
    """sync_telegram should delegate to PipelineService.run_recent_sync."""
    mock_service = AsyncMock()
    mock_service.run_recent_sync = AsyncMock(return_value={"synced": 5})

    with patch("src.pipeline.tasks.PipelineService", return_value=mock_service):
        sync_telegram.apply(kwargs={"db_name": "crm_test"})
        mock_service.run_recent_sync.assert_awaited_once()
