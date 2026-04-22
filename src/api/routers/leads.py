"""Leads router — endpoints for managing and viewing detected leads."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Contact, Message
from src.api.routers.contacts import _contact_to_response

router = APIRouter(prefix="/leads", tags=["Leads"])

@router.get("/top")
async def list_top_leads(
    db: AsyncSession = Depends(get_db),
    min_score: float = Query(0.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List contacts identified as leads, ranked by score."""
    base_query = select(Contact).where(
        and_(Contact.is_lead == True, Contact.lead_score >= min_score)
    )
    
    # Get total count
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Build paginated query
    query = (
        base_query
        .order_by(Contact.lead_score.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    
    result = await db.execute(query)
    contacts = result.scalars().all()

    return {
        "contacts": [_contact_to_response(c) for c in contacts],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0
    }

# Legacy alias
@router.get("/ad-buyers")
async def list_top_ad_buyers(
    db: AsyncSession = Depends(get_db),
    min_score: float = Query(0.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return await list_top_leads(db, min_score, page, page_size)

@router.get("/{contact_id}/history")
async def get_lead_history(
    contact_id: str, 
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get detailed lead history for a contact (paginated)."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")

    lead_ctx = contact.lead_context or {}
    # Fallback for old data: check lead_history then ad_history
    history = lead_ctx.get("lead_history", lead_ctx.get("ad_history", []))
    total = len(history)
    
    # Slice history for pagination
    start = (page - 1) * page_size
    end = start + page_size
    paged_history = history[start:end]
    
    # Extract all message IDs to fetch them in one go
    message_ids = [item["message_id"] for item in paged_history if item.get("message_id")]
    
    messages_map = {}
    if message_ids:
        msg_result = await db.execute(
            select(Message).where(Message.id.in_(message_ids))
        )
        messages_map = {str(m.id): m for m in msg_result.scalars().all()}

    enriched = []
    for item in paged_history:
        msg_id = item.get("message_id")
        if msg_id and msg_id in messages_map:
            item["full_content"] = messages_map[msg_id].content
        enriched.append(item)

    return {
        "contact_id": contact_id, 
        "lead_history": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0
    }

# Legacy alias
@router.get("/ad-buyers/{contact_id}/history")
async def get_ad_history_alias(
    contact_id: str, 
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return await get_lead_history(contact_id, db, page, page_size)

@router.post("/process", status_code=202)
async def trigger_lead_processing(request: Request):
    """Manually trigger lead detection and scoring tasks."""
    db_name = request.headers.get("X-Database")
    from src.pipeline.tasks import process_unified_messages, update_lead_scores_task
    
    # Run sequentially (chain)
    chain = (process_unified_messages.s(db_name=db_name) | update_lead_scores_task.s(db_name=db_name))
    result = chain.delay()
    
    return {"task_id": result.id, "status": "queued"}
