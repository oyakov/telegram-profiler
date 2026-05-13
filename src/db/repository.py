from __future__ import annotations
import structlog
from typing import List, Optional, Union
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Message, MessageContact, Contact, ExtractionLog

logger = structlog.get_logger()


class MessageRepository:
    """Repository for managing Message and MessageContact operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_telegram_message(
        self,
        contact_id: UUID,
        source_message_id: str,
        direction: str,
        content: str,
        group_id: str,
        group_name: str,
        timestamp: any,
        raw_json: Optional[dict] = None
    ) -> Message:
        """Create a new message and its sender association."""
        
        # Check if exists
        exists_stmt = select(Message).where(Message.source_message_id == source_message_id)
        result = await self.session.execute(exists_stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing

        message = Message(
            contact_id=contact_id,
            source="telegram",
            source_message_id=source_message_id,
            direction=direction,
            content=content,
            group_id=group_id,
            group_name=group_name,
            timestamp=timestamp,
            raw_json=raw_json
        )
        self.session.add(message)
        await self.session.flush()

        # Create association
        assoc = MessageContact(
            message_id=message.id,
            contact_id=contact_id,
            role="sender"
        )
        self.session.add(assoc)
        
        return message

    async def bulk_check_exists(self, source_message_ids: List[str]) -> set[str]:
        """Check which message IDs already exist in the database."""
        if not source_message_ids:
            return set()
            
        stmt = select(Message.source_message_id).where(Message.source_message_id.in_(source_message_ids))
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}


class ContactRepository:
    """Repository for managing Contact operations and deduplication."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_duplicate(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        telegram_id: Optional[str] = None,
        telegram_username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        embedding: Optional[list[float]] = None,
        cosine_threshold: float = 0.85,
    ) -> Optional[Contact]:
        """Find a potential duplicate contact using multi-stage matching."""

        # Stage 1: Exact identifiers
        exact_conditions = []
        if email: exact_conditions.append(Contact.email == email)
        if phone: exact_conditions.append(Contact.phone == phone)
        if telegram_id: exact_conditions.append(Contact.telegram_id == telegram_id)
        if telegram_username: exact_conditions.append(Contact.telegram_username == telegram_username)

        if exact_conditions:
            result = await self.session.execute(
                select(Contact).where(or_(*exact_conditions)).limit(1)
            )
            match = result.scalar_one_or_none()
            if match:
                logger.info("dedup_exact_match", contact_id=str(match.id), match_type="exact")
                return match

        # Stage 2: Cosine similarity on embeddings
        if embedding:
            distance_threshold = 1.0 - cosine_threshold
            result = await self.session.execute(
                select(Contact)
                .where(Contact.embedding.cosine_distance(embedding) <= distance_threshold)
                .order_by(Contact.embedding.cosine_distance(embedding))
                .limit(1)
            )
            match = result.scalar_one_or_none()
            if match:
                logger.info("dedup_cosine_match", contact_id=str(match.id), match_type="fuzzy_embedding")
                return match

        # Stage 3: Name match fallback
        if first_name and last_name:
            result = await self.session.execute(
                select(Contact)
                .where(Contact.first_name == first_name, Contact.last_name == last_name)
                .limit(1)
            )
            match = result.scalar_one_or_none()
            if match:
                logger.info("dedup_name_match", contact_id=str(match.id))
                return match

        return None

    def merge_contact_fields(self, existing: Contact, new_data: dict) -> bool:
        """Merge new data into an existing contact. Only fills empty fields."""
        updated = False
        fillable_fields = ["first_name", "last_name", "company", "position", "email", "phone", "telegram_id", "telegram_username", "linkedin_url", "context"]

        for field in fillable_fields:
            new_val = new_data.get(field)
            if new_val and not getattr(existing, field, None):
                setattr(existing, field, new_val)
                updated = True

        for list_field in ["interests", "skills"]:
            new_items = new_data.get(list_field, [])
            if new_items:
                current = getattr(existing, list_field, None) or []
                merged = list(set(current + new_items))
                if merged != current:
                    setattr(existing, list_field, merged)
                    updated = True

        new_facts = new_data.get("facts", {}) or new_data.get("facts_json", {})
        if new_facts:
            current_facts = existing.facts_json or {}
            for k, v in new_facts.items():
                if k not in current_facts:
                    current_facts[k] = v
                    updated = True
            if updated:
                existing.facts_json = current_facts

        new_notes = new_data.get("notes")
        if new_notes:
            existing.notes = f"{existing.notes}\n---\n{new_notes}" if existing.notes else new_notes
            updated = True

        if updated:
            existing.embedding_dirty = True
            logger.info("contact_merged", contact_id=str(existing.id))

        return updated


class ExtractionRepository:
    """Repository for managing ExtractionLog and AI results."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_extraction(
        self,
        source_type: str,
        source_id: str,
        model_used: str,
        extracted_data: dict,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> ExtractionLog:
        """Log an AI extraction attempt."""
        log_entry = ExtractionLog(
            source_type=source_type,
            source_id=source_id,
            model_used=model_used,
            extracted_data=extracted_data,
            success=success,
            error_message=error_message
        )
        self.session.add(log_entry)
        return log_entry
