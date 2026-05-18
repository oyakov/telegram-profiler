"""Contacts router — Refactored to delegate to ContactService."""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.services.contact_service import ContactService
from src.api.schemas import ContactCreate, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["Contacts"])

class AddToTrackedRequest(BaseModel):
    contact_ids: list[str]

@router.get("")
async def list_contacts(
    db: AsyncSession = Depends(get_db),
    source: Optional[str] = None,
    search: Optional[str] = None,
    is_personal: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List contacts with optional filtering and pagination."""
    service = ContactService(db)
    return await service.list_contacts(source, search, is_personal, page, page_size)

@router.get("/{contact_id}")
async def get_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single contact with details."""
    service = ContactService(db)
    try:
        return await service.get_contact(contact_id)
    except ValueError:
        raise HTTPException(404, "Contact not found")

@router.post("", status_code=201)
async def create_contact(data: ContactCreate, db: AsyncSession = Depends(get_db)):
    """Create a new contact."""
    service = ContactService(db)
    result = await service.create_contact(data.model_dump())
    await db.commit()
    return result

@router.patch("/{contact_id}")
async def update_contact(contact_id: str, data: ContactUpdate, db: AsyncSession = Depends(get_db)):
    """Update a contact."""
    service = ContactService(db)
    try:
        result = await service.update_contact(contact_id, data.model_dump(exclude_none=True))
        await db.commit()
        return result
    except ValueError:
        raise HTTPException(404, "Contact not found")

@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a contact."""
    service = ContactService(db)
    try:
        await service.delete_contact(contact_id)
        await db.commit()
    except ValueError:
        raise HTTPException(404, "Contact not found")

@router.post("/add-to-tracked")
async def add_to_tracked(
    req: AddToTrackedRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add contacts to tracked list."""
    service = ContactService(db)
    count = await service.add_to_tracked(req.contact_ids)
    await db.commit()
    return {"status": "success", "count": count}
