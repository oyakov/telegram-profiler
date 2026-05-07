from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.db.models import Contact, Message, VoiceNote, MessageEmbedding
from src.core.config import get_settings
from datetime import datetime
import redis

router = APIRouter(prefix="/stats", tags=["System"])

@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """System health check."""
    checks = {"api": "ok"}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
    
    try:
        import redis as redis_lib
        settings = get_settings()
        r = redis_lib.from_url(settings.redis_url, socket_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    try:
        from src.connectors.audio import AudioProcessor
        processor = AudioProcessor()
        if await processor.health_check(): checks["whisper"] = "ok"
        else: checks["whisper"] = "unavailable"
    except Exception: checks["whisper"] = "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "checks": checks}

@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Dashboard statistics."""
    total_contacts = (await db.execute(select(func.count(Contact.id)))).scalar()
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar()
    total_voice = (await db.execute(select(func.count(VoiceNote.id)))).scalar()

    by_source = await db.execute(
        select(Contact.source, func.count(Contact.id)).group_by(Contact.source)
    )

    return {
        "total_contacts": total_contacts,
        "total_messages": total_messages,
        "total_voice_notes": total_voice,
        "contacts_by_source": {row[0]: row[1] for row in by_source},
    }

@router.get("/stats/distribution")
async def get_distribution_stats(db: AsyncSession = Depends(get_db)):
    """Detailed distribution stats."""
    msg_per_contact = await db.execute(
        select(Contact.first_name, Contact.last_name, Contact.telegram_username, func.count(Message.id).label("msg_count"))
        .join(Message, Message.contact_id == Contact.id)
        .group_by(Contact.id).order_by(text("msg_count DESC")).limit(20)
    )
    contacts_data = [{"name": f"{r[0] or ''} {r[1] or ''}".strip() or f"@{r[2]}" if r[2] else "Unknown", "count": r[3]} for r in msg_per_contact]

    msg_per_channel = await db.execute(
        select(Message.group_id, Message.group_name, func.count(Message.id).label("msg_count"))
        .where(Message.group_id.isnot(None))
        .group_by(Message.group_id, Message.group_name).order_by(text("msg_count DESC")).limit(20)
    )
    channels_data = [{"id": r[0], "name": r[1] or "Unknown Channel", "count": r[2]} for r in msg_per_channel]

    return {"messages_per_contact": contacts_data, "messages_per_channel": channels_data}

@router.get("/ai-monitoring")
async def get_ai_monitoring_stats(db: AsyncSession = Depends(get_db)):
    """AI Extraction monitoring stats."""
    from src.db.models import ExtractionLog
    
    # 1. Total runs and success rate
    total_runs = (await db.execute(select(func.count(ExtractionLog.id)))).scalar() or 0
    success_runs = (await db.execute(select(func.count(ExtractionLog.id)).where(ExtractionLog.success == True))).scalar() or 0
    
    # 2. Token usage
    tokens = (await db.execute(select(
        func.sum(ExtractionLog.prompt_tokens).label("prompt"),
        func.sum(ExtractionLog.completion_tokens).label("completion")
    ))).one_or_none()
    
    prompt_tokens = int(tokens.prompt or 0) if tokens else 0
    completion_tokens = int(tokens.completion or 0) if tokens else 0
    
    # 3. Processing time
    avg_time = (await db.execute(select(func.avg(ExtractionLog.processing_time_ms)))).scalar() or 0
    
    # 4. Success rate over time (last 30 days)
    # This is a bit complex for a single query, but let's just return basic success counts
    
    # Estimating cost (rough estimate for gpt-4o or gemini)
    # Gemini 1.5 Flash is effectively free/very cheap, but let's use a generic 1$ per 1M tokens as illustration
    total_tokens = prompt_tokens + completion_tokens
    estimated_cost_usd = (prompt_tokens / 1_000_000 * 0.15) + (completion_tokens / 1_000_000 * 0.60) # Gemini 1.5 Flash prices
    
    return {
        "total_runs": total_runs,
        "success_rate": (success_runs / total_runs * 100) if total_runs > 0 else 0,
        "total_prompt_tokens": prompt_tokens,
        "total_completion_tokens": completion_tokens,
        "avg_processing_time_ms": int(avg_time),
        "estimated_cost_usd": round(estimated_cost_usd, 4)
    }

@router.get("/embeddings")
async def get_embeddings_stats(db: AsyncSession = Depends(get_db)):
    """Get embedding generation statistics."""
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    messages_with_embeddings = (await db.execute(
        select(func.count(func.distinct(MessageEmbedding.message_id)))
    )).scalar() or 0
    total_embeddings = (await db.execute(select(func.count(MessageEmbedding.id)))).scalar() or 0

    messages_needing_embeddings = total_messages - messages_with_embeddings

    return {
        "total_messages": total_messages,
        "messages_with_embeddings": messages_with_embeddings,
        "messages_needing_embeddings": messages_needing_embeddings,
        "total_embeddings": total_embeddings,
        "progress_percent": round((messages_with_embeddings / total_messages * 100) if total_messages > 0 else 0, 1)
    }

@router.post("/embeddings/reindex")
async def reindex_embeddings_endpoint(db: AsyncSession = Depends(get_db)):
    """Trigger embeddings reindexing via Celery task."""
    from src.pipeline.celery_app import app as celery_app

    task = celery_app.send_task('src.pipeline.tasks.reindex_embeddings', queue='processing')

    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Embeddings reindexing started. Check task status for progress."
    }

@router.get("/workers")
async def get_workers_status():
    """Get Celery workers status."""
    try:
        from celery_app import app as celery_app

        workers_info = celery_app.control.inspect().active()
        workers_stats = celery_app.control.inspect().stats()
        workers_registered = celery_app.control.inspect().registered()

        if not workers_info:
            return {"workers": [], "status": "no_workers"}

        workers = []
        for worker_name, active_tasks in (workers_info or {}).items():
            stats = workers_stats.get(worker_name, {}) if workers_stats else {}
            registered_tasks = workers_registered.get(worker_name, []) if workers_registered else []

            workers.append({
                "name": worker_name,
                "status": "online",
                "active_tasks": len(active_tasks),
                "tasks": active_tasks[:5],
                "pool": stats.get("pool", {}).get("implementation", "unknown"),
                "max_concurrency": stats.get("pool", {}).get("max-concurrency", 0),
                "processes": stats.get("pool", {}).get("processes", []),
                "registered_tasks_count": len(registered_tasks)
            })

        return {"workers": workers, "status": "ok", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"workers": [], "status": "error", "error": str(e)}
