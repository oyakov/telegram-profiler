from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Message, Contact, MessageContact

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.get("/search")
async def search_messages(
    query: Optional[str] = Query(None),
    contact_id: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
    group_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_channel: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Keyword search and filtering for messages."""
    stmt = select(Message)
    
    # Filtering by user (either via UUID or Telegram ID)
    if contact_id or telegram_id:
        # Join with MessageContact to find messages where the user is involved
        stmt = stmt.join(Message.associated_contacts)
        if contact_id:
            stmt = stmt.where(MessageContact.contact_id == contact_id)
        if telegram_id:
            stmt = stmt.join(MessageContact.contact)
            stmt = stmt.where(Contact.telegram_id == telegram_id)
        if role:
            stmt = stmt.where(MessageContact.role == role)

    if query:
        stmt = stmt.where(Message.content.ilike(f"%{query}%"))
    if group_id:
        stmt = stmt.where(Message.group_id == group_id)
    if is_channel is True:
        stmt = stmt.where(Message.raw_json["is_channel"].as_boolean() == True)
    elif is_channel is False:
        stmt = stmt.where(
            or_(
                Message.raw_json["is_channel"].as_boolean() == False,
                Message.raw_json["is_channel"].is_(None)
            )
        )
        
    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0
    
    stmt = stmt.order_by(Message.timestamp.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(stmt.options(sa.orm.joinedload(Message.contact)))
    messages = result.scalars().all()
    
    return {
        "messages": [
            {
                "id": str(m.id),
                "contact_id": str(m.contact_id),
                "contact_name": f"{m.contact.first_name or ''} {m.contact.last_name or ''}".strip(),
                "source": m.source,
                "direction": m.direction,
                "content": m.content,
                "media_type": m.media_type,
                "group_id": m.group_id,
                "group_name": m.group_name,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "raw_json": m.raw_json,
            }
            for m in messages
        ],
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


# Also move the contact-specific messages here, but keep the prefix consistent with main.py if needed.
# Actually, I can mount this router and also have a specific endpoint in contacts.py that delegates to this.
# But for now, let's just keep it simple.
@router.get("/contact/{contact_id}")
async def get_contact_messages(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get interaction history for a contact (all roles)."""
    query = (
        select(Message)
        .join(Message.associated_contacts)
        .where(MessageContact.contact_id == contact_id)
        .order_by(Message.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    return {
        "messages": [
            {
                "id": str(m.id),
                "source": m.source,
                "direction": m.direction,
                "content": m.content,
                "media_type": m.media_type,
                "group_name": m.group_name,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in messages
        ],
        "page": page,
        "page_size": page_size
    }
