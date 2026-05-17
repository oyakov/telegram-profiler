"""Contact service — manages contact data and response mapping."""

from __future__ import annotations
import structlog
from typing import Optional, List, Any
from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Contact
from src.db.repository import ContactRepository

logger = structlog.get_logger()

class ContactService:
    """Service for managing Contact operations and API response mapping."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ContactRepository(session)

    @staticmethod
    def map_to_response(c: Contact) -> dict:
        """Map a Contact model to a consistent API response dictionary."""
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
            "is_tracked": bool(c.is_tracked),
            "is_personal": bool(c.is_personal),
            "saved_at": c.saved_at.isoformat() if c.saved_at else None,
            "total_synced": int(c.total_messages_synced or 0),
            "oldest_msg_date": c.oldest_message_date.isoformat() if c.oldest_message_date else None,
            "last_interaction": c.last_interaction.isoformat() if c.last_interaction else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }

    async def list_contacts(
        self, 
        source: Optional[str] = None, 
        search: Optional[str] = None, 
        is_personal: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50
    ) -> dict:
        """List contacts with filtering and pagination."""
        query = select(Contact)
        if source:
            query = query.where(Contact.source == source)
        if is_personal is not None:
            query = query.where(Contact.is_personal == is_personal)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Contact.first_name.ilike(search_pattern))
                | (Contact.last_name.ilike(search_pattern))
                | (Contact.email.ilike(search_pattern))
                | (Contact.company.ilike(search_pattern))
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        query = query.order_by(Contact.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        contacts = result.scalars().all()

        return {
            "contacts": [self.map_to_response(c) for c in contacts],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else 0,
        }

    async def get_contact(self, contact_id: str) -> dict:
        """Get a single contact by ID."""
        result = await self.session.execute(select(Contact).where(Contact.id == contact_id))
        contact = result.scalar_one_or_none()
        if not contact:
            raise ValueError("Contact not found")
        return self.map_to_response(contact)

    async def create_contact(self, data: dict) -> dict:
        """Create a new contact."""
        contact = Contact(**data)
        self.session.add(contact)
        await self.session.flush()
        return self.map_to_response(contact)

    async def update_contact(self, contact_id: str, data: dict) -> dict:
        """Update an existing contact."""
        result = await self.session.execute(select(Contact).where(Contact.id == contact_id))
        contact = result.scalar_one_or_none()
        if not contact:
            raise ValueError("Contact not found")

        for field, value in data.items():
            setattr(contact, field, value)

        contact.embedding_dirty = True
        await self.session.flush()
        return self.map_to_response(contact)

    async def delete_contact(self, contact_id: str) -> None:
        """Delete a contact."""
        result = await self.session.execute(select(Contact).where(Contact.id == contact_id))
        contact = result.scalar_one_or_none()
        if not contact:
            raise ValueError("Contact not found")
        await self.session.delete(contact)
        await self.session.flush()

    async def add_to_tracked(self, contact_ids: List[str]) -> int:
        """Mark contacts as leads and tracked."""
        from uuid import UUID as _UUID
        validated_ids = [str(cid) for cid in contact_ids]
        
        result = await self.session.execute(
            select(Contact).where(Contact.id.in_(validated_ids))
        )
        contacts = result.scalars().all()

        for contact in contacts:
            contact.is_lead = True
            contact.is_tracked = True

        await self.session.flush()
        return len(contacts)
