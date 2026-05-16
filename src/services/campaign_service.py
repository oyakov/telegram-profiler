import asyncio
import structlog
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.marketing import Campaign, CampaignMessage, LeadSearch
from src.db.models.content import Contact
from src.connectors.telegram_connector import TelegramConnector
from src.ai.services import ExtractionService

logger = structlog.get_logger()

# Hard cap: never send to more than 200 contacts in a single campaign run to
# avoid Telegram spam bans and accidental mass-message incidents.
_MAX_CAMPAIGN_RECIPIENTS = 200

# Delay between messages: 5 s keeps us well under Telegram's ~30 msg/min limit.
_INTER_MESSAGE_DELAY_S = 5


class CampaignService:
    def __init__(self, session: AsyncSession, db_name: str | None = None):
        self.session = session
        self.db_name = db_name
        self.ai = ExtractionService()
        self.tg = TelegramConnector(db_name=db_name)

    async def create_messages_from_search(self, campaign_id: UUID, search_id: UUID):
        """Generate CampaignMessage entries for all contacts in a search."""
        # 1. Get search filter
        search = await self.session.get(LeadSearch, search_id)
        if not search:
            raise Exception("Search not found")

        # 2. Find matching contacts — cap at _MAX_CAMPAIGN_RECIPIENTS
        res = await self.session.execute(
            select(Contact).limit(_MAX_CAMPAIGN_RECIPIENTS)
        )
        contacts = res.scalars().all()

        # 3. Create CampaignMessages
        for contact in contacts:
            msg = CampaignMessage(
                campaign_id=campaign_id,
                contact_id=contact.id,
                status="pending"
            )
            self.session.add(msg)

        await self.session.commit()
        return len(contacts)

    async def run_campaign(self, campaign_id: UUID):
        """Execute the campaign: personalize and send messages."""
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            return

        # Safety check: refuse to run if already completed or running
        if campaign.status in ("running", "completed"):
            logger.warning(
                "campaign_already_in_terminal_state",
                campaign_id=str(campaign_id),
                status=campaign.status,
            )
            return

        campaign.status = "running"
        campaign.started_at = datetime.now(timezone.utc)
        await self.session.commit()

        # Get pending messages — apply hard cap here too in case rows were added manually
        res = await self.session.execute(
            select(CampaignMessage)
            .where(
                CampaignMessage.campaign_id == campaign_id,
                CampaignMessage.status == "pending"
            )
            .limit(_MAX_CAMPAIGN_RECIPIENTS)
        )
        messages = res.scalars().all()

        sent = 0
        failed = 0

        for cm in messages:
            try:
                # 1. Load contact
                contact = await self.session.get(Contact, cm.contact_id)
                if not contact:
                    continue

                # Guard: skip contacts with no telegram_id (can't deliver)
                if not contact.telegram_id:
                    cm.status = "skipped"
                    cm.error_message = "No telegram_id"
                    failed += 1
                    continue

                # 2. Build personalised text
                text = campaign.message.replace("{name}", contact.first_name or "")

                # 3. Send via Telegram
                success = await self.tg.send_message(contact.telegram_id, text)

                if success:
                    cm.status = "sent"
                    cm.sent_at = datetime.now(timezone.utc)
                    sent += 1
                else:
                    cm.status = "failed"
                    cm.error_message = "Telegram delivery failed"
                    failed += 1

            except Exception as e:
                cm.status = "failed"
                cm.error_message = str(e)
                failed += 1
                logger.error(
                    "campaign_message_failed",
                    campaign_id=str(campaign_id),
                    contact_id=str(cm.contact_id),
                    error=str(e),
                )

            # Persist progress and throttle
            campaign.sent_count = sent
            campaign.failed_count = failed
            await self.session.commit()

            # Rate-limit: 5 s between messages ≈ 12 msg/min, safe under Telegram's limit
            await asyncio.sleep(_INTER_MESSAGE_DELAY_S)

        campaign.status = "completed"
        campaign.completed_at = datetime.now(timezone.utc)
        await self.session.commit()

        logger.info(
            "campaign_completed",
            campaign_id=str(campaign_id),
            sent=sent,
            failed=failed,
        )
        return {"sent": sent, "failed": failed}
