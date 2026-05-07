"""Unified processing pipeline — orchestrates extraction, deduplication, and lead scoring."""

from __future__ import annotations

import asyncio
import structlog
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Union

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.services import ExtractionService, ContactExtraction, LeadExtraction
from src.ai.deduplication import find_duplicate, merge_contact_fields
from src.ai.embeddings import generate_embedding
from src.core.settings_service import SettingsService
from src.db.database import get_session
from src.db.models import Contact, ExtractionLog, Message, MessageEmbedding, MessageContact

logger = structlog.get_logger()


class MessageProcessor:
    """Unified processor for incoming messages from all sources."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ai_service = ExtractionService()

    async def process_batch(self, messages: list[Message], force_lead_detection: bool = False) -> dict:
        """Process a batch of messages. 
        Detects contacts, leads, and generates embeddings.
        """
        stats = {"processed": 0, "contacts_found": 0, "leads_found": 0, "errors": 0}

        for msg in messages:
            try:
                if not msg.content or len(msg.content.strip()) < 10:
                    continue

                # 1. Run Extraction
                is_channel = msg.raw_json.get("is_channel", False) if msg.raw_json else False
                
                # Extract contacts
                contacts, _ = await self.ai_service.extract(
                    msg.content, 
                    extraction_type="contacts", 
                    source_context=f"Group: {msg.group_name or 'Unknown'}"
                )
                
                # Extract leads (commercial intent)
                leads = []
                if is_channel or force_lead_detection:
                    leads, _ = await self.ai_service.extract(
                        msg.content, 
                        extraction_type="leads",
                        source_context=f"Group: {msg.group_name or 'Unknown'}"
                    )
                
                # 3. Sync contacts found (if any)
                for c_data in contacts:
                    contact = await self._sync_contact(c_data)
                    if contact:
                        stats["contacts_found"] += 1
                        if not is_channel:
                            msg.contact_id = contact.id

                # 4. Sync leads found
                for l_data in leads:
                    if l_data.confidence < 0.6:
                        continue
                    contact = await self._sync_lead(l_data, msg)
                    if contact:
                        stats["leads_found"] += 1

                # 5. Log extraction
                log_entry = ExtractionLog(
                    source_type="unified_message",
                    source_id=str(msg.id),
                    model_used=self.ai_service.model,
                    extracted_data={
                        "contacts": [c.model_dump() for c in contacts],
                        "leads": [l.model_dump() for l in leads]
                    },
                    success=True
                )
                self.session.add(log_entry)
                stats["processed"] += 1

                await self.session.flush()

            except Exception as e:
                logger.error("unified_message_processing_error", message_id=str(msg.id), error=str(e))
                stats["errors"] += 1

        return stats

    async def _sync_contact(self, extraction: ContactExtraction) -> Optional[Contact]:
        """Deduplicate and sync contact data."""
        contact = await find_duplicate(
            self.session,
            email=extraction.email,
            phone=extraction.phone,
            telegram_username=extraction.telegram_username,
            first_name=extraction.first_name,
            last_name=extraction.last_name
        )

        if not contact:
            contact = Contact(
                **extraction.model_dump(exclude={"confidence", "facts"}),
                facts_json=extraction.facts,
                source="ai_extraction",
                embedding_dirty=True
            )
            self.session.add(contact)
            await self.session.flush()
        else:
            merge_contact_fields(contact, extraction.model_dump(exclude_none=True))
        
        return contact

    async def _sync_lead(self, lead_data: LeadExtraction, original_msg: Message) -> Optional[Contact]:
        """Update or create a contact based on detected lead data."""
        contact = await find_duplicate(
            self.session,
            telegram_username=lead_data.username,
            first_name=lead_data.display_name
        )
            
        new_lead_entry = {
            "message_id": str(original_msg.id),
            "group_id": original_msg.group_id,
            "timestamp": original_msg.timestamp.isoformat(),
            "summary": lead_data.content_summary,
            "category": lead_data.category,
            "lead_type": lead_data.lead_type,
            "evidence": lead_data.evidence_quote,
            "quality": lead_data.lead_quality
        }

        if not contact:
            contact = Contact(
                first_name=lead_data.display_name or lead_data.username,
                telegram_username=lead_data.username,
                source="telegram_lead",
                is_lead=True,
                lead_context={
                    "lead_history": [new_lead_entry]
                },
                notes=f"Detected as {lead_data.category} {lead_data.lead_type} in Belgrade. {lead_data.content_summary}"
            )
            self.session.add(contact)
            await self.session.flush()
        else:
            contact.is_lead = True
            ctx = contact.lead_context or {}
            history = ctx.get("lead_history", [])
            history.append(new_lead_entry)
            ctx["lead_history"] = history[-50:]
            if "niche" not in ctx:
                ctx["niche"] = lead_data.category
            contact.lead_context = ctx
            contact.embedding_dirty = True
            
        link_exists = await self.session.execute(
            select(MessageContact).where(
                and_(
                    MessageContact.message_id == original_msg.id,
                    MessageContact.contact_id == contact.id,
                    MessageContact.role == "lead"
                )
            )
        )
        if not link_exists.scalar_one_or_none():
            msg_link = MessageContact(message_id=original_msg.id, contact_id=contact.id, role="lead")
            self.session.add(msg_link)

        return contact


async def process_unprocessed_messages(limit: int = 100, session: Optional[AsyncSession] = None, db_name: str | None = None) -> dict:
    """Entry point for background task to process new messages."""
    if session is None:
        async with get_session(db_name=db_name) as new_session:
            return await _process_messages_impl(new_session, limit)
    return await _process_messages_impl(session, limit)


async def _process_messages_impl(session: AsyncSession, limit: int) -> dict:
    processed_ids = select(ExtractionLog.source_id).where(ExtractionLog.source_type == "unified_message")
    import sqlalchemy as sa
    query = (
        select(Message)
        .where(Message.id.cast(sa.String).not_in(processed_ids))
        .order_by(Message.timestamp.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    messages = result.scalars().all()
    if not messages: return {"processed": 0}
    processor = MessageProcessor(session)
    return await processor.process_batch(messages)


async def update_all_lead_scores(session: Optional[AsyncSession] = None, db_name: str | None = None) -> dict:
    """Calculate lead scores for all leads."""
    if session is None:
        async with get_session(db_name=db_name) as new_session:
            return await _update_lead_scores_impl(new_session)
    return await _update_lead_scores_impl(session)


async def _update_lead_scores_impl(session: AsyncSession) -> dict:
    settings = SettingsService(session)
    HIGH_VALUE_KEYWORDS = await settings.get("scoring_high_value_keywords", ['dev', 'invest', 'agency', 'partnership', 'ai', 'software', 'hiring'])
    OUR_CHANNEL_ID = await settings.get("scoring_our_channel_id", "1753396658")
    KW_BONUS = await settings.get("scoring_weight_keyword_bonus", 5.0)
    MULT_WEEK = await settings.get("scoring_multiplier_recent_week", 3.0)
    MULT_MONTH = await settings.get("scoring_multiplier_recent_month", 2.0)
    
    stats = {"scored": 0}
    result = await session.execute(select(Contact).where(Contact.is_lead == True))
    contacts = result.scalars().all()
    
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    for contact in contacts:
        ctx = contact.lead_context or {}
        history = ctx.get("lead_history", [])
        total_score = 0.0
        our_channel_count = 0
        for entry in history:
            entry_score = 1.0
            if str(entry.get("group_id")) == OUR_CHANNEL_ID: our_channel_count += 1
            try:
                ts = datetime.fromisoformat(entry["timestamp"])
                if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
                if ts > week_ago: entry_score *= MULT_WEEK
                elif ts > month_ago: entry_score *= MULT_MONTH
            except Exception: pass
            summary = (entry.get("summary") or "").lower()
            if any(kw in summary for kw in HIGH_VALUE_KEYWORDS): entry_score += KW_BONUS
            quality = float(entry.get("quality", 5))
            entry_score *= (quality / 5.0)
            total_score += entry_score
        contact.lead_score = round(total_score, 2)
        if history: contact.our_channel_ratio = round((our_channel_count / len(history)) * 100.0, 1)
        else: contact.our_channel_ratio = 0.0
        stats["scored"] += 1
    return stats


async def maintenance_reindex_dirty(batch_size: int = 50, session: Optional[AsyncSession] = None, db_name: str | None = None) -> dict:
    """Process contacts with embedding_dirty=True."""
    if session is None:
        async with get_session(db_name=db_name) as new_session:
            return await _maintenance_reindex_dirty_impl(new_session, batch_size)
    return await _maintenance_reindex_dirty_impl(session, batch_size)


async def _maintenance_reindex_dirty_impl(session: AsyncSession, batch_size: int) -> dict:
    stats = {"processed": 0, "errors": 0, "skipped": 0}
    result = await session.execute(select(Contact).where(Contact.embedding_dirty == True).limit(batch_size))
    contacts = result.scalars().all()
    if not contacts: return stats

    for contact in contacts:
        try:
            profile_text = _build_contact_profile(contact)
            msg_result = await session.execute(select(Message).where(Message.contact_id == contact.id).order_by(Message.timestamp.desc()).limit(20))
            messages = msg_result.scalars().all()
            message_texts = [m.content for m in messages if m.content]
            if message_texts: profile_text += "\n\nRecent messages:\n" + "\n".join(message_texts[:10])
            if profile_text.strip():
                contact.embedding = await generate_embedding(profile_text)
            contact.embedding_dirty = False
            contact.updated_at = datetime.now(timezone.utc)
            stats["processed"] += 1
        except Exception as e:
            logger.error("contact_processing_error", contact_id=str(contact.id), error=str(e))
            stats["errors"] += 1
    return stats


async def maintenance_index_messages(batch_size: int = 100, session: Optional[AsyncSession] = None, db_name: str | None = None) -> dict:
    """Find messages without embeddings and generate them."""
    if session is None:
        async with get_session(db_name=db_name) as new_session:
            return await _maintenance_index_messages_impl(new_session, batch_size)
    return await _maintenance_index_messages_impl(session, batch_size)


async def _maintenance_index_messages_impl(session: AsyncSession, batch_size: int) -> dict:
    stats = {"processed": 0, "errors": 0}
    processed_ids = select(MessageEmbedding.message_id)
    query = (
        select(Message)
        .where(Message.id.not_in(processed_ids))
        .where(Message.content.isnot(None))
        .where(func.length(Message.content) > 10)
        .limit(batch_size)
    )
    result = await session.execute(query)
    messages = result.scalars().all()
    if not messages: return stats

    for msg in messages:
        try:
            text = msg.content.strip()
            if not text: continue
            vector = await generate_embedding(text)
            emb = MessageEmbedding(message_id=msg.id, embedding=vector, chunk_text=text[:1000])
            session.add(emb)
            stats["processed"] += 1
        except Exception as e:
            logger.error("message_embedding_error", message_id=str(msg.id), error=str(e))
            stats["errors"] += 1
    await session.commit()
    return stats


async def full_reindex(db_name: str | None = None) -> dict:
    """Re-generate all embeddings."""
    from sqlalchemy import delete
    async with get_session(db_name=db_name) as session:
        await session.execute(update(Contact).values(embedding_dirty=True, embedding=None))
        await session.execute(delete(MessageEmbedding))
    
    stats = {"contacts_reindexed": 0, "errors": 0}
    while True:
        result = await maintenance_reindex_dirty(batch_size=50, db_name=db_name)
        stats["contacts_reindexed"] += result["processed"]
        stats["errors"] += result["errors"]
        if result["processed"] == 0: break
    return stats


def _build_contact_profile(contact: Contact) -> str:
    """Build a text profile for embedding generation."""
    parts = []
    if contact.first_name or contact.last_name:
        parts.append(f"Name: {contact.first_name or ''} {contact.last_name or ''}".strip())
    if contact.company: parts.append(f"Company: {contact.company}")
    if contact.position: parts.append(f"Position: {contact.position}")
    if contact.context: parts.append(f"Context: {contact.context}")
    if contact.interests: parts.append(f"Interests: {', '.join(contact.interests)}")
    if contact.skills: parts.append(f"Skills: {', '.join(contact.skills)}")
    if contact.notes: parts.append(f"Notes: {contact.notes}")
    if contact.facts_json:
        for k, v in contact.facts_json.items(): parts.append(f"{k}: {v}")
    return "\n".join(parts)
