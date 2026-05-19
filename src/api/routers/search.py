from fastapi import APIRouter, Depends
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from src.db.database import get_db
from src.db.models import Contact, MessageEmbedding, Message
from src.api.schemas import SearchRequest
from src.services.contact_service import ContactService
from src.core.config import get_settings

settings = get_settings()

def _contact_to_response(contact):
    return ContactService.map_to_response(contact)

router = APIRouter(prefix="/search", tags=["Search"])


def _normalize_text(text: str) -> str:
    """Normalize text for keyword search."""
    return text.lower().strip()


async def _extract_evidence_batch(
    db: AsyncSession,
    contact_ids: list,
    query_embedding: list[float],
    max_quotes: int = 3,
) -> dict:
    """Extract top N most relevant message quotes for multiple contacts (batch load)."""
    # Cap results: max_quotes per contact, hard ceiling to avoid unbounded scans
    row_limit = len(contact_ids) * max_quotes * 4  # 4× overshot to allow filtering
    results = await db.execute(
        select(
            Message.contact_id,
            MessageEmbedding.chunk_text,
            MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Message, Message.id == MessageEmbedding.message_id)
        .where(Message.contact_id.in_(contact_ids))
        .where(MessageEmbedding.chunk_text.isnot(None))
        .order_by(Message.contact_id, "distance")
        .limit(row_limit)
    )

    evidence_by_contact = defaultdict(list)
    for contact_id, chunk_text, distance in results:
        if chunk_text and chunk_text.strip() and len(evidence_by_contact[contact_id]) < max_quotes:
            evidence_by_contact[contact_id].append({
                "text": chunk_text.strip()[:200],
                "relevance": round(1 - distance, 3),
            })

    return dict(evidence_by_contact)


async def _keyword_search(db: AsyncSession, query: str, limit: int) -> list[tuple]:
    """Keyword search in contacts and messages."""
    query_normalized = _normalize_text(query)
    keywords = query_normalized.split()

    # Build dynamic LIKE conditions for all keywords
    like_conditions = []
    for kw in keywords:
        like_conditions.append(
            or_(
                Contact.first_name.ilike(f"%{kw}%"),
                Contact.last_name.ilike(f"%{kw}%"),
                Contact.company.ilike(f"%{kw}%"),
                Contact.position.ilike(f"%{kw}%"),
            )
        )

    results = await db.execute(
        select(
            Contact,
            func.count(Message.id).label("msg_count")
        )
        .outerjoin(Message, Message.contact_id == Contact.id)
        .where(and_(*like_conditions) if like_conditions else True)
        .group_by(Contact.id)
        .order_by(text("msg_count DESC"))
        .limit(limit)
    )

    return results.fetchall()


@router.post("")
async def semantic_search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """Hybrid search: semantic + keyword."""
    from src.ai.analysis import generate_embedding
    import sqlalchemy as sa

    query_embedding = await generate_embedding(req.query)

    # Raise HNSW ef_search from default 40 → 100 for better recall at 2M+ embeddings.
    # This runs per-query and is cheap (no lock, session-local).
    await db.execute(sa.text("SET LOCAL hnsw.ef_search = 100"))

    # 1. Semantic search in messages - increased threshold for better recall
    msg_results = await db.execute(
        select(
            MessageEmbedding,
            Message,
            MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Message, Message.id == MessageEmbedding.message_id)
        .options(sa.orm.joinedload(Message.contact))
        .order_by("distance")
        .limit(req.limit * settings.search_row_limit_multiplier)
    )

    # contact_id → (contact, best_distance, [evidence_items])
    semantic_contacts: dict = {}
    for me, msg, distance in msg_results:
        if not msg.contact or distance >= settings.search_semantic_threshold:
            continue
        cid = msg.contact.id
        evidence_item = {
            "text": (me.chunk_text or msg.content or "").strip()[:300],
            "relevance": round(1 - distance, 3),
        }
        if cid not in semantic_contacts:
            semantic_contacts[cid] = (msg.contact, distance, [evidence_item])
        else:
            contact, best_dist, ev_list = semantic_contacts[cid]
            if len(ev_list) < 3:
                ev_list.append(evidence_item)
            if distance < best_dist:
                semantic_contacts[cid] = (contact, distance, ev_list)

    # 2. Keyword search as fallback
    keyword_contacts = {}
    if len(semantic_contacts) < req.limit:
        kw_results = await _keyword_search(db, req.query, req.limit * 2)
        for contact, msg_count in kw_results:
            if contact.id not in semantic_contacts:
                keyword_contacts[contact.id] = (contact, None, settings.search_keyword_fallback_relevance)

    # 3. Combine + build keyword evidence (recent messages)
    all_contacts = {}
    for contact_id, (contact, best_dist, ev_list) in semantic_contacts.items():
        all_contacts[contact_id] = (contact, best_dist, "semantic", ev_list)

    if keyword_contacts:
        kw_ids = [cid for cid in keyword_contacts if cid not in all_contacts]
        if kw_ids:
            kw_msgs = await db.execute(
                select(Message.contact_id, Message.content)
                .where(Message.contact_id.in_(kw_ids))
                .where(Message.content.isnot(None), Message.content != "")
                .order_by(Message.contact_id, Message.timestamp.desc())
                .limit(len(kw_ids) * 3)
            )
            kw_evidence: dict = defaultdict(list)
            for cid, content in kw_msgs:
                if len(kw_evidence[cid]) < 3:
                    kw_evidence[cid].append({"text": content.strip()[:300], "relevance": None})
        for contact_id, (contact, _, fallback_dist) in keyword_contacts.items():
            if contact_id not in all_contacts:
                all_contacts[contact_id] = (contact, fallback_dist, "keyword", kw_evidence.get(contact_id, []))

    # 4. Build final contact list
    contact_list = list(all_contacts.values())[:req.limit]
    contacts = []
    for contact, distance, search_type, ev_list in contact_list:
        contacts.append({
            **_contact_to_response(contact),
            "similarity": round(1 - distance, 4) if search_type == "semantic" else 0.5,
            "evidence": ev_list,
            "search_type": search_type,
        })

    # 6. Search individual messages
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

