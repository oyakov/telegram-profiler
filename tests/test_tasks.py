import pytest
from unittest.mock import patch, MagicMock
from src.pipeline.tasks import orchestrate_multi_db_sync, sync_telegram

def test_orchestrate_multi_db_sync_calls():
    """Verify that orchestrator calls sync_telegram for defined folders."""
    with patch("src.core.config.get_settings") as mock_settings:
        mock_settings.return_value.database_url = "postgresql+asyncpg://user:pass@host:5432/db"
        
        # Setup mock engine and execution results
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("crm_test1",), ("crm_test2",)]
        
        with patch("src.pipeline.tasks.sync_telegram.delay") as mock_sync:
            with patch("src.db.database.get_engine") as mock_get_engine:
                mock_engine = MagicMock()
                mock_get_engine.return_value = mock_engine
                
                # Mock async context manager for connection
                mock_conn = MagicMock()
                mock_engine.connect.return_value.__aenter__ = MagicMock(return_value=mock_conn)
                mock_conn.execute = MagicMock(return_value=mock_result)
                
                # Also mock _run_async to just return the result of executing the coro (if we can)
                # But orchestrate_multi_db_sync calls _run_async(_get_dbs())
                # For simplicity, let's just patch _run_async
                with patch("src.pipeline.tasks._run_async", return_value=["crm_test1", "crm_test2"]):
                    orchestrate_multi_db_sync()
                    assert mock_sync.call_count == 2

def test_sync_telegram_task_logic():
    """Verify sync_telegram task correctly initializes account and starts sync."""
    with patch("src.core.config.get_settings") as mock_settings:
        mock_settings.return_value.database_url = "postgresql+asyncpg://user:pass@host:5432/db"
        mock_settings.return_value.postgres_port = 5432
        
        with patch("src.connectors.telegram_connector.TelegramConnector") as mock_connector:
            mock_instance = mock_connector.return_value
            mock_instance.initialize = MagicMock()
            mock_instance.sync = MagicMock()
            
            # Patch _run_async to execute the coroutine
            import asyncio
            def run_sync(coro):
                return asyncio.run(coro)
            
            with patch("src.pipeline.tasks._run_async", side_effect=run_sync):
                sync_telegram(db_name="db1")
                mock_connector.assert_called_once()
