"""Leads router — endpoints for managing and viewing detected leads."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import json

from src.db.database import get_db
from src.db.models import Contact, Message, LeadSearch
from src.api.routers.contacts import _contact_to_response
from src.api.schemas.leads import LeadProfileFilter, LeadSearchCreate, LeadSearchUpdate, LeadSearchResponse

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


@router.post("/search")
async def search_leads_by_profile(
    profile: LeadProfileFilter,
    db: AsyncSession = Depends(get_db),
):
    """Search leads by profile criteria (keywords, company, position, score, etc.)."""
    query = select(Contact).where(Contact.is_lead == True)

    # Apply filters
    filters = []

    if profile.first_name:
        filters.append(Contact.first_name.ilike(f"%{profile.first_name}%"))

    if profile.last_name:
        filters.append(Contact.last_name.ilike(f"%{profile.last_name}%"))

    if profile.company:
        filters.append(Contact.company.ilike(f"%{profile.company}%"))

    if profile.position:
        filters.append(Contact.position.ilike(f"%{profile.position}%"))

    # Keyword matching - search in interests or skills
    if profile.keywords:
        keyword_filters = []
        for kw in profile.keywords:
            keyword_filters.append(Contact.interests.contains([kw]))
        if keyword_filters:
            filters.append(or_(*keyword_filters))

    # Interest matching
    if profile.interests:
        interest_filters = []
        for interest in profile.interests:
            interest_filters.append(Contact.interests.contains([interest]))
        if interest_filters:
            filters.append(or_(*interest_filters))

    # Score filter
    if profile.min_score > 0:
        filters.append(Contact.lead_score >= profile.min_score)

    # Activity ratio filter
    filters.append(
        and_(
            Contact.our_channel_ratio >= profile.min_activity_ratio,
            Contact.our_channel_ratio <= profile.max_activity_ratio
        )
    )

    # Date filters
    if profile.created_after:
        filters.append(Contact.created_at >= profile.created_after)
    if profile.created_before:
        filters.append(Contact.created_at <= profile.created_before)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Build paginated query
    query = (
        query
        .order_by(Contact.lead_score.desc(), Contact.created_at.desc())
        .offset((profile.page - 1) * profile.page_size)
        .limit(profile.page_size)
    )

    result = await db.execute(query)
    contacts = result.scalars().all()

    return {
        "contacts": [_contact_to_response(c) for c in contacts],
        "total": total,
        "page": profile.page,
        "page_size": profile.page_size,
        "pages": (total + profile.page_size - 1) // profile.page_size if total else 0
    }


@router.post("/searches")
async def create_lead_search(
    search: LeadSearchCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a new tracked lead search."""
    lead_search = LeadSearch(
        name=search.name,
        description=search.description,
        profile_filter=search.profile_filter.model_dump(),
    )
    db.add(lead_search)
    await db.commit()
    await db.refresh(lead_search)

    return LeadSearchResponse(
        id=str(lead_search.id),
        name=lead_search.name,
        description=lead_search.description,
        profile_filter=lead_search.profile_filter,
        is_active=lead_search.is_active,
        created_at=lead_search.created_at,
        updated_at=lead_search.updated_at,
    )


@router.get("/searches")
async def list_lead_searches(
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(True),
):
    """List saved lead searches."""
    query = select(LeadSearch)
    if active_only:
        query = query.where(LeadSearch.is_active == True)

    query = query.order_by(LeadSearch.created_at.desc())

    result = await db.execute(query)
    searches = result.scalars().all()

    return [
        LeadSearchResponse(
            id=str(s.id),
            name=s.name,
            description=s.description,
            profile_filter=s.profile_filter,
            is_active=s.is_active,
            result_count=s.last_result_count,
            last_run_at=s.last_run_at,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in searches
    ]


@router.get("/searches/{search_id}")
async def get_lead_search(
    search_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific saved lead search."""
    result = await db.execute(select(LeadSearch).where(LeadSearch.id == search_id))
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(404, "Search not found")

    return LeadSearchResponse(
        id=str(search.id),
        name=search.name,
        description=search.description,
        profile_filter=search.profile_filter,
        is_active=search.is_active,
        result_count=search.last_result_count,
        last_run_at=search.last_run_at,
        created_at=search.created_at,
        updated_at=search.updated_at,
    )


@router.put("/searches/{search_id}")
async def update_lead_search(
    search_id: str,
    update: LeadSearchUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a saved lead search."""
    result = await db.execute(select(LeadSearch).where(LeadSearch.id == search_id))
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(404, "Search not found")

    if update.name is not None:
        search.name = update.name
    if update.description is not None:
        search.description = update.description
    if update.profile_filter is not None:
        search.profile_filter = update.profile_filter.model_dump()
    if update.is_active is not None:
        search.is_active = update.is_active

    await db.commit()
    await db.refresh(search)

    return LeadSearchResponse(
        id=str(search.id),
        name=search.name,
        description=search.description,
        profile_filter=search.profile_filter,
        is_active=search.is_active,
        result_count=search.last_result_count,
        last_run_at=search.last_run_at,
        created_at=search.created_at,
        updated_at=search.updated_at,
    )


@router.delete("/searches/{search_id}", status_code=204)
async def delete_lead_search(
    search_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved lead search."""
    result = await db.execute(select(LeadSearch).where(LeadSearch.id == search_id))
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(404, "Search not found")

    await db.delete(search)
    await db.commit()


@router.post("/searches/{search_id}/run")
async def run_lead_search(
    search_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run a saved lead search and return results."""
    result = await db.execute(select(LeadSearch).where(LeadSearch.id == search_id))
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(404, "Search not found")

    # Reconstruct profile filter from stored JSON
    profile_data = search.profile_filter.copy() if isinstance(search.profile_filter, dict) else json.loads(search.profile_filter)
    profile_data["page"] = 1
    profile_data["page_size"] = 50
    profile = LeadProfileFilter(**profile_data)

    # Execute the search
    query = select(Contact).where(Contact.is_lead == True)
    filters = []

    if profile.first_name:
        filters.append(Contact.first_name.ilike(f"%{profile.first_name}%"))
    if profile.last_name:
        filters.append(Contact.last_name.ilike(f"%{profile.last_name}%"))
    if profile.company:
        filters.append(Contact.company.ilike(f"%{profile.company}%"))
    if profile.position:
        filters.append(Contact.position.ilike(f"%{profile.position}%"))

    if profile.keywords:
        keyword_filters = []
        for kw in profile.keywords:
            keyword_filters.append(Contact.interests.contains([kw]))
        if keyword_filters:
            filters.append(or_(*keyword_filters))

    if profile.interests:
        interest_filters = []
        for interest in profile.interests:
            interest_filters.append(Contact.interests.contains([interest]))
        if interest_filters:
            filters.append(or_(*interest_filters))

    if profile.min_score > 0:
        filters.append(Contact.lead_score >= profile.min_score)

    filters.append(
        and_(
            Contact.our_channel_ratio >= profile.min_activity_ratio,
            Contact.our_channel_ratio <= profile.max_activity_ratio
        )
    )

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Update search metadata
    search.last_run_at = datetime.utcnow()
    search.last_result_count = total
    await db.commit()

    # Fetch results
    result_query = (
        query
        .order_by(Contact.lead_score.desc(), Contact.created_at.desc())
        .limit(50)
    )

    results = await db.execute(result_query)
    contacts = results.scalars().all()

    return {
        "search_id": str(search.id),
        "contacts": [_contact_to_response(c) for c in contacts],
        "total": total,
        "last_run_at": search.last_run_at,
    }
