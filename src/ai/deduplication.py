"""Contact deduplication — exact match + cosine similarity."""

from __future__ import annotations

import structlog
from typing import Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.embeddings import cosine_similarity, generate_embedding
from src.db.models import Contact

logger = structlog.get_logger()


async def find_duplicate(
    session: AsyncSession,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    telegram_id: Optional[str] = None,
    telegram_username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    embedding: Optional[list[float]] = None,
    cosine_threshold: float = 0.85,
) -> Optional[Contact]:
    """Find a potential duplicate contact.

    Strategy:
    1. Exact match on email, phone, or telegram_id (definitive)
    2. Cosine similarity on embeddings (fuzzy)
    3. Name match as fallback
    """

    # --- Stage 1: Exact identifiers ---
    exact_conditions = []
    if email:
        exact_conditions.append(Contact.email == email)
    if phone:
        exact_conditions.append(Contact.phone == phone)
    if telegram_id:
        exact_conditions.append(Contact.telegram_id == telegram_id)
    if telegram_username:
        exact_conditions.append(Contact.telegram_username == telegram_username)

    if exact_conditions:
        result = await session.execute(
            select(Contact).where(or_(*exact_conditions)).limit(1)
        )
        match = result.scalar_one_or_none()
        if match:
            logger.info("dedup_exact_match", contact_id=str(match.id), match_type="exact")
            return match

    # --- Stage 2: Cosine similarity on embeddings ---
    if embedding:
        # cosine_distance = 1 - cosine_similarity
        # similarity >= 0.85  =>  distance <= 0.15
        distance_threshold = 1.0 - cosine_threshold
        
        result = await session.execute(
            select(Contact)
            .where(Contact.embedding.cosine_distance(embedding) <= distance_threshold)
            .order_by(Contact.embedding.cosine_distance(embedding))
            .limit(1)
        )
        match = result.scalar_one_or_none()
        if match:
            # We can still log the exact similarity for tracking
            # But the database already filtered it for us
            logger.info(
                "dedup_cosine_match",
                contact_id=str(match.id),
                match_type="fuzzy_embedding"
            )
            return match

    # --- Stage 3: Name match fallback ---
    if first_name and last_name:
        result = await session.execute(
            select(Contact)
            .where(
                Contact.first_name == first_name,
                Contact.last_name == last_name,
            )
            .limit(1)
        )
        match = result.scalar_one_or_none()
        if match:
            logger.info("dedup_name_match", contact_id=str(match.id))
            return match

    return None


def merge_contact_fields(existing: Contact, new_data: dict) -> bool:
    """Merge new data into an existing contact. Only fills empty fields.

    Returns True if any field was updated.
    """
    updated = False

    # Fields that can be filled if currently empty
    fillable_fields = [
        "first_name", "last_name", "company", "position",
        "email", "phone", "telegram_id", "telegram_username",
        "linkedin_url", "context",
    ]

    for field in fillable_fields:
        new_val = new_data.get(field)
        if new_val and not getattr(existing, field, None):
            setattr(existing, field, new_val)
            updated = True

    # Merge lists (interests, skills) — append unique items
    for list_field in ["interests", "skills"]:
        new_items = new_data.get(list_field, [])
        if new_items:
            current = getattr(existing, list_field, None) or []
            merged = list(set(current + new_items))
            if merged != current:
                setattr(existing, list_field, merged)
                updated = True

    # Merge facts_json — add new keys, don't overwrite existing
    new_facts = new_data.get("facts", {}) or new_data.get("facts_json", {})
    if new_facts:
        current_facts = existing.facts_json or {}
        for k, v in new_facts.items():
            if k not in current_facts:
                current_facts[k] = v
                updated = True
        if updated:
            existing.facts_json = current_facts

    # Notes — append
    new_notes = new_data.get("notes")
    if new_notes:
        if existing.notes:
            existing.notes = f"{existing.notes}\n---\n{new_notes}"
        else:
            existing.notes = new_notes
        updated = True

    if updated:
        existing.embedding_dirty = True
        logger.info("contact_merged", contact_id=str(existing.id))

    return updated
