"""Unit tests for UnifiedProcessor AI extraction logic."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.pipeline.unified_processor import MessageProcessor
from src.db.models import Message, Contact
from src.ai.schemas import ContactExtraction, LeadExtraction

@pytest.fixture
def processor():
    session = AsyncMock()
    # Mock settings_svc to return default values and avoid DB/coroutine issues
    p = MessageProcessor(session, db_name="test_db")
    p.settings_svc = AsyncMock()
    p.settings_svc.get.return_value = 0.6
    return p

@pytest.mark.asyncio
async def test_message_length_filtering(processor):
    """Messages with < 10 characters should be skipped."""
    msg_short = Message(id=1, content="Hi", group_name="Test")
    msg_long = Message(id=2, content="Hello world, this is a long message for extraction.", group_name="Test")
    
    with patch.object(processor.ai_service, "extract", AsyncMock(return_value=([], []))):
        stats = await processor.process_batch([msg_short, msg_long])
        
    assert stats["processed"] == 1

@pytest.mark.asyncio
async def test_lead_threshold_enforcement(processor):
    """Leads below the confidence threshold should be ignored."""
    msg = Message(id=1, content="Looking for python developer in Belgrade.", group_name="Test")
    
    # Mock settings_svc.get to return 0.6
    processor.settings_svc.get.return_value = 0.6
    
    # Mock AI to return a lead with 0.4 confidence
    low_conf_lead = LeadExtraction(
        username="user1", 
        display_name="User One",
        content_summary="Looking for dev",
        category="job_search",
        lead_type="Consumer",
        evidence_quote="Looking for...",
        lead_quality=5,
        confidence=0.4
    )
    
    with patch.object(processor.ai_service, "extract", AsyncMock(side_effect=[([], []), ([low_conf_lead], [])])):
        stats = await processor.process_batch([msg])
        
    assert stats["leads_found"] == 0
    assert stats["processed"] == 1

@pytest.mark.asyncio
async def test_llm_failure_isolation(processor):
    """If one message fails, others in the batch should still be processed."""
    msg1 = Message(id=1, content="Message one for extraction.", group_name="Test")
    msg2 = Message(id=2, content="Message two for extraction.", group_name="Test")
    
    # Mock AI to fail for msg1 and succeed for msg2
    processor.ai_service.extract = AsyncMock(side_effect=[
        Exception("LLM Timeout"),
        ([], [])
    ])
    
    stats = await processor.process_batch([msg1, msg2])
    
    assert stats["errors"] == 1
    assert stats["processed"] == 1 # Only msg2 succeeded

@pytest.mark.asyncio
async def test_is_extracted_flag(processor):
    """Messages should be marked as is_extracted only on success."""
    msg = Message(id=1, content="Valid message content here.", group_name="Test", is_extracted=False)
    
    with patch.object(processor.ai_service, "extract", AsyncMock(return_value=([], []))):
        await processor.process_batch([msg])
        
    assert msg.is_extracted is True
