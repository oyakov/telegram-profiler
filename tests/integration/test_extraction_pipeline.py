import pytest
from src.pipeline.unified_processor import MessageProcessor
from src.db.models import Message, Contact, ExtractionLog
from src.ai.schemas import ContactExtraction, LeadExtraction
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_message_processing_pipeline(db_session):
    # Message requires a contact_id, so create one first
    contact = Contact(first_name="Ghost", telegram_username="ghost_user")
    db_session.add(contact)
    await db_session.flush()

    # Setup test message
    msg = Message(
        content="I am looking for a flat in Belgrade. Contact me at oleg@example.com",
        source="telegram",
        group_name="Belgrade Real Estate",
        raw_json={"is_channel": True},
        contact_id=contact.id,
        timestamp=pytest.importorskip("datetime").datetime.now(pytest.importorskip("datetime").timezone.utc)
    )
    db_session.add(msg)
    await db_session.commit()
    
    processor = MessageProcessor(db_session)
    
    # Mock AI Service
    mock_contacts = [
        ContactExtraction(
            first_name="Oleg",
            email="oleg@example.com",
            confidence=0.9,
            facts=["Looking for a flat"]
        )
    ]
    mock_leads = [
        LeadExtraction(
            username="ghost_user",
            content_summary="Wants to buy a flat in Belgrade",
            category="RealEstate",
            lead_type="Consumer",
            evidence_quote="I am looking for a flat in Belgrade",
            confidence=0.85
        )
    ]
    
    with patch.object(processor.ai_service, 'extract', AsyncMock()) as mock_extract:
        # (Assuming the mock settings in conftest.py use 'crm_test')
        from src.core.config import get_settings
        settings = get_settings()
        # Mocking twice: once for contacts, once for leads
        mock_extract.side_effect = [
            (mock_contacts, "usage_info"),
            (mock_leads, "usage_info")
        ]
        
        stats = await processor.process_batch([msg])
        
        assert stats["processed"] == 1
        assert stats["contacts_found"] == 1
        assert stats["leads_found"] == 1
        
        # Verify persistence
        # 1. Contact created
        result = await db_session.execute(
            pytest.importorskip("sqlalchemy").select(Contact).where(Contact.email == "oleg@example.com")
        )
        contact = result.scalar_one()
        assert contact.first_name == "Oleg"
        
        # 2. Extraction log created
        result = await db_session.execute(
            pytest.importorskip("sqlalchemy").select(ExtractionLog).where(ExtractionLog.source_id == str(msg.id))
        )
        log = result.scalar_one()
        assert log.success is True
        assert "contacts" in log.extracted_data
