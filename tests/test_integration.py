import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.pipeline.unified_processor import MessageProcessor
from src.db.models import Message
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_parallel_message_processing_concurrency():
    """Verify that MessageProcessor.process_batch runs tasks concurrently."""
    # 1. Setup mocks
    mock_session = AsyncMock()
    # Make session.execute().scalar_one_or_none() return None so SettingsService.get returns defaults
    mock_exec_result = MagicMock()
    mock_exec_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_exec_result

    # Mocking the AI service to have a slight delay to prove concurrency
    mock_ai_service = AsyncMock()
    
    async def mocked_extract(*args, **kwargs):
        await asyncio.sleep(0.1) # Simulate network latency
        return [], {} # Return empty contacts/leads for simplicity

    mock_ai_service.extract.side_effect = mocked_extract
    
    processor = MessageProcessor(mock_session)
    processor.ai_service = mock_ai_service
    
    # 2. Create a batch of messages
    messages = [
        Message(id="msg1", content="This is message 1 content that is long enough", raw_json={}, timestamp=datetime.now(timezone.utc)),
        Message(id="msg2", content="This is message 2 content that is long enough", raw_json={}, timestamp=datetime.now(timezone.utc)),
        Message(id="msg3", content="This is message 3 content that is long enough", raw_json={}, timestamp=datetime.now(timezone.utc)),
    ]
    
    # 3. Execute batch
    start_time = asyncio.get_event_loop().time()
    stats = await processor.process_batch(messages)
    end_time = asyncio.get_event_loop().time()
    
    # 4. Verify
    # If it was sequential, it would take at least 0.3s (3 messages * 0.1s)
    # Since it's parallel, it should take ~0.1s (plus overhead)
    duration = end_time - start_time
    assert duration < 0.25, f"Processing took too long ({duration}s), concurrency might not be working"
    assert stats["processed"] == 3
    assert mock_ai_service.extract.call_count == 3 # contacts extraction (leads extraction is skipped for non-channels)

@pytest.mark.asyncio
async def test_multi_db_discovery():
    """Verify that get_all_crm_databases returns list from mock."""
    with patch("asyncpg.connect") as mock_connect:
        mock_conn = mock_connect.return_value
        mock_conn.fetch.return_value = [
            {'datname': 'crm'},
            {'datname': 'crm_crypto'},
            {'datname': 'crm_bg_rent'}
        ]
        
        from scripts.migrate_all import get_all_crm_databases
        dbs = await get_all_crm_databases()
        
        assert len(dbs) == 3
        assert "crm_crypto" in dbs
        assert "crm_bg_rent" in dbs
