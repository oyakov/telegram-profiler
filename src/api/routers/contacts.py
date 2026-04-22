from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Contact
from src.api.schemas import ContactCreate, ContactUpdate, ContactResponse

router = APIRouter(prefix="/contacts", tags=["Contacts"])

def _contact_to_response(c: Contact) -> dict:
    return {
        "id": str(c.id),
        "first_name": c.first_name,
        "last_name": c.last_name,
        "company": c.company,
        "position": c.position,
        "email": c.email,
        "phone": c.phone,
        "telegram_id": c.telegram_id,
        "telegram_username": c.telegram_username,
        "linkedin_url": c.linkedin_url,
        "source": c.source,
        "interests": c.interests or [],
        "skills": c.skills or [],
        "notes": c.notes,
        "context": c.context,
        "bio": c.bio,
        "profile_photo_path": c.profile_photo_path,
        "is_lead": bool(c.is_lead),
        "lead_score": float(c.lead_score or 0.0),
        "our_channel_ratio": float(c.our_channel_ratio or 0.0),
        "lead_context": dict(c.lead_context or {}),
        "last_interaction": c.last_interaction.isoformat() if c.last_interaction else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }

@router.get("")
async def list_contacts(
    db: AsyncSession = Depends(get_db),
    source: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List contacts with optional filtering and pagination."""
    query = select(Contact)
    if source:
        query = query.where(Contact.source == source)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Contact.first_name.ilike(search_pattern))
            | (Contact.last_name.ilike(search_pattern))
            | (Contact.email.ilike(search_pattern))
            | (Contact.company.ilike(search_pattern))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(Contact.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    contacts = result.scalars().all()

    return {
        "contacts": [_contact_to_response(c) for c in contacts],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }

@router.get("/{contact_id}")
async def get_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single contact with details."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    return _contact_to_response(contact)

@router.post("", status_code=201)
async def create_contact(data: ContactCreate, db: AsyncSession = Depends(get_db)):
    """Create a new contact."""
    contact = Contact(**data.model_dump())
    db.add(contact)
    await db.flush()
    return _contact_to_response(contact)

@router.patch("/{contact_id}")
async def update_contact(contact_id: str, data: ContactUpdate, db: AsyncSession = Depends(get_db)):
    """Update a contact."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")

    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    contact.embedding_dirty = True
    await db.flush()
    return _contact_to_response(contact)

@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a contact."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    await db.delete(contact)
    await db.commit()
