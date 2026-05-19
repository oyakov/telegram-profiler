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

# Contacts with more messages than this threshold are likely channels/bots,
# not individual people. Exclude them from person-targeted contact search.
CHANNEL_MSG_THRESHOLD = 5_000

def _contact_to_response(contact):
    return ContactService.map_to_response(contact)

router = APIRouter(prefix="/search", tags=["Search"])


def _normalize_text(t: str) -> str:
    return t.lower().strip()


def _rrf_score(ranks: list[int | None], k: int = 60) -> float:
    return sum(1 / (k + r) for r in ranks if r is not None)


def _channel_subquery():
    """Subquery: contact_ids that are high-volume channels/bots."""
    return (
        select(Message.contact_id)
        .group_by(Message.contact_id)
        .having(func.count(Message.id) > CHANNEL_MSG_THRESHOLD)
        .scalar_subquery()
    )


async def _message_keyword_search(
    db: AsyncSession,
    query: str,
    limit: int,
) -> list[tuple]:
    """Per-keyword message search with coverage-first ranking.

    Contacts matching ALL keywords rank above those matching only some.
    High-volume channel contacts are excluded via subquery filter.
    """
    keywords = [w for w in _normalize_text(query).split() if len(w) >= 3]
    if not keywords:
        return []

    channel_sq = _channel_subquery()
    per_kw: list[dict[int, int]] = []
    for kw in keywords:
        q = (
            select(Message.contact_id, func.count(Message.id).label("cnt"))
            .where(Message.content.isnot(None))
            .where(Message.content.ilike(f"%{kw}%"))
            .where(Message.contact_id.not_in(channel_sq))
            .group_by(Message.contact_id)
            .order_by(text("cnt DESC"))
            .limit(limit * 6)
        )
        rows = await db.execute(q)
        per_kw.append({cid: cnt for cid, cnt in rows.all()})

    all_ids: set[int] = set()
    for kw_map in per_kw:
        all_ids |= kw_map.keys()

    scored: list[tuple[int, int, int]] = []
    for cid in all_ids:
        kw_coverage = sum(1 for kw_map in per_kw if cid in kw_map)
        total_mentions = sum(kw_map.get(cid, 0) for kw_map in per_kw)
        scored.append((cid, kw_coverage, total_mentions))

    scored.sort(key=lambda x: (-x[1], -x[2]))
    return [(cid, kw_cov * 10000 + mentions) for cid, kw_cov, mentions in scored[:limit]]


async def _keyword_search(db: AsyncSession, query: str, limit: int) -> list[tuple]:
    """Keyword search in contact profile fields (name, company, position)."""
    keywords = _normalize_text(query).split()
    like_conditions = [
        or_(
            Contact.first_name.ilike(f"%{kw}%"),
            Contact.last_name.ilike(f"%{kw}%"),
            Contact.company.ilike(f"%{kw}%"),
            Contact.position.ilike(f"%{kw}%"),
        )
        for kw in keywords
    ]
    rows = await db.execute(
        select(Contact, func.count(Message.id).label("msg_count"))
        .outerjoin(Message, Message.contact_id == Contact.id)
        .where(and_(*like_conditions) if like_conditions else True)
        .group_by(Contact.id)
        .order_by(text("msg_count DESC"))
        .limit(limit)
    )
    return rows.fetchall()


