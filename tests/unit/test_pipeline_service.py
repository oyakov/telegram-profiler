"""Unit tests for PipelineService — orchestration and sync management."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.pipeline_service import PipelineService


@pytest.fixture
def mock_deps():
    """Mock all services that PipelineService depends on."""
    with patch("src.services.pipeline_service.TelegramClientFactory") as mock_factory, \
         patch("src.services.pipeline_service.TelegramAuthService") as mock_auth_cls, \
         patch("src.services.pipeline_service.TelegramSyncService") as mock_sync_cls, \
         patch("src.services.pipeline_service.TelegramEntityService") as mock_entity_cls:
        
        mock_auth = mock_auth_cls.return_value
        mock_sync = mock_sync_cls.return_value
        mock_entity = mock_entity_cls.return_value
        
        yield {
            "factory": mock_factory,
            "auth": mock_auth,
            "sync": mock_sync,
            "entity": mock_entity
        }


@pytest.mark.asyncio
async def test_run_recent_sync_not_authorized(mock_deps):
    mock_deps["auth"].is_authorized = AsyncMock(return_value=False)
    svc = PipelineService(db_name="test_db")
    
    result = await svc.run_recent_sync()
    
    assert result["status"] == "skipped"
    assert result["reason"] == "not_authorized"
    mock_deps["sync"].sync_recent.assert_not_called()


@pytest.mark.asyncio
async def test_run_recent_sync_authorized(mock_deps):
    mock_deps["auth"].is_authorized = AsyncMock(return_value=True)
    mock_deps["sync"].sync_recent = AsyncMock(return_value={"status": "success", "fetched": 42})
    svc = PipelineService(db_name="test_db")
    
    result = await svc.run_recent_sync()
    
    assert result["status"] == "success"
    assert result["fetched"] == 42
    mock_deps["sync"].sync_recent.assert_called_once()


@pytest.mark.asyncio
async def test_run_historical_sync_authorized(mock_deps):
    mock_deps["auth"].is_authorized = AsyncMock(return_value=True)
    mock_deps["sync"].sync_historical = AsyncMock(return_value=10)
    svc = PipelineService(db_name="test_db")
    
    result = await svc.run_historical_sync(chat_ids=["123", 456], limit=100)
    
    assert result["status"] == "success"
    assert result["fetched"] == 20 # 10 + 10
    assert mock_deps["sync"].sync_historical.call_count == 2


@pytest.mark.asyncio
async def test_orchestrate_message_processing(mock_deps):
    with patch("src.pipeline.tasks.process_unified_messages.delay") as mock_proc, \
         patch("src.pipeline.tasks.process_message_embeddings.delay") as mock_embed, \
         patch("src.pipeline.tasks.reindex_dirty_contacts.delay") as mock_reindex:
        
        svc = PipelineService(db_name="test_db")
        result = await svc.orchestrate_message_processing()
        
        assert result["status"] == "dispatched"
        assert result["db_name"] == "test_db"
        mock_proc.assert_called_once_with(limit=100, db_name="test_db")
        mock_embed.assert_called_once_with(batch_size=100, db_name="test_db")
        mock_reindex.assert_called_once_with(batch_size=50, db_name="test_db")


@pytest.mark.asyncio
async def test_orchestrate_sync(mock_deps):
    with patch("src.pipeline.tasks.sync_telegram.delay") as mock_sync_task:
        svc = PipelineService(db_name="test_db")
        result = await svc.orchestrate_sync()
        
        assert result["status"] == "dispatched"
        mock_sync_task.assert_called_once_with(db_name="test_db")
