"""Unit tests for CampaignService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.services.campaign_service import CampaignService
from src.db.models.marketing import Campaign, CampaignMessage, LeadSearch
from src.db.models.content import Contact


def _make_session():
    """Return a mock async session with synchronous add."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


def _make_service(session):
    """Return a CampaignService with a mock delivery provider (avoids abstract TelegramConnector)."""
    mock_delivery = AsyncMock()
    mock_delivery.send_message = AsyncMock(return_value=True)
    return CampaignService(session, delivery_provider=mock_delivery)


@pytest.mark.asyncio
async def test_create_messages_from_search_raises_when_search_missing():
    session = _make_session()
    session.get = AsyncMock(return_value=None)

    svc = _make_service(session)
    with pytest.raises(Exception, match="Search not found"):
        await svc.create_messages_from_search(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_create_messages_from_search_creates_entries():
    session = _make_session()

    search = LeadSearch(id=uuid4(), name="Test", profile_filter={})
    contact_a = Contact(id=uuid4(), first_name="Alice", telegram_id="111")
    contact_b = Contact(id=uuid4(), first_name="Bob", telegram_id="222")

    session.get = AsyncMock(return_value=search)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [contact_a, contact_b]
    session.execute = AsyncMock(return_value=mock_result)

    campaign_id = uuid4()
    svc = _make_service(session)
    count = await svc.create_messages_from_search(campaign_id, search.id)

    assert count == 2
    assert session.add.call_count == 2
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_campaign_marks_completed_and_returns_stats():
    session = _make_session()

    campaign_id = uuid4()
    campaign = Campaign(
        id=campaign_id,
        name="Demo",
        message="Hello {name}!",
        status="draft",
    )
    contact = Contact(
        id=uuid4(),
        first_name="Alice",
        telegram_id="111",
        interests=[]
    )
    cm = CampaignMessage(
        id=uuid4(),
        campaign_id=campaign_id,
        contact_id=contact.id,
        status="pending"
    )

    # get() returns campaign on first call, contact on subsequent
    session.get = AsyncMock(side_effect=[campaign, contact])

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [cm]
    session.execute = AsyncMock(return_value=mock_result)

    svc = _make_service(session)
    svc.delivery.send_message = AsyncMock(return_value=True)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await svc.run_campaign(campaign_id)

    assert result["sent"] == 1
    assert result["failed"] == 0
    assert campaign.status == "completed"
    assert campaign.completed_at is not None


@pytest.mark.asyncio
async def test_run_campaign_handles_send_failure():
    session = _make_session()

    campaign_id = uuid4()
    campaign = Campaign(
        id=campaign_id,
        name="Demo",
        message="Hi!",
        status="draft",
    )
    contact = Contact(id=uuid4(), first_name="Bob", telegram_id="222", interests=[])
    cm = CampaignMessage(
        id=uuid4(),
        campaign_id=campaign_id,
        contact_id=contact.id,
        status="pending"
    )

    session.get = AsyncMock(side_effect=[campaign, contact])
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [cm]
    session.execute = AsyncMock(return_value=mock_result)

    svc = _make_service(session)
    svc.delivery.send_message = AsyncMock(return_value=False)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await svc.run_campaign(campaign_id)

    assert result["sent"] == 0
    assert result["failed"] == 1
    assert cm.status == "failed"
    assert cm.error_message == "Delivery provider failed"


@pytest.mark.asyncio
async def test_run_campaign_returns_skipped_for_missing_campaign():
    session = _make_session()
    session.get = AsyncMock(return_value=None)

    svc = _make_service(session)
    result = await svc.run_campaign(uuid4())
    # New service returns {"status": "skipped"} rather than None when campaign not found
    assert result == {"status": "skipped"}
