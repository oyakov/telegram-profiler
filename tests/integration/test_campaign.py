import pytest
from unittest.mock import AsyncMock
from src.services.campaign_service import CampaignService
from src.db.models.marketing import Campaign, LeadSearch
from src.db.models.content import Contact


@pytest.mark.asyncio
async def test_campaign_lifecycle(db_session):
    """Test full campaign creation and execution flow."""
    # 1. Setup test data
    # contact must be marked is_lead=True so create_messages_from_search picks it up
    contact = Contact(
        first_name="Test",
        last_name="User",
        telegram_id="123456789",
        source="test",
        is_lead=True,
    )
    db_session.add(contact)

    search = LeadSearch(
        name="Test Search",
        profile_filter={"keywords": ["test"]}
    )
    db_session.add(search)

    campaign = Campaign(
        name="Test Campaign",
        message="Hello {name}!"
    )
    db_session.add(campaign)
    await db_session.commit()

    service = CampaignService(db_session)

    # 2. Add contacts to campaign
    count = await service.create_messages_from_search(campaign.id, search.id)
    assert count >= 1

    # 3. Run campaign — mock TelegramConnector to avoid real network calls
    service.tg.send_message = AsyncMock(return_value=True)

    result = await service.run_campaign(campaign.id)

    assert result["sent"] == count
    assert campaign.status == "completed"
