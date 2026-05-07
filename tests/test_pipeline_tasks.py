import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.pipeline.tasks import (
    sync_telegram, deep_sync_telegram, enrich_contact_task,
    orchestrate_multi_db_sync, orchestrate_multi_db_message_processing,
    _run_async
)
import asyncio
from datetime import datetime

from dataclasses import dataclass, asdict

@dataclass
class MockSyncResult:
    status: str = "success"

def test_run_async_utility():
    async def sample_coro():
        return "success"
    result = _run_async(sample_coro())
    assert result == "success"

def test_sync_telegram_task():
    with patch("src.connectors.telegram_connector.TelegramConnector") as mock_connector_cls, \
         patch("src.pipeline.tasks.process_unified_messages.delay") as mock_process:
        
        mock_connector = mock_connector_cls.return_value
        mock_connector.sync = AsyncMock(return_value=MockSyncResult(status="success"))
        
        result = sync_telegram(db_name="crm_test")
        assert result["status"] == "success"
        mock_connector_cls.assert_called_once()
        mock_process.assert_called_once_with(db_name="crm_test")

def test_deep_sync_telegram_task():
    with patch("src.connectors.telegram_connector.TelegramConnector") as mock_connector_cls, \
         patch("src.pipeline.tasks.process_unified_messages.delay") as mock_process:
        
        mock_connector = mock_connector_cls.return_value
        mock_connector.deep_sync = AsyncMock(return_value=MockSyncResult(status="success"))
        
        result = deep_sync_telegram(chat_ids=["123"], db_name="crm_test")
        assert result["status"] == "success"
        mock_process.assert_called_once()

def test_enrich_contact_task():
    with patch("src.connectors.telegram_connector.TelegramConnector") as mock_connector_cls:
        mock_connector = mock_connector_cls.return_value
        mock_connector.enrich_contact = AsyncMock(return_value=True)
        
        result = enrich_contact_task(contact_id="123", db_name="crm_test")
        assert result["status"] == "success"

def test_orchestrate_multi_db_sync():
    def mock_run_async(coro):
        coro.close()
        return {"status": "dispatched", "databases": ["crm_db1", "crm_db2"]}

    with patch("src.pipeline.tasks._run_async", side_effect=mock_run_async), \
         patch("src.pipeline.tasks.sync_telegram.delay") as mock_sync:
        
        result = orchestrate_multi_db_sync()
        assert result["status"] == "dispatched"
        assert "crm_db1" in result["databases"]

def test_orchestrate_multi_db_message_processing():
    def mock_run_async(coro):
        coro.close()
        return {"status": "dispatched", "databases": ["crm_db1"]}

    with patch("src.pipeline.tasks._run_async", side_effect=mock_run_async), \
         patch("src.pipeline.tasks.process_unified_messages.delay") as mock_unif, \
         patch("src.pipeline.tasks.process_message_embeddings.delay") as mock_emb:
        
        result = orchestrate_multi_db_message_processing()
        assert result["status"] == "dispatched"
        assert "crm_db1" in result["databases"]

def test_sync_telegram_skipped_auto():
    with patch("src.db.database.get_session") as mock_get_session, \
         patch("src.core.config.SettingsService") as mock_svc_cls:
        
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        mock_svc = mock_svc_cls.return_value
        mock_svc.get = AsyncMock(return_value=False) # Sync disabled
        
        result = sync_telegram(auto=True, db_name="crm_test")
        assert result["status"] == "skipped"
        assert result["reason"] == "disabled"
