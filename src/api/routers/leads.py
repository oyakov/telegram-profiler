"""Leads router — Refactored to delegate to LeadService."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.db.database import get_db
from src.services.lead_service import LeadService
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
    service = LeadService(db)
    return await service.list_top_leads(min_score, page, page_size)

@router.get("/searches")
async def list_lead_searches(
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(True),
):
    """List saved lead searches."""
    service = LeadService(db)
    searches = await service.list_searches(active_only=active_only)

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

@router.get("/{contact_id}/history")
async def get_lead_history(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get detailed lead history for a contact (paginated)."""
    service = LeadService(db)
    try:
        return await service.get_lead_history(contact_id, page, page_size)
    except ValueError as e:
        raise HTTPException(404, str(e))

@router.post("/process", status_code=202)
async def trigger_lead_processing(request: Request):
    """Manually trigger lead detection and scoring tasks."""
    from src.db.database import _DB_NAME_RE
    db_name = request.headers.get("X-Database") or None
    if db_name is not None and not _DB_NAME_RE.match(db_name):
        raise HTTPException(status_code=400, detail="Invalid X-Database header value")
    from src.pipeline.tasks import process_unified_messages, reindex_dirty_contacts

    r1 = process_unified_messages.delay(limit=500, db_name=db_name)
    r2 = reindex_dirty_contacts.delay(batch_size=50, db_name=db_name)

    return {"task_ids": [r1.id, r2.id], "status": "queued"}

@router.post("/search")
async def search_leads_by_profile(
    profile: LeadProfileFilter,
    db: AsyncSession = Depends(get_db),
):
    """Search leads by profile criteria (keywords, company, position, score, etc.)."""
    service = LeadService(db)
    return await service.search_leads(profile.model_dump())

@router.post("/searches")
async def create_lead_search(
    search: LeadSearchCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a new tracked lead search."""
    service = LeadService(db)
    lead_search = await service.create_lead_search({
        "name": search.name,
        "description": search.description,
        "profile_filter": search.profile_filter.model_dump()
    })
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

@router.post("/searches/{search_id}/run")
async def run_lead_search(
    search_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run a saved lead search and return results."""
    service = LeadService(db)
    try:
        result = await service.run_saved_search(search_id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
