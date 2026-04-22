"""Tests for lead detection and scoring logic."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy import delete, select

from src.ai.services import ExtractionService, LeadExtraction
from src.pipeline.unified_processor import update_all_lead_scores, MessageProcessor
from src.db.models import Contact, Message

@pytest.mark.asyncio
async def test_detect_leads_mock():
    """Test the lead detection logic with mocked LLM."""
    mock_data = {
        "items": [
            {
                "username": "lead123",
                "display_name": "Lead Name",
                "content_summary": "Test Product",
                "category": "Other",
                "lead_type": "Supplier",
                "confidence": 0.9,
                "evidence_quote": "Ad by @lead123",
                "lead_quality": 8
            }
        ]
    }
    
    with patch("src.ai.services.structured_extraction", new_callable=AsyncMock) as mock_ext:
        mock_ext.return_value = {"data": mock_data, "prompt_tokens": 100, "completion_tokens": 50, "processing_time_ms": 200}
        
        service = ExtractionService()
        items, _ = await service.extract("Some text with an ad", extraction_type="leads")
        
        assert len(items) == 1
        assert items[0].username == "lead123"

@pytest.mark.asyncio
async def test_sync_lead(db_session):
    """Test syncing lead data to the database."""
    # Create a dummy contact for the message sender (channel)
    channel_contact = Contact(first_name="Test Channel", telegram_id="channel_123", source="telegram")
    db_session.add(channel_contact)
    await db_session.flush()

    # Setup test message
    msg = Message(
        contact_id=channel_contact.id,
        source="telegram",
        source_message_id="test_sync_1",
        content="Ad by @test_lead_sync",
        timestamp=datetime.now(timezone.utc),
        raw_json={"is_channel": True}
    )
    db_session.add(msg)
    await db_session.flush()
    
    lead_data = LeadExtraction(
        username="test_lead_sync",
        display_name="Test Lead Sync",
        content_summary="Promo",
        confidence=1.0,
        evidence_quote="Ad by @test_lead_sync",
        lead_quality=5,
        category="Other",
        lead_type="Supplier"
    )
    
    processor = MessageProcessor(db_session)
    
    # Sync first time (create)
    contact = await processor._sync_lead(lead_data, msg)
    assert contact.telegram_username == "test_lead_sync"
    assert contact.is_lead is True
    
    # Sync second time (update)
    msg2 = Message(
        contact_id=channel_contact.id,
        source="telegram",
        source_message_id="test_sync_2",
        content="Another ad by @test_lead_sync",
        timestamp=datetime.now(timezone.utc)
    )
    db_session.add(msg2)
    await db_session.flush()

    contact2 = await processor._sync_lead(lead_data, msg2)
    assert contact2.id == contact.id
    assert len(contact2.lead_context["lead_history"]) >= 2
    
    # Cleanup
    await db_session.execute(delete(Contact).where(Contact.telegram_id == "channel_123"))
    await db_session.execute(delete(Contact).where(Contact.telegram_username == "test_lead_sync"))
    await db_session.commit()

@pytest.mark.asyncio
async def test_lead_scoring(db_session):
    """Test lead scoring calculation."""
    now = datetime.now(timezone.utc)
    
    # Ensure no existing contact with this username
    await db_session.execute(delete(Contact).where(Contact.telegram_username == "scored_lead"))
    await db_session.commit()

    contact = Contact(
        first_name="Scored Lead",
        telegram_username="scored_lead",
        is_lead=True,
        lead_context={
            "lead_history": [
                {"timestamp": (now - timedelta(days=5)).isoformat(), "quality": 5}, # Recent (3 pts base)
                {"timestamp": (now - timedelta(days=40)).isoformat(), "quality": 5}, # Old (1 pt base)
            ]
        },
        source="telegram"
    )
    db_session.add(contact)
    await db_session.commit()
    
    await update_all_lead_scores()
    
    # Force refresh by expiring session
    db_session.expire_all()
    
    # Refresh from db
    res = await db_session.execute(select(Contact).where(Contact.telegram_username == "scored_lead"))
    row = res.scalar_one_or_none()
    assert row is not None
    assert float(row.lead_score) == 4.0
    
    # Cleanup
    await db_session.execute(delete(Contact).where(Contact.telegram_username == "scored_lead"))
    await db_session.commit()