@router.post("")
async def semantic_search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """Hybrid search: semantic + per-keyword message search with RRF merge.

    News channels and bots are excluded from results via message-count threshold.
    Semantic results are kept dominant; keyword results fill gaps.
    """
    from src.ai.analysis import generate_embedding
    import sqlalchemy as sa

    query_embedding = await generate_embedding(req.query)
    await db.execute(sa.text("SET LOCAL hnsw.ef_search = 100"))

    channel_sq = _channel_subquery()

    # ── 1. Semantic search in message embeddings (channels excluded) ──────────
    sem_q = (
        select(
            MessageEmbedding,
            Message,
            MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Message, Message.id == MessageEmbedding.message_id)
        .options(sa.orm.joinedload(Message.contact))
        .where(Message.contact_id.not_in(channel_sq))
        .order_by("distance")
        .limit(req.limit * settings.search_row_limit_multiplier)
    )

    msg_results = await db.execute(sem_q)

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

    # ── 2. Per-keyword message search (channels excluded via subquery) ────────
    kw_msg_rows = await _message_keyword_search(db, req.query, req.limit * 3)
    kw_msg_rank: dict[int, int] = {
        contact_id: rank for rank, (contact_id, _) in enumerate(kw_msg_rows)
    }

    # ── 3. Pure RRF merge (no demotion — let evidence quality speak) ──────────
    semantic_ranked = sorted(semantic_contacts.keys(), key=lambda cid: semantic_contacts[cid][1])
    semantic_rank: dict[int, int] = {cid: rank for rank, cid in enumerate(semantic_ranked)}

    all_candidate_ids = set(semantic_contacts.keys()) | set(kw_msg_rank.keys())
    rrf_scores: dict[int, float] = {
        cid: _rrf_score([semantic_rank.get(cid), kw_msg_rank.get(cid)])
        for cid in all_candidate_ids
    }

    top_ids = sorted(all_candidate_ids, key=lambda cid: -rrf_scores[cid])[:req.limit]

    # ── 4. Fetch contact objects for keyword-only candidates ──────────────────
    kw_only_ids = [cid for cid in top_ids if cid not in semantic_contacts]
    kw_contact_map: dict = {}
    if kw_only_ids:
        rows = await db.execute(select(Contact).where(Contact.id.in_(kw_only_ids)))
        for (contact,) in rows:
            kw_contact_map[contact.id] = contact

    # ── 5. Evidence for keyword-only contacts: relevant messages (not just latest)
    kw_evidence: dict = defaultdict(list)
    if kw_only_ids:
        keywords = [w for w in _normalize_text(req.query).split() if len(w) >= 3]
        like_conds = [Message.content.ilike(f"%{kw}%") for kw in keywords] if keywords else []
        ev_q = (
            select(Message.contact_id, Message.content)
            .where(Message.contact_id.in_(kw_only_ids))
            .where(Message.content.isnot(None), Message.content != "")
        )
        if like_conds:
            ev_q = ev_q.where(or_(*like_conds))
        ev_q = ev_q.order_by(Message.contact_id).limit(len(kw_only_ids) * 5)
        for cid, content in (await db.execute(ev_q)):
            if len(kw_evidence[cid]) < 3:
                kw_evidence[cid].append({"text": content.strip()[:300], "relevance": None})

    # ── 6. Assemble final contact list ────────────────────────────────────────
    contacts = []
    for cid in top_ids:
        if cid in semantic_contacts:
            contact, best_dist, ev_list = semantic_contacts[cid]
            in_kw = cid in kw_msg_rank
            contacts.append({
                **_contact_to_response(contact),
                "similarity": round(min(1.0, (1 - best_dist) * (1.05 if in_kw else 1.0)), 4),
                "evidence": ev_list,
                "search_type": "semantic",
            })
        elif cid in kw_contact_map:
            contact = kw_contact_map[cid]
            contacts.append({
                **_contact_to_response(contact),
                "similarity": settings.search_keyword_fallback_relevance,
                "evidence": kw_evidence.get(cid, []),
                "search_type": "keyword",
            })

    # ── 7. Search individual messages ─────────────────────────────────────────
    msg_q = (
        select(
            MessageEmbedding,
            Message,
            MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Message, Message.id == MessageEmbedding.message_id)
        .options(sa.orm.joinedload(Message.contact))
        .where(Message.contact_id.not_in(channel_sq))
        .order_by("distance")
        .limit(req.limit)
    )

    messages = []
    for me, msg, distance in (await db.execute(msg_q)):
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
