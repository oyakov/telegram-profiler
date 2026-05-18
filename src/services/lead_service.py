"""Lead service — manages lead detection, history, and search execution."""

from __future__ import annotations
import structlog
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Contact, Message, LeadSearch
from src.db.repository import LeadSearchRepository
from src.services.contact_service import ContactService

logger = structlog.get_logger()

class LeadService:
    """Service for managing Lead-specific operations and history."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LeadSearchRepository(session)
        self.contact_svc = ContactService(session)

    async def list_top_leads(
        self, 
        min_score: float = 0.0, 
        page: int = 1, 
        page_size: int = 50
    ) -> dict:
        """List contacts identified as leads, ranked by score."""
        base_query = select(Contact).where(
            and_(Contact.is_lead == True, Contact.lead_score >= min_score)
        )
        
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0
        
        query = (
            base_query
            .order_by(Contact.lead_score.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        
        result = await self.session.execute(query)
        contacts = result.scalars().all()

        return {
            "contacts": [self.contact_svc.map_to_response(c) for c in contacts],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else 0
        }

    async def get_lead_history(
        self, 
        contact_id: str, 
        page: int = 1, 
        page_size: int = 50
    ) -> dict:
        """Get detailed lead history for a contact with enriched message content."""
        try:
            contact_uuid = UUID(contact_id)
        except (ValueError, AttributeError):
            raise ValueError("Contact not found")
        result = await self.session.execute(select(Contact).where(Contact.id == contact_uuid))
        contact = result.scalar_one_or_none()
        if not contact:
            raise ValueError("Contact not found")

        lead_ctx = contact.lead_context or {}
        history = lead_ctx.get("lead_history", lead_ctx.get("ad_history", []))
        total = len(history)
        
        start = (page - 1) * page_size
        end = start + page_size
        paged_history = history[start:end]
        
        message_ids = [item["message_id"] for item in paged_history if item.get("message_id")]
        
        messages_map = {}
        if message_ids:
            msg_result = await self.session.execute(
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

    async def search_leads(self, profile_filter: dict) -> dict:
        """Search leads by profile criteria."""
        page = profile_filter.get("page", 1)
        page_size = profile_filter.get("page_size", 50)
        offset = (page - 1) * page_size

        # Count query — DB-level, no Python-side slice
        total = await self.repo.count_matching_contacts(profile_filter)

        # Paged data query
        contacts = await self.repo.get_matching_contacts(
            profile_filter, limit=page_size, offset=offset
        )

        return {
            "contacts": [self.contact_svc.map_to_response(c) for c in contacts],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else 0
        }

    async def create_lead_search(self, data: dict) -> LeadSearch:
        """Save a new tracked lead search."""
        lead_search = LeadSearch(
            name=data["name"],
            description=data.get("description"),
            profile_filter=data["profile_filter"],
        )
        self.session.add(lead_search)
        await self.session.flush()
        return lead_search

    async def list_searches(self, active_only: bool = True) -> list:
        """List saved lead searches."""
        query = select(LeadSearch)
        if active_only:
            query = query.where(LeadSearch.is_active == True)
        query = query.order_by(LeadSearch.created_at.desc()).limit(200)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def run_saved_search(self, search_id: str) -> dict:
        """Run a saved lead search and return results."""
        try:
            search_uuid = UUID(search_id)
        except (ValueError, AttributeError):
            raise ValueError("Search not found")
        result = await self.session.execute(select(LeadSearch).where(LeadSearch.id == search_uuid))
        search = result.scalar_one_or_none()
        if not search:
            raise ValueError("Search not found")

        # Execute the search using the stored filter.
        # Use the saved page_size, or a generous default of 200 so that
        # last_result_count reflects a realistic count rather than always ≤ 50.
        profile_filter = search.profile_filter
        run_limit = profile_filter.get("page_size", 200) if isinstance(profile_filter, dict) else 200
        contacts = await self.repo.get_matching_contacts(profile_filter, limit=run_limit)

        # Update search metadata
        search.last_run_at = datetime.now(timezone.utc)
        search.last_result_count = len(contacts)
        
        return {
            "search_id": str(search.id),
            "contacts": [self.contact_svc.map_to_response(c) for c in contacts],
            "total": len(contacts),
            "last_run_at": search.last_run_at,
        }
