"""Unit tests for resilience and retry logic in Telegram services."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from telethon.errors import RPCError
from telethon.tl.types import Channel
from src.services.telegram.sync_service import TelegramSyncService

# Mock RPCError since it needs a message in __init__
class MockRPCError(RPCError):
    def __init__(self, message="Test error"):
        super().__init__(400, message)

class AsyncIter:
    def __init__(self, items):
        self.items = items
    def __aiter__(self):
        return self
    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)

@pytest.fixture
def mock_factory():
    factory = AsyncMock()
    client = MagicMock() # Use MagicMock for client to avoid coroutine issues on non-async methods
    factory.get_client.return_value = client
    
    client.is_connected = MagicMock(return_value=True)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.get_entity = AsyncMock()
    client.iter_messages = MagicMock(return_value=AsyncIter([]))
    
    return factory, client

@pytest.fixture
def sync_service(mock_factory):
    factory, client = mock_factory
    entity_service = MagicMock()
    return TelegramSyncService(factory, entity_service), client

@pytest.mark.asyncio
async def test_retry_on_connection_error(sync_service):
    service, client = sync_service
    
    mock_entity = MagicMock(spec=Channel)
    mock_entity.id = 12345
    mock_entity.broadcast = True
    
    client.get_entity.side_effect = [
        ConnectionError("Lost connection"), 
        ConnectionError("Lost connection"), 
        mock_entity
    ]
    
    with patch("src.services.telegram.sync_service.get_session") as mock_session_ctx, \
         patch("src.services.telegram.sync_service.SyncStateRepository") as mock_repo_cls:
        
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_session
        
        mock_repo = mock_repo_cls.return_value
        mock_state = MagicMock()
        mock_state.metadata_json = {}
        mock_repo.get_or_create_connector_state = AsyncMock(return_value=mock_state)
        
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_res)

        await service.sync_historical(12345, session=mock_session)
    
    assert client.get_entity.call_count >= 3

@pytest.mark.asyncio
async def test_retry_limit_exceeded(sync_service):
    service, client = sync_service
    client.get_entity.side_effect = ConnectionError("Persistent failure")
    
    with patch("src.services.telegram.sync_service.get_session") as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_session
        
        with pytest.raises(ConnectionError, match="Persistent failure"):
            await service.sync_historical(12345, session=mock_session)
            
    assert client.get_entity.call_count >= 3

@pytest.mark.asyncio
async def test_retry_on_rpc_error(sync_service):
    service, client = sync_service
    
    mock_entity = MagicMock(spec=Channel)
    mock_entity.id = 12345
    mock_entity.broadcast = True
    
    client.get_entity.side_effect = [MockRPCError("Temp error"), mock_entity]
    
    with patch("src.services.telegram.sync_service.get_session") as mock_session_ctx, \
         patch("src.services.telegram.sync_service.SyncStateRepository") as mock_repo_cls:
        
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_session
        
        mock_repo = mock_repo_cls.return_value
        mock_state = MagicMock()
        mock_state.metadata_json = {}
        mock_repo.get_or_create_connector_state = AsyncMock(return_value=mock_state)
        
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_res)

        await service.sync_historical(12345, session=mock_session)
        
    assert client.get_entity.call_count == 2
