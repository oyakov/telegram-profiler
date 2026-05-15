"""Unit tests for TelegramConnector."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from src.connectors.telegram_connector import TelegramConnector

@pytest.fixture
def mock_client():
    client = AsyncMock()
    # Mock context manager
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client

@pytest.fixture
def connector():
    return TelegramConnector(db_name="test_db")

@pytest.mark.asyncio
async def test_telegram_is_authorized(connector, mock_client):
    with patch.object(connector, "_get_client", return_value=mock_client):
        mock_client.is_user_authorized.return_value = True
        authorized = await connector.is_authorized()
        assert authorized is True
        mock_client.is_user_authorized.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_send_code_request(connector, mock_client):
    with patch.object(connector, "_get_client", return_value=mock_client):
        mock_res = MagicMock()
        mock_res.phone_code_hash = "hash_123"
        mock_client.send_code_request.return_value = mock_res
        
        result = await connector.send_code_request("+1234567890")
        assert result == "hash_123"
        mock_client.send_code_request.assert_called_with("+1234567890")

@pytest.mark.asyncio
async def test_telegram_sign_in_success(connector, mock_client):
    with patch.object(connector, "_get_client", return_value=mock_client):
        mock_client.sign_in.return_value = None
        result = await connector.sign_in("+1234567890", "12345", "hash_123")
        assert result["status"] == "success"

@pytest.mark.asyncio
async def test_telegram_sign_in_2fa_needed(connector, mock_client):
    from telethon.errors import SessionPasswordNeededError
    with patch.object(connector, "_get_client", return_value=mock_client):
        mock_client.sign_in.side_effect = SessionPasswordNeededError(MagicMock())
        result = await connector.sign_in("+1234567890", "12345", "hash_123")
        assert result["status"] == "requires_2fa"

@pytest.mark.asyncio
async def test_telegram_logout(connector, mock_client):
    with patch.object(connector, "_get_client", return_value=mock_client):
        await connector.logout()
        mock_client.log_out.assert_called_once()

@pytest.mark.asyncio
async def test_telegram_test_connection(connector, mock_client):
    with patch.object(connector, "_get_client", return_value=mock_client):
        mock_client.get_me.return_value = MagicMock()
        assert await connector.test_connection() is True
        
        mock_client.get_me.side_effect = Exception("failed")
        assert await connector.test_connection() is False

@pytest.mark.asyncio
async def test_telegram_sync_basic(connector, mock_client):
    # Mock database session
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    
    # Mock tracked channels
    mock_res = MagicMock()
    mock_res.all.return_value = [("123",)]
    mock_session.execute.return_value = mock_res
    
    # Mock sync state
    mock_state = MagicMock()
    mock_state.status = "idle"
    mock_state.metadata_json = {}
    
    with patch.object(connector, "_get_client", return_value=mock_client), \
         patch("src.connectors.telegram_connector.get_session", return_value=mock_session), \
         patch.object(connector, "_get_sync_state", return_value=mock_state), \
         patch.object(connector, "_sync_chat", return_value=5) as mock_sync_chat:
        
        mock_client.is_user_authorized.return_value = True
        
        result = await connector.sync(limit=10)
        
        assert result.status == "success"
        assert result.messages_fetched == 5
        mock_sync_chat.assert_called_once()
        assert mock_state.status == "idle"

@pytest.mark.asyncio
async def test_sync_chat_logic(connector, mock_client):
    mock_session = AsyncMock()
    mock_session.add = MagicMock() # session.add is synchronous
    mock_entity = MagicMock()
    mock_entity.id = 123
    
    # Mock messages
    mock_msg = MagicMock()
    mock_msg.id = 456
    mock_msg.text = "Hello world"
    mock_msg.date = datetime.now(timezone.utc)
    mock_msg.out = False
    mock_msg.sender = MagicMock()
    mock_msg.sender.id = 789
    
    # Mock client.iter_messages to return our mock message
    async def mock_iter(*args, **kwargs):
        yield mock_msg
    
    mock_client.get_entity.return_value = mock_entity
    mock_client.iter_messages = mock_iter
    
    # Mock _get_or_create_contact
    mock_contact = MagicMock()
    mock_contact.id = "contact_789"
    
    # Mock session execute results for the "existing message" check
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res
    
    with patch.object(connector, "_get_or_create_contact", return_value=mock_contact):
        count = await connector._sync_chat(mock_client, mock_session, 123, 10, None)
        assert count == 1
        # Check that session.add was called for message and MessageContact
        assert mock_session.add.call_count >= 2

@pytest.mark.skip(reason="search_communities not yet implemented")
@pytest.mark.asyncio
async def test_telegram_search_communities(connector, mock_client):
    pass


@pytest.mark.skip(reason="join_community not yet implemented")
@pytest.mark.asyncio
async def test_telegram_join_community(connector, mock_client):
    pass


@pytest.mark.asyncio
async def test_telegram_deep_sync(connector, mock_client):
    # Tests the existing sync() method with explicit chat_ids
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_state = MagicMock()
    mock_state.status = "idle"
    mock_state.metadata_json = {}

    with patch.object(connector, "_get_client", return_value=mock_client), \
         patch("src.connectors.telegram_connector.get_session", return_value=mock_session), \
         patch.object(connector, "_get_sync_state", return_value=mock_state), \
         patch.object(connector, "_sync_chat", return_value=10) as mock_sync_chat:

        mock_client.is_user_authorized.return_value = True
        result = await connector.sync(chat_ids=[123], limit=100)
        assert result.messages_fetched == 10
        mock_sync_chat.assert_called_once()


@pytest.mark.skip(reason="reorganize_all_tracked not yet implemented")
@pytest.mark.asyncio
async def test_telegram_reorganize_all_tracked(connector, mock_client):
    pass


@pytest.mark.asyncio
async def test_telegram_enrich_contact(connector, mock_client):
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.add = MagicMock()
    
    # Mock contact
    mock_contact = MagicMock()
    mock_contact.telegram_id = "111"
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_contact
    mock_session.execute.return_value = mock_res
    
    with patch.object(connector, "_get_client", return_value=mock_client), \
         patch("src.connectors.telegram_connector.get_session", return_value=mock_session):
        
        # Mock client methods for enrichment
        mock_client.get_entity = AsyncMock(return_value=MagicMock(id=111, first_name="Test", last_name="User", username="testuser"))
        
        # Mock GetFullUserRequest response
        mock_full_user = MagicMock()
        mock_full_user.full_user.about = "Test Bio"
        mock_client.side_effect = lambda req: mock_full_user
        
        # Mock _download_photo
        with patch.object(connector, "_download_photo", return_value="path/to/photo.jpg"):
            success = await connector.enrich_contact("contact_id")
            assert success is True
            assert mock_contact.bio == "Test Bio"
            assert mock_contact.profile_photo_path == "path/to/photo.jpg"

@pytest.mark.asyncio
async def test_telegram_get_status(connector):
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    
    # Mock sync state
    mock_state = MagicMock()
    mock_state.status = "idle"
    mock_state.last_sync_at = datetime.now(timezone.utc)
    mock_state.error_message = None
    mock_state.metadata_json = {"messages_fetched": 100}
    
    with patch("src.connectors.telegram_connector.get_session", return_value=mock_session), \
         patch.object(connector, "_get_sync_state", return_value=mock_state):
        
        status = await connector.get_status()
        assert status["status"] == "idle"
        assert status["messages_fetched"] == 100
