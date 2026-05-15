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
    if not search: raise Exception("Search not found")
    
    # 2. Find matching contacts (simplified logic for now)
    # In a real system, we'd run the full profile filter here
    # For now, we'll take contacts that were identified in the last run or just all contacts
    res = await self.session.execute(select(Contact).limit(100))
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
    if not campaign: return
    
    campaign.status = "running"
    campaign.started_at = datetime.now(timezone.utc)
    await self.session.commit()
    
    # Get pending messages
    res = await self.session.execute(
      select(CampaignMessage).where(
        CampaignMessage.campaign_id == campaign_id,
        CampaignMessage.status == "pending"
      )
    )
    messages = res.scalars().all()
    
    sent = 0
    failed = 0
    
    for cm in messages:
      try:
        # 1. Personalize message
        contact = await self.session.get(Contact, cm.contact_id)
        if not contact: continue
        
        # Personalized prompt
        prompt = f"Personalize this message for {contact.first_name} who is into {', '.join(contact.interests or [])}. Template: {campaign.message}"
        # For now, just use template
        text = campaign.message.replace("{name}", contact.first_name)
        
        # 2. Send via Telegram
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
        logger.error("campaign_message_failed", campaign_id=campaign_id, contact_id=cm.contact_id, error=str(e))
      
      # Update campaign progress
      campaign.sent_count = sent
      campaign.failed_count = failed
      await self.session.commit()
      
      # Throttling to avoid Telegram spam detection
      await asyncio.sleep(5) 
      
    campaign.status = "completed"
    campaign.completed_at = datetime.now(timezone.utc)
    await self.session.commit()
    
    return {"sent": sent, "failed": failed}
