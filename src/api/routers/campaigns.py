"""API routes for campaign management."""

from uuid import UUID
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.db.models import Campaign, CampaignMessage, Contact
from src.db.database import get_db
from src.api.schemas.campaigns import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignPreviewRequest,
    CampaignPreviewResponse,
    CampaignMessageResponse,
)
from src.pipeline.tasks import send_campaign

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _render_message(message: str, contact: Contact) -> str:
    """Render message template with contact variables using safe string replacement.

    Deliberately avoids str.format() to prevent format-string injection attacks
    (e.g. `{first_name.__class__.__mro__}` exposing internals).
    """
    replacements = {
        "{first_name}": contact.first_name or "",
        "{last_name}": contact.last_name or "",
        "{email}": contact.email or "",
        "{phone}": contact.phone or "",
        "{company}": contact.company or "",
        "{position}": contact.position or "",
        # Legacy single-brace alias still supported by campaign_service.py
        "{name}": contact.first_name or "",
    }
    result = message
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    request: CampaignCreate,
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    """Create a new campaign in draft status."""
    # Check if campaign name already exists
    existing = await db.execute(
        select(Campaign).where(Campaign.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Campaign with this name already exists")

    # Verify all contacts exist
    if request.contact_ids:
        contacts_result = await db.execute(
            select(Contact).where(Contact.id.in_(request.contact_ids))
        )
        contacts = contacts_result.scalars().all()
        if len(contacts) != len(request.contact_ids):
            raise HTTPException(status_code=400, detail="Some contacts not found")

    # Create campaign
    campaign = Campaign(
        name=request.name,
        description=request.description,
        message=request.message,
        status="draft",
        total_contacts=len(request.contact_ids),
    )
    db.add(campaign)
    await db.flush()

    # Create campaign messages for each contact
    messages = [
        CampaignMessage(campaign_id=campaign.id, contact_id=contact_id, status="pending")
        for contact_id in request.contact_ids
    ]
    db.add_all(messages)

    await db.commit()
    await db.refresh(campaign)
    return campaign


_CampaignStatus = Literal["draft", "sending", "completed", "failed"]
_CampaignMessageStatus = Literal["pending", "sent", "failed", "skipped"]


@router.get("", response_model=dict)
async def list_campaigns(
    status: Optional[_CampaignStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List campaigns with pagination."""
    query = select(Campaign)
    if status:
        query = query.where(Campaign.status == status)

    # Get total count (must apply the same status filter)
    count_query = select(func.count(Campaign.id))
    if status:
        count_query = count_query.where(Campaign.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get paginated results
    query = query.order_by(Campaign.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    campaigns = result.scalars().all()

    return {
        "campaigns": [CampaignListResponse.model_validate(c) for c in campaigns],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    """Get campaign details with message statuses."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Load messages
    msg_result = await db.execute(
        select(CampaignMessage)
        .where(CampaignMessage.campaign_id == campaign_id)
        .order_by(CampaignMessage.created_at)
        .limit(100)
    )
    campaign.messages = msg_result.scalars().all()

    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    request: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
) -> Campaign:
    """Update campaign (only draft status)."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Can only update draft campaigns")

    if request.name is not None:
        campaign.name = request.name
    if request.description is not None:
        campaign.description = request.description
    if request.message is not None:
        campaign.message = request.message

    campaign.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete campaign (only draft status)."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Can only delete draft campaigns")

    await db.delete(campaign)
    await db.commit()
    return {"ok": True}


@router.post("/{campaign_id}/send")
async def send_campaign_messages(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start sending campaign messages."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ("draft", "failed"):
        raise HTTPException(status_code=400, detail="Campaign already sent or sending")

    campaign.status = "sending"
    campaign.started_at = datetime.now(timezone.utc)
    await db.commit()

    task = send_campaign.delay(str(campaign_id))

    return {
        "ok": True,
        "campaign_id": str(campaign_id),
        "task_id": task.id,
        "status": "sending",
    }


@router.get("/{campaign_id}/messages")
async def get_campaign_messages(
    campaign_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[_CampaignMessageStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get campaign message statuses with pagination."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = select(CampaignMessage).where(CampaignMessage.campaign_id == campaign_id)
    if status:
        query = query.where(CampaignMessage.status == status)

    count_query = select(func.count(CampaignMessage.id)).where(CampaignMessage.campaign_id == campaign_id)
    if status:
        count_query = count_query.where(CampaignMessage.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    query = query.order_by(CampaignMessage.created_at).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    messages = result.scalars().all()

    return {
        "messages": [CampaignMessageResponse.model_validate(m) for m in messages],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.post("/preview")
async def preview_campaign_message(
    request: CampaignPreviewRequest,
) -> CampaignPreviewResponse:
    """Preview campaign message with variable substitution."""
    class DummyContact:
        def __init__(self, data: dict):
            self.first_name = data.get("first_name", "John")
            self.last_name = data.get("last_name", "Doe")
            self.email = data.get("email", "john@example.com")
            self.phone = data.get("phone", "+1234567890")
            self.company = data.get("company", "Acme Corp")
            self.position = data.get("position", "Developer")

    contact = DummyContact(request.sample_contact)
    rendered = _render_message(request.message, contact)

    return CampaignPreviewResponse(original=request.message, rendered=rendered)
