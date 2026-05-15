"""Unified processing pipeline — orchestrates extraction, deduplication, and lead scoring."""

from __future__ import annotations

import asyncio
import structlog
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Union

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.services import ExtractionService
from src.ai.schemas import ContactExtraction, LeadExtraction
from src.ai.analysis import generate_embedding, generate_embeddings_batch
from src.core.config import SettingsService
from src.db.database import get_session
from src.db.models import Contact, ExtractionLog, Message, MessageEmbedding, MessageContact
from src.db.repository import ContactRepository

logger = structlog.get_logger()


class MessageProcessor:
    """Unified processor for incoming messages from all sources."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ai_service = ExtractionService()
        self.contact_repo = ContactRepository(session)
        self.settings_svc = SettingsService(session)

    async def process_batch(self, messages: list[Message], force_lead_detection: bool = False) -> dict:
        """Process a batch of messages concurrently.
        LLM extraction runs in parallel; DB writes are serialised to avoid race conditions.
        """
        stats = {"processed": 0, "contacts_found": 0, "leads_found": 0, "errors": 0}

        semaphore = asyncio.Semaphore(5)
        lead_threshold = await self.settings_svc.get("extraction_lead_confidence_threshold", 0.6)

        # Phase 1: run all LLM extractions concurrently (no DB writes here)
        async def _extract_single(msg: Message):
            async with semaphore:
                if not msg.content or len(msg.content.strip()) < 10:
                    return None
                try:
                    is_channel = msg.raw_json.get("is_channel", False) if msg.raw_json else False
                    contacts, _ = await self.ai_service.extract(
                        msg.content,
                        extraction_type="contacts",
                        source_context=f"Group: {msg.group_name or 'Unknown'}"
                    )
                    leads = []
                    if is_channel or force_lead_detection:
                        leads, _ = await self.ai_service.extract(
                            msg.content,
                            extraction_type="leads",
                            source_context=f"Group: {msg.group_name or 'Unknown'}"
                        )
                    return msg, contacts, leads, is_channel
                except Exception as e:
                    logger.error("unified_message_extraction_error", message_id=str(msg.id), error=str(e))
                    stats["errors"] += 1
                    return None

        extraction_results = await asyncio.gather(*[_extract_single(msg) for msg in messages])

        # Phase 2: apply DB writes sequentially to eliminate concurrent JSONB mutations
        for result in extraction_results:
            if result is None:
                continue
            msg, contacts, leads, is_channel = result
            try:
                for c_data in contacts:
                    contact = await self._sync_contact(c_data)
                    if contact:
                        stats["contacts_found"] += 1
                        if not is_channel:
                            msg.contact_id = contact.id

                for l_data in leads:
                    if l_data.confidence < lead_threshold:
                        continue
                    contact = await self._sync_lead(l_data, msg)
                    if contact:
                        stats["leads_found"] += 1

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

            except Exception as e:
                logger.error("unified_message_processing_error", message_id=str(msg.id), error=str(e))
                stats["errors"] += 1

        await self.session.flush()
        return stats

    async def _sync_contact(self, extraction: ContactExtraction) -> Optional[Contact]:
        """Deduplicate and sync contact data."""
        contact = await self.contact_repo.find_duplicate(
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
            self.contact_repo.merge_contact_fields(contact, extraction.model_dump(exclude_none=True))
        
        return contact

    async def _sync_lead(self, lead_data: LeadExtraction, original_msg: Message) -> Optional[Contact]:
        """Update or create a contact based on detected lead data."""
        contact = await self.contact_repo.find_duplicate(
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
    import sqlalchemy as sa
    already_processed = (
        select(ExtractionLog.id)
        .where(ExtractionLog.source_type == "unified_message")
        .where(ExtractionLog.source_id == Message.id.cast(sa.String))
        .correlate(Message)
        .exists()
    )
    query = (
        select(Message)
        .where(~already_processed)
        .where(Message.content.isnot(None))
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
    logger.info("maintenance_index_messages_called", batch_size=batch_size, db_name=db_name, has_session=session is not None)
    if session is None:
        logger.info("creating_new_session", db_name=db_name)
        async with get_session(db_name=db_name) as new_session:
            result = await _maintenance_index_messages_impl(new_session, batch_size)
            logger.info("maintenance_index_messages_result", result=result, db_name=db_name)
            return result
    return await _maintenance_index_messages_impl(session, batch_size)


async def _maintenance_index_messages_impl(session: AsyncSession, batch_size: int) -> dict:
    from datetime import datetime, timezone
    import redis.asyncio as aioredis
    from src.core.config import get_settings

    stats = {"processed": 0, "errors": 0, "tokens": 0}
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
    if not messages:
        logger.info("no_messages_to_embed")
        return stats

    # Setup async Redis for metrics tracking
    r = None
    tokens_key = requests_key = None
    try:
        settings = get_settings()
        r = aioredis.from_url(settings.redis_url, socket_timeout=2)
        minute_key = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        tokens_key = f"embeddings:tokens:{minute_key}"
        requests_key = f"embeddings:requests:{minute_key}"
    except Exception as e:
        logger.warning("redis_tracking_unavailable", error=str(e))
        r = None

    # Prepare texts for batch embedding
    texts = [msg.content.strip() for msg in messages if msg.content and msg.content.strip()]
    if not texts:
        if r:
            await r.aclose()
        return stats

    try:
        vectors = await generate_embeddings_batch(texts)

        for msg, vector in zip(messages, vectors):
            emb = MessageEmbedding(message_id=msg.id, embedding=vector, chunk_text=msg.content[:1000])
            session.add(emb)
            stats["processed"] += 1

            estimated_tokens = max(1, len(msg.content) // 4)
            stats["tokens"] += estimated_tokens

            if r:
                try:
                    await r.incr(tokens_key, estimated_tokens)
                    await r.incr(requests_key, 1)
                    await r.expire(tokens_key, 3600)
                    await r.expire(requests_key, 3600)
                except Exception:
                    pass

    except Exception as e:
        logger.error("batch_embedding_error", error=str(e))
        stats["errors"] += len(messages)
    finally:
        if r:
            await r.aclose()

    logger.info("embeddings_before_commit", processed=stats["processed"], errors=stats["errors"], tokens=stats["tokens"])
    try:
        await session.commit()
        logger.info("embeddings_commit_success", processed=stats["processed"], tokens=stats["tokens"])
    except Exception as e:
        logger.error("embeddings_commit_failed", error=str(e))
        raise

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
