from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from src.db.database import get_db
from src.db.models import Contact, MessageEmbedding, Message
from src.api.schemas import SearchRequest
from src.api.routers.contacts import _contact_to_response

router = APIRouter(prefix="/search", tags=["Search"])


async def _extract_evidence_for_contact(
    db: AsyncSession,
    contact_id,
    query_embedding: list[float],
    max_quotes: int = 3,
) -> list[dict]:
    """Extract top N most relevant message quotes for a contact."""
    results = await db.execute(
        select(
            MessageEmbedding.chunk_text,
            MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Message, Message.id == MessageEmbedding.message_id)
        .where(Message.contact_id == contact_id)
        .where(MessageEmbedding.chunk_text.isnot(None))
        .order_by("distance")
        .limit(max_quotes)
    )

    quotes = []
    for chunk_text, distance in results:
        if chunk_text and chunk_text.strip():
            quotes.append({
                "text": chunk_text.strip()[:200],  # Truncate to 200 chars
                "relevance": round(1 - distance, 3),
            })

    return quotes


@router.post("")
async def semantic_search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """Semantic search across contacts and messages using embeddings."""
    from src.ai.analysis import generate_embedding
    import sqlalchemy as sa

    query_embedding = await generate_embedding(req.query)

    # 1. Search contacts with evidence
    contact_results = await db.execute(
        select(Contact, Contact.embedding.cosine_distance(query_embedding).label("distance"))
        .where(Contact.embedding.isnot(None))
        .order_by("distance")
        .limit(req.limit)
    )

    contacts = []
    for contact, distance in contact_results:
        # Extract evidence quotes for this contact
        evidence = await _extract_evidence_for_contact(db, contact.id, query_embedding)

        contacts.append({
            **_contact_to_response(contact),
            "similarity": round(1 - distance, 4),
            "evidence": evidence,
        })

    # 2. Search messages
    msg_results = await db.execute(
        select(
            MessageEmbedding,
            Message,
            MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Message, Message.id == MessageEmbedding.message_id)
        .options(sa.orm.joinedload(Message.contact))
        .order_by("distance")
        .limit(req.limit)
    )

    messages = []
    for me, msg, distance in msg_results:
        messages.append({
            "message_id": str(me.message_id),
            "content": msg.content,
            "group_name": msg.group_name,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
            "contact_name": f"{msg.contact.first_name or ''} {msg.contact.last_name or ''}".strip() if msg.contact else "Неизвестно",
            "similarity": round(1 - distance, 4),
        })

    return {
        "query": req.query,
        "contacts": contacts,
        "messages": messages,
    }

