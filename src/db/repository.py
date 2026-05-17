from __future__ import annotations
import structlog
from typing import List, Optional, Union
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Message, MessageContact, Contact, ExtractionLog, ChannelSyncState, SyncBatchLog, SyncState, Campaign, CampaignMessage, LeadSearch

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

    async def bulk_save_messages(self, messages_data: List[dict]) -> List[Message]:
        """Bulk upsert messages using ON CONFLICT."""
        if not messages_data:
            return []
            
        from sqlalchemy.dialects.postgresql import insert
        
        stmt = insert(Message).values(messages_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Message.source_message_id],
            set_={
                "content": stmt.excluded.content,
                "updated_at": datetime.now(timezone.utc)
            }
        ).returning(Message)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ContactRepository:
    """Repository for managing Contact operations and deduplication."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert_contacts(self, contacts_data: List[dict]) -> List[Contact]:
        """Bulk upsert contacts based on telegram_id or email."""
        if not contacts_data:
            return []
            
        from sqlalchemy.dialects.postgresql import insert
        
        stmt = insert(Contact).values(contacts_data)
        # We assume telegram_id is the primary unique identifier for sync
        stmt = stmt.on_conflict_do_update(
            index_elements=[Contact.telegram_id],
            set_={
                "first_name": stmt.excluded.first_name,
                "last_name": stmt.excluded.last_name,
                "telegram_username": stmt.excluded.telegram_username,
                "updated_at": datetime.now(timezone.utc)
            }
        ).returning(Contact)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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


class SyncStateRepository:
    """Repository for managing sync states and batch logs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_connector_state(self, connector_name: str) -> SyncState:
        """Get or create the global sync state for a connector."""
        result = await self.session.execute(
            select(SyncState).where(SyncState.connector == connector_name)
        )
        state = result.scalar_one_or_none()
        if not state:
            state = SyncState(connector=connector_name, status="idle")
            self.session.add(state)
            await self.session.flush()
        return state

    async def update_eta(self, sync_state: ChannelSyncState) -> None:
        """Calculate and update ETA and sync rate for an active sync."""
        if sync_state.started_at and sync_state.estimated_total_messages:
            elapsed = datetime.now(timezone.utc) - sync_state.started_at
            elapsed_seconds = elapsed.total_seconds()

            if elapsed_seconds > 0:
                # Calculate rate (messages per second)
                rate = sync_state.messages_synced / elapsed_seconds

                if rate > 0:
                    remaining = sync_state.estimated_total_messages - sync_state.messages_synced
                    eta_seconds = remaining / rate

                    sync_state.eta_minutes = int(eta_seconds / 60)
                    sync_state.estimated_completion = (
                        datetime.now(timezone.utc) + timedelta(seconds=eta_seconds)
                    )
        
    async def get_active_syncs(self) -> List[ChannelSyncState]:
        """Get all sync states currently in progress."""
        result = await self.session.execute(
            select(ChannelSyncState).where(
                ChannelSyncState.phase.in_(["metadata", "syncing"])
            )
        )
        return list(result.scalars().all())

    async def get_pending_batches(self, sync_state_id: UUID) -> List[SyncBatchLog]:
        """Get batches that are pending or running for a given sync."""
        result = await self.session.execute(
            select(SyncBatchLog).where(
                and_(
                    SyncBatchLog.sync_state_id == sync_state_id,
                    SyncBatchLog.status.in_(["pending", "processing", "running"])
                )
            )
        )
        return list(result.scalars().all())

    async def get_failed_batches(self, limit: int = 10) -> List[SyncBatchLog]:
        """Get recently failed batches for retry."""
        result = await self.session.execute(
            select(SyncBatchLog).where(
                and_(
                    SyncBatchLog.status == "failed",
                    SyncBatchLog.retry_attempt < 3
                )
            ).order_by(SyncBatchLog.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class CampaignRepository:
    """Repository for managing marketing Campaigns and Messages."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_pending_messages(self, campaign_id: UUID, limit: int = 100) -> List[CampaignMessage]:
        """Get pending messages for a campaign."""
        result = await self.session.execute(
            select(CampaignMessage)
            .where(
                and_(
                    CampaignMessage.campaign_id == campaign_id,
                    CampaignMessage.status == "pending"
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())


class LeadSearchRepository:
    """Repository for managing Lead Searches and contact filtering."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_matching_contacts(self, profile_filter: dict, limit: int = 200) -> List[Contact]:
        """Find contacts matching a complex profile filter."""
        stmt = select(Contact).where(Contact.is_lead == True)
        
        if profile_filter.get("first_name"):
            stmt = stmt.where(Contact.first_name.ilike(f"%{profile_filter['first_name']}%"))
        if profile_filter.get("last_name"):
            stmt = stmt.where(Contact.last_name.ilike(f"%{profile_filter['last_name']}%"))
        if profile_filter.get("company"):
            stmt = stmt.where(Contact.company.ilike(f"%{profile_filter['company']}%"))
        if profile_filter.get("position"):
            stmt = stmt.where(Contact.position.ilike(f"%{profile_filter['position']}%"))
        if profile_filter.get("min_lead_score") is not None:
            stmt = stmt.where(Contact.lead_score >= profile_filter["min_lead_score"])

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
