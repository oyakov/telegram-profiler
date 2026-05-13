from __future__ import annotations
import structlog
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Message, MessageContact, Contact

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
