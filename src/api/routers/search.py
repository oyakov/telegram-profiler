from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Contact, MessageEmbedding
from src.api.schemas import SearchRequest
from src.api.routers.contacts import _contact_to_response

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("")
async def semantic_search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """Semantic search across contacts and messages using embeddings."""
    from src.ai.embeddings import generate_embedding

    query_embedding = await generate_embedding(req.query)

    # 1. Search contacts
    contact_results = await db.execute(
        select(Contact, Contact.embedding.cosine_distance(query_embedding).label("distance"))
        .where(Contact.embedding.isnot(None))
        .order_by("distance")
        .limit(req.limit)
    )

    contacts = []
    for contact, distance in contact_results:
        contacts.append({
            **_contact_to_response(contact),
            "similarity": round(1 - distance, 4),
        })

    # 2. Search messages
    from src.db.models import Message
    import sqlalchemy as sa
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

