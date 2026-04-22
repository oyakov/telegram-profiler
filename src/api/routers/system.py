from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.db.models import Contact, Message, VoiceNote
from src.core.config import get_settings

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
        from src.connectors.whisper_client import WhisperClient
        whisper = WhisperClient()
        if await whisper.health_check(): checks["whisper"] = "ok"
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
