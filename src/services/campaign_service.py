"""Campaign service — orchestrates lead selection, personalization, and message delivery."""

import asyncio
import structlog
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Campaign, CampaignMessage, LeadSearch, Contact
from src.db.repository import CampaignRepository, LeadSearchRepository
from src.services.marketing.base import BaseDeliveryProvider, PersonalizerInterface
from src.services.marketing.delivery.telegram import TelegramDeliveryProvider
from src.services.marketing.personalizer import SimplePersonalizer
from src.connectors.telegram_connector import TelegramConnector

logger = structlog.get_logger()

# Hard cap: never send to more than 200 contacts in a single campaign run
_MAX_CAMPAIGN_RECIPIENTS = 200

# Delay between messages to avoid spam bans
_INTER_MESSAGE_DELAY_S = 5


class CampaignService:
    """Service for managing and running marketing campaigns."""

    def __init__(
        self, 
        session: AsyncSession, 
        delivery_provider: Optional[BaseDeliveryProvider] = None,
        personalizer: Optional[PersonalizerInterface] = None
    ):
        self.session = session
        self.campaign_repo = CampaignRepository(session)
        self.search_repo = LeadSearchRepository(session)

        # Dependency Injection with defaults
        self.personalizer = personalizer or SimplePersonalizer()
        # Store provider; create the real Telegram delivery lazily (via the
        # property below) so no DB connections are opened at construction time
        # when running in test or DI contexts.
        self._delivery: Optional[BaseDeliveryProvider] = delivery_provider

    @property
    def delivery(self) -> BaseDeliveryProvider:
        """Lazy-initialized delivery provider — avoids real connections at init."""
        if self._delivery is None:
            self._delivery = TelegramDeliveryProvider(TelegramConnector())
        return self._delivery

    @delivery.setter
    def delivery(self, value: BaseDeliveryProvider) -> None:
        self._delivery = value

    async def create_messages_from_search(self, campaign_id: UUID, search_id: UUID) -> int:
        """Generate CampaignMessage entries for all contacts matching a lead search."""
        search = await self.session.get(LeadSearch, search_id)
        if not search:
            raise ValueError("Search not found")

        contacts = await self.search_repo.get_matching_contacts(
            search.profile_filter or {}, 
            limit=_MAX_CAMPAIGN_RECIPIENTS
        )

        for contact in contacts:
            msg = CampaignMessage(
                campaign_id=campaign_id,
                contact_id=contact.id,
                status="pending"
            )
            self.session.add(msg)

        await self.session.commit()
        return len(contacts)

    async def run_campaign(self, campaign_id: UUID) -> Dict[str, Any]:
        """Execute the campaign: personalize and deliver messages."""
        campaign = await self.session.get(Campaign, campaign_id)
        # Skip only fully completed campaigns — allow retry of "running" campaigns
        # so a worker crash mid-delivery doesn't permanently strand the campaign.
        # Pending CampaignMessages are re-fetched below, so already-sent ones are skipped.
        if not campaign or campaign.status == "completed":
            logger.warning("campaign_skip_execution", campaign_id=str(campaign_id), status=getattr(campaign, 'status', 'None'))
            return {"status": "skipped"}

        campaign.status = "running"
        campaign.started_at = datetime.now(timezone.utc)
        await self.session.commit()

        messages = await self.campaign_repo.get_pending_messages(campaign_id, limit=_MAX_CAMPAIGN_RECIPIENTS)

        # Bulk-load all contacts for the campaign messages to avoid N+1 queries
        contact_ids = [cm.contact_id for cm in messages]
        contacts_result = await self.session.execute(
            select(Contact).where(Contact.id.in_(contact_ids))
        )
        contacts_map = {c.id: c for c in contacts_result.scalars().all()}

        sent = 0
        failed = 0

        for cm in messages:
            try:
                contact = contacts_map.get(cm.contact_id)
                if not contact or not contact.telegram_id:
                    cm.status = "skipped"
                    cm.error_message = "No delivery identifier (telegram_id)"
                    failed += 1
                    continue

                # 1. Personalize
                context = {
                    "first_name": contact.first_name,
                    "last_name": contact.last_name,
                    "company": contact.company,
                    "position": contact.position
                }
                text = self.personalizer.personalize(campaign.message, context)

                # 2. Deliver
                success = await self.delivery.send_message(contact.telegram_id, text)

                if success:
                    cm.status = "sent"
                    cm.sent_at = datetime.now(timezone.utc)
                    sent += 1
                else:
                    cm.status = "failed"
                    cm.error_message = "Delivery provider failed"
                    failed += 1

            except Exception as e:
                logger.error("campaign_message_error", campaign_id=str(campaign_id), error=str(e))
                cm.status = "failed"
                # Store a generic message — str(e) may contain internal stack details
                # that would be exposed via the GET /campaigns/{id}/messages API.
                cm.error_message = "Internal delivery error"
                failed += 1

            # Update stats and throttle
            campaign.sent_count = sent
            campaign.failed_count = failed
            await self.session.commit()
            await asyncio.sleep(_INTER_MESSAGE_DELAY_S)

        campaign.status = "completed"
        campaign.completed_at = datetime.now(timezone.utc)
        await self.session.commit()

        return {"sent": sent, "failed": failed}
