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

router = APIRouter(prefix="/search", tags=["Search"])


def _contact_to_response(contact):
    return ContactService.map_to_response(contact)


def _normalize_text(t: str) -> str:
    return t.lower().strip()


def _rrf_score(ranks: list[int | None], k: int = 60) -> float:
    return sum(1 / (k + r) for r in ranks if r is not None)


async def _message_keyword_search(
    db: AsyncSession,
    query: str,
    limit: int,
) -> list[tuple]:
    """Per-keyword message search on personal contacts only, coverage-first ranking."""
    keywords = [w for w in _normalize_text(query).split() if len(w) >= 3]
    if not keywords:
        return []

    per_kw: list[dict] = []
    for kw in keywords:
        q = (
            select(Message.contact_id, func.count(Message.id).label("cnt"))
            .join(Contact, Contact.id == Message.contact_id)
            .where(Contact.is_personal == True)  # noqa: E712
            .where(Message.content.isnot(None))
            .where(Message.content.ilike(f"%{kw}%"))
            .group_by(Message.contact_id)
            .order_by(text("cnt DESC"))
            .limit(limit * 6)
        )
        rows = await db.execute(q)
        per_kw.append({cid: cnt for cid, cnt in rows.all()})

    all_ids: set = set()
    for kw_map in per_kw:
        all_ids |= kw_map.keys()

    scored: list[tuple] = []
    for cid in all_ids:
        kw_coverage = sum(1 for kw_map in per_kw if cid in kw_map)
        total_mentions = sum(kw_map.get(cid, 0) for kw_map in per_kw)
        scored.append((cid, kw_coverage, total_mentions))

    scored.sort(key=lambda x: (-x[1], -x[2]))
    return [(cid, kw_cov * 10000 + mentions) for cid, kw_cov, mentions in scored[:limit]]


@router.post("")
async def semantic_search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """Hybrid search: semantic (IVFFlat) + per-keyword on personal contacts only.

    Channels/bots are excluded by filtering Contact.is_personal == True,
    which is O(1) vs the previous O(n) GROUP BY over 2.8M messages.
    Falls back to keyword-only mode when the embedding provider is unavailable.
    """
    import sqlalchemy as sa
    import logging
    logger = logging.getLogger(__name__)

    query_embedding = None
    try:
        from src.ai.providers.factory import get_embedding_provider
        # 8-second HTTP timeout — if LMStudio is busy with a worker batch we fall back
        # to keyword-only rather than blocking the search request indefinitely.
        _provider = get_embedding_provider(timeout=8.0)
        query_embedding = await _provider.generate_embedding(req.query)
        await db.execute(sa.text("SET LOCAL ivfflat.probes = 10"))
    except Exception as emb_err:
        logger.warning("Embedding generation failed, falling back to keyword-only search: %s", emb_err)

    # ── 1. Semantic search over personal-contact message embeddings ───────────
    # Only ~200 embeddings belong to personal contacts; IVFFlat scan is instant.
    semantic_contacts: dict = {}
    if query_embedding is not None:
        sem_q = (
            select(
                MessageEmbedding.id,
                MessageEmbedding.message_id,
                MessageEmbedding.chunk_text,
                Message.contact_id,
                Message.content,
                MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .join(Message, Message.id == MessageEmbedding.message_id)
            .join(Contact, Contact.id == Message.contact_id)
            .where(Contact.is_personal == True)  # noqa: E712
            .order_by("distance")
            .limit(req.limit * settings.search_row_limit_multiplier)
        )

        msg_rows = (await db.execute(sem_q)).fetchall()

        sem_contact_ids = list({r.contact_id for r in msg_rows if r.distance < settings.search_semantic_threshold})
        sem_contact_map: dict = {}
        if sem_contact_ids:
            c_rows = await db.execute(select(Contact).where(Contact.id.in_(sem_contact_ids)))
            for (c,) in c_rows:
                sem_contact_map[c.id] = c

        for r in msg_rows:
            if r.distance >= settings.search_semantic_threshold:
                continue
            contact = sem_contact_map.get(r.contact_id)
            if not contact:
                continue
            cid = contact.id
            evidence_item = {
                "text": (r.chunk_text or r.content or "").strip()[:300],
                "relevance": round(1 - r.distance, 3),
            }
            if cid not in semantic_contacts:
                semantic_contacts[cid] = (contact, r.distance, [evidence_item])
            else:
                existing_contact, best_dist, ev_list = semantic_contacts[cid]
                if len(ev_list) < 3:
                    ev_list.append(evidence_item)
                if r.distance < best_dist:
                    semantic_contacts[cid] = (existing_contact, r.distance, ev_list)

    # ── 2. Per-keyword message search (personal contacts only) ────────────────
    kw_msg_rows = await _message_keyword_search(db, req.query, req.limit * 3)
    kw_msg_rank: dict = {
        contact_id: rank for rank, (contact_id, _) in enumerate(kw_msg_rows)
    }

    # ── 3. RRF merge ──────────────────────────────────────────────────────────
    semantic_ranked = sorted(semantic_contacts.keys(), key=lambda cid: semantic_contacts[cid][1])
    semantic_rank: dict = {cid: rank for rank, cid in enumerate(semantic_ranked)}

    all_candidate_ids = set(semantic_contacts.keys()) | set(kw_msg_rank.keys())
    rrf_scores: dict = {
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

    # ── 5. Evidence snippets for keyword-only contacts ────────────────────────
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

    # ── 7. Top matching messages (personal contacts, no embedding vector fetched)
    messages = []
    if query_embedding is not None:
        msg_q = (
            select(
                MessageEmbedding.message_id,
                MessageEmbedding.chunk_text,
                Message.content,
                Message.group_name,
                Message.timestamp,
                Message.contact_id,
                MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .join(Message, Message.id == MessageEmbedding.message_id)
            .join(Contact, Contact.id == Message.contact_id)
            .where(Contact.is_personal == True)  # noqa: E712
            .order_by("distance")
            .limit(req.limit)
        )

        raw_msg_rows = (await db.execute(msg_q)).fetchall()
        msg_contact_ids_needed = list({r.contact_id for r in raw_msg_rows if r.contact_id})
        msg_contact_map: dict = {}
        if msg_contact_ids_needed:
            mc_rows = await db.execute(
                select(Contact.id, Contact.first_name, Contact.last_name)
                .where(Contact.id.in_(msg_contact_ids_needed))
            )
            for cid, fn, ln in mc_rows:
                msg_contact_map[cid] = f"{fn or ''} {ln or ''}".strip() or "Неизвестно"

        for r in raw_msg_rows:
            messages.append({
                "message_id": str(r.message_id),
                "content": r.content,
                "group_name": r.group_name,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "contact_name": msg_contact_map.get(r.contact_id, "Неизвестно"),
                "similarity": round(1 - r.distance, 4),
            })

    return {
        "query": req.query,
        "search_mode": "hybrid" if query_embedding is not None else "keyword_only",
        "contacts": contacts,
        "messages": messages,
    }
