import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from src.api.main import app

@pytest.mark.asyncio
async def test_telegram_auth_status(api_client):
    with patch("src.api.routers.telegram.TelegramConnector") as mock_connector:
        # Mock class instance
        mock_instance = mock_connector.return_value
        mock_instance.is_authorized = AsyncMock(return_value=True)
        
        response = await api_client.get("/api/telegram/auth/status")
        assert response.status_code == 200
        assert response.json() == {"authorized": True}

@pytest.mark.asyncio
async def test_telegram_send_code(api_client):
    # Mock settings to have API ID/Hash
    with patch("src.api.routers.telegram.get_settings") as mock_settings:
        mock_settings.return_value.telegram_api_id = "123"
        mock_settings.return_value.telegram_api_hash = "abc"
        
        with patch("src.api.routers.telegram.TelegramConnector") as mock_connector:
            mock_instance = mock_connector.return_value
            mock_instance.send_code_request = AsyncMock(return_value="hash123")
            
            response = await api_client.post("/api/telegram/auth/send_code", json={"phone": "+1234567890"})
            assert response.status_code == 200
            assert response.json() == {"status": "success", "phone_code_hash": "hash123"}

@pytest.mark.asyncio
async def test_telegram_join_basic(api_client):
    with patch("src.api.routers.telegram.TelegramConnector") as mock_connector:
        mock_entity = MagicMock()
        mock_entity.id = 777
        mock_connector.return_value.join_community = AsyncMock(return_value=(True, mock_entity))
        
        # Mock DB operations
        with patch("src.api.routers.telegram.get_session") as mock_session:
            mock_session_inst = AsyncMock()
            mock_session_inst.add = MagicMock() # session.add is synchronous
            mock_session.return_value.__aenter__.return_value = mock_session_inst
            
            # Mock select results
            mock_res = MagicMock()
            mock_res.scalar_one_or_none.return_value = None # No folder, no channel
            mock_session_inst.execute.return_value = mock_res
            
            # Also need to mock 'select' used in the function
            with patch("src.api.routers.telegram.select") as mock_select:
                response = await api_client.post("/api/telegram/join", json={"chat_id": "test_chat", "deep_sync_days": 0})
                assert response.status_code == 200
                assert response.json()["joined_id"] == 777

@pytest.mark.asyncio
async def test_telegram_deep_sync(api_client):
    with patch("src.api.routers.telegram.deep_sync_telegram") as mock_task:
        mock_task.delay.return_value.id = "task_123"
        
        response = await api_client.post("/api/telegram/deep-sync", json={"chat_ids": ["123"], "limit": 100, "days": 7})
        assert response.status_code == 200
        assert response.json() == {"status": "queued", "task_id": "task_123"}
