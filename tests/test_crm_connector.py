import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from src.connectors.crm_connector import CRMConnector
from src.connectors.base import SyncResult

@pytest.mark.asyncio
async def test_crm_connector_init():
    with patch("os.getenv", return_value="test_db"):
        conn = CRMConnector()
        assert conn.db_name == "test_db"
    
    conn = CRMConnector(db_name="specific_db")
    assert conn.db_name == "specific_db"

@pytest.mark.asyncio
async def test_crm_sync_no_url():
    conn = CRMConnector(db_name="test_db")
    with patch("src.connectors.crm_connector.get_session") as mock_session:
        # Mock SettingsService to return empty URL
        with patch("src.connectors.crm_connector.SettingsService") as mock_svc:
            mock_svc.return_value.get = AsyncMock(return_value="")
            
            result = await conn.sync()
            assert result.status == "error"
            assert "CRM API URL not configured" in result.errors

@pytest.mark.asyncio
async def test_crm_sync_success():
    conn = CRMConnector(db_name="test_db")
    
    mock_data = {
        "contacts": [
            {"email": "test@example.com", "first_name": "Test", "last_name": "User"}
        ]
    }
    
    with patch("src.connectors.crm_connector.get_session") as mock_session:
        mock_session_inst = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_inst
        
        with patch("src.connectors.crm_connector.SettingsService") as mock_svc:
            mock_svc.return_value.get = AsyncMock(side_effect=lambda k, d: "http://api.com" if k=="crm_api_url" else "secret")
            
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.raise_for_status = MagicMock()
                mock_resp.json = MagicMock(return_value=mock_data)
                mock_get.return_value = mock_resp
                
                # Mock _upsert_contact and _get_or_create_state
                with patch.object(CRMConnector, "_upsert_contact", new_callable=AsyncMock) as mock_upsert:
                    with patch.object(CRMConnector, "_get_or_create_state", new_callable=AsyncMock) as mock_state:
                        result = await conn.sync()
                        
                        assert result.status == "success"
                        assert result.contacts_created == 1
                        mock_upsert.assert_called_once()
                        mock_state.assert_called_once()

@pytest.mark.asyncio
async def test_crm_test_connection():
    conn = CRMConnector(db_name="test_db")
    with patch("src.connectors.crm_connector.get_session") as mock_session:
        with patch("src.connectors.crm_connector.SettingsService") as mock_svc:
            mock_svc.return_value.get = AsyncMock(return_value="http://api.com")
            
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_get.return_value.status_code = 200
                res = await conn.test_connection()
                assert res is True
                
                mock_get.return_value.status_code = 500
                res = await conn.test_connection()
                assert res is False
