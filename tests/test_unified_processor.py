import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from src.db.models import Message, Contact, MessageEmbedding
from src.pipeline.unified_processor import (
    MessageProcessor,
    process_unprocessed_messages,
    update_all_lead_scores,
    full_reindex,
    _maintenance_reindex_dirty_impl,
    _maintenance_index_messages_impl,
    _build_contact_profile
)
from src.ai.schemas import ContactExtraction, LeadExtraction


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_sync_contact_logic(mock_session):
    processor = MessageProcessor(mock_session)

    # Case 1: New contact — find_duplicate returns None
    with patch.object(processor.contact_repo, "find_duplicate", AsyncMock(return_value=None)):
        extraction = ContactExtraction(first_name="New", last_name="Contact", email="new@example.com")
        contact = await processor._sync_contact(extraction)
        assert contact.first_name == "New"
        assert contact.email == "new@example.com"
        mock_session.add.assert_called()

    # Case 2: Duplicate contact — find_duplicate returns existing
    mock_session.add.reset_mock()
    existing_contact = Contact(id=1, first_name="Old", email="new@example.com")
    with patch.object(processor.contact_repo, "find_duplicate", AsyncMock(return_value=existing_contact)), \
         patch.object(processor.contact_repo, "merge_contact_fields", MagicMock()) as mock_merge:

        extraction = ContactExtraction(first_name="Old", email="new@example.com", phone="12345")
        contact = await processor._sync_contact(extraction)
        assert contact.id == 1
        mock_merge.assert_called_once()
        mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_sync_lead_logic(mock_session):
    processor = MessageProcessor(mock_session)
    msg = Message(id=1, timestamp=datetime.now(timezone.utc), group_id="123")

    lead_data = LeadExtraction(
        username="leaduser",
        display_name="Lead User",
        content_summary="Wants dev",
        category="Dev",
        lead_type="Direct",
        evidence_quote="Hire me",
        lead_quality=8,
        confidence=0.9
    )
    with patch.object(processor.contact_repo, "find_duplicate", AsyncMock(return_value=None)):
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)
        contact = await processor._sync_lead(lead_data, msg)
        assert contact.is_lead is True
        assert contact.telegram_username == "leaduser"


@pytest.mark.asyncio
async def test_maintenance_reindex_dirty(mock_session):
    contact = Contact(id=1, first_name="John", embedding_dirty=True)
    msg = Message(id=10, content="Some message content")

    res_contact = MagicMock()
    res_contact.scalars.return_value.all.return_value = [contact]

    res_msg = MagicMock()
    res_msg.scalars.return_value.all.return_value = [msg]

    mock_session.execute.side_effect = [res_contact, res_msg]

    with patch("src.pipeline.unified_processor.generate_embedding", return_value=[0.1] * 1024):
        stats = await _maintenance_reindex_dirty_impl(mock_session, batch_size=10)
        assert stats["processed"] == 1
        assert stats["errors"] == 0
        assert contact.embedding_dirty is False
        assert contact.embedding == [0.1] * 1024


@pytest.mark.asyncio
async def test_maintenance_index_messages(mock_session):
    msg = Message(id=1, content="This is a long enough message for embedding")
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [msg]
    mock_session.execute.return_value = mock_res

    with patch("src.pipeline.unified_processor.generate_embeddings_batch", AsyncMock(return_value=[[0.2] * 1024])):
        stats = await _maintenance_index_messages_impl(mock_session, batch_size=10)
        assert stats["processed"] == 1
        mock_session.add.assert_called()


@pytest.mark.asyncio
async def test_full_reindex():
    mock_session_val = AsyncMock()
    mock_session_val.__aenter__.return_value = mock_session_val
    mock_session_val.execute = AsyncMock()

    with patch("src.pipeline.unified_processor.get_session", return_value=mock_session_val), \
         patch("src.pipeline.unified_processor.maintenance_reindex_dirty") as mock_reindex:

        mock_reindex.side_effect = [{"processed": 50, "errors": 0}, {"processed": 0, "errors": 0}]

        stats = await full_reindex()
        assert stats["contacts_reindexed"] == 50
        assert mock_reindex.call_count == 2


def test_build_contact_profile():
    contact = Contact(first_name="John", last_name="Doe", company="Acme", facts_json={"City": "Belgrade"})
    profile = _build_contact_profile(contact)
    assert "Name: John Doe" in profile
    assert "Company: Acme" in profile
    assert "City: Belgrade" in profile


@pytest.mark.asyncio
async def test_update_all_lead_scores(mock_session):
    contact = Contact(
        id=1,
        is_lead=True,
        lead_context={
            "lead_history": [
                {"timestamp": datetime.now(timezone.utc).isoformat(), "quality": 8, "summary": "Dev work"}
            ]
        }
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [contact]
    mock_session.execute.return_value = mock_res

    with patch("src.pipeline.unified_processor.SettingsService") as mock_settings_cls, \
         patch("src.pipeline.unified_processor.get_session") as mock_get_session:

        mock_get_session.return_value.__aenter__.return_value = mock_session

        mock_settings = mock_settings_cls.return_value
        mock_settings.get = AsyncMock()
        mock_settings.get.side_effect = [['dev'], "1753396658", 5.0, 3.0, 2.0]

        stats = await update_all_lead_scores()
        assert stats["scored"] == 1
        assert contact.lead_score > 0
