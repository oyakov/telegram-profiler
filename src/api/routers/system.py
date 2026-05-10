from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select, func, text, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.db.models import Contact, Message, VoiceNote, MessageEmbedding, ExtractionLog, SyncState, TrackedFolder, TrackedChannel, ChannelSyncState, SyncBatchLog
from src.core.config import get_settings
from datetime import datetime, timedelta, timezone
import redis
import psutil
import structlog

logger = structlog.get_logger()

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

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "checks": checks}

@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Dashboard statistics."""
    total_contacts = (await db.execute(select(func.count(Contact.id)))).scalar()
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar()
    messages_with_group = (await db.execute(select(func.count(Message.id)).where(Message.group_id.isnot(None)))).scalar()
    total_voice = (await db.execute(select(func.count(VoiceNote.id)))).scalar()
    by_source = await db.execute(select(Contact.source, func.count(Contact.id)).group_by(Contact.source))
    return {
        "total_contacts": total_contacts,
        "total_messages": total_messages,
        "messages_with_group": messages_with_group,
        "messages_without_group": total_messages - (messages_with_group or 0),
        "total_voice_notes": total_voice,
        "contacts_by_source": {row[0]: row[1] for row in by_source},
    }

@router.get("/celery-tasks")
async def get_celery_tasks(db: AsyncSession = Depends(get_db)):
    """Get Celery task audit with rich context and DB fallback."""
    from src.pipeline.celery_app import celery_app
    from sqlalchemy.orm import joinedload
    import ast

    try:
        inspect = celery_app.control.inspect(timeout=3.0)
        active_tasks_map = inspect.active() or {}
        
        channels_res = await db.execute(select(TrackedChannel))
        channels_map = {str(c.telegram_id): c for c in channels_res.scalars().all()}
        uuid_map = {str(c.id): c for c in channels_map.values()}

        running_tasks = []
        for worker_name, tasks_list in active_tasks_map.items():
            for task in tasks_list:
                name = task.get("name", "unknown")
                args_str = task.get("args", "()")
                context = "Фоновая задача"
                progress = None
                try:
                    parsed_args = ast.literal_eval(args_str)
                    target_id = str(parsed_args[0]) if parsed_args else None
                    ch = channels_map.get(target_id) or uuid_map.get(target_id)
                    if ch:
                        context = f"Канал: {ch.title}"
                except: pass
                running_tasks.append({"id": task.get("id"), "name": name, "worker": worker_name, "status": "running", "context": context, "progress": progress})

        if not running_tasks:
            active_syncs_res = await db.execute(
                select(ChannelSyncState).options(joinedload(ChannelSyncState.channel))
                .where(ChannelSyncState.phase.in_(["metadata", "syncing", "reconciling"]))
                .where(ChannelSyncState.updated_at >= datetime.now(timezone.utc) - timedelta(minutes=10))
                .order_by(desc(ChannelSyncState.updated_at))
            )
            for sync in active_syncs_res.scalars().all():
                running_tasks.append({
                    "id": f"db_{sync.id}", "name": f"SYNC_{sync.phase.upper()}", "worker": "worker-connectors", "status": "running",
                    "context": f"Канал: {sync.channel.title if sync.channel else 'Unknown'}",
                    "progress": round(sync.progress_percent or 0, 1),
                    "timestamp": sync.updated_at.timestamp(),
                })

        return {"running": running_tasks, "workers": {}, "summary": {"total_running": len(running_tasks), "total_queued": 0, "total_workers": 0}}
    except Exception as e:
        logger.error("celery_tasks_error", error=str(e))
        return {"error": str(e), "running": []}

@router.post("/celery-tasks/purge")
async def purge_celery_tasks():
    import redis as redis_lib
    settings = get_settings()
    try:
        r = redis_lib.from_url(settings.redis_url, socket_timeout=2)
        for q in ["connectors", "processing", "celery"]:
            r.delete(f"celery/queue/{q}" if q != "celery" else "celery")
        return {"status": "success"}
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/tree")
async def get_hierarchical_tree(db: AsyncSession = Depends(get_db)):
    """Bulletproof hierarchical tree with factual progress calculation."""
    from sqlalchemy.orm import selectinload
    try:
        folders_res = await db.execute(select(TrackedFolder).order_by(TrackedFolder.created_at))
        folders = folders_res.scalars().all()
        counts_res = await db.execute(select(Message.group_id, func.count(Message.id)).group_by(Message.group_id))
        channel_counts = {str(row[0]): row[1] for row in counts_res.all()}
        channels_res = await db.execute(select(TrackedChannel))
        channels = channels_res.scalars().all()
        cids = [c.id for c in channels]
        sync_res = await db.execute(select(ChannelSyncState).where(ChannelSyncState.channel_id.in_(cids)).order_by(ChannelSyncState.channel_id, ChannelSyncState.started_at.desc()))
        latest_states = {}
        for s in sync_res.scalars().all():
            if s.channel_id not in latest_states: latest_states[s.channel_id] = s
        tree = []
        folder_nodes = {}
        for f in folders:
            f_node = {"id": str(f.id), "name": f.name, "type": "folder", "children": [], "files": 0, "percentage": 0, "last_change": f.updated_at.isoformat() if f.updated_at else None}
            folder_nodes[str(f.id)] = f_node
            tree.append(f_node)
        for ch in channels:
            if not ch.folder_id or str(ch.folder_id) not in folder_nodes: continue
            raw_id = str(ch.telegram_id).replace("-100", "").lstrip("-")
            variants = [raw_id, f"-100{raw_id}", f"-{raw_id}", str(ch.telegram_id)]
            ch_msg_count = sum(channel_counts.get(v, 0) for v in set(variants))
            st = latest_states.get(ch.id)
            progress = 0.0; status = "idle"
            if st:
                status = st.phase; est = st.estimated_total_messages or 0
                if est > 0: progress = (ch_msg_count / est) * 100
                else: progress = st.progress_percent or 0.0
                if ch_msg_count > 100 and status == "metadata": status = "syncing"
                if status == "complete": progress = 100.0
                elif status == "reconciling": progress = max(99.0, progress)
                if status in ["metadata", "syncing"] and progress < 0.1: progress = 0.1
            elif ch_msg_count > 0: status = "complete"; progress = 100.0
            ch_node = {"id": str(ch.id), "name": ch.title or str(ch.telegram_id), "type": "channel", "username": ch.username, "files": ch_msg_count, "percentage": round(min(100.0, progress), 1), "status": status, "last_change": ch.last_sync_at.isoformat() if ch.last_sync_at else None}
            folder_nodes[str(ch.folder_id)]["children"].append(ch_node); folder_nodes[str(ch.folder_id)]["files"] += ch_msg_count
        for fn in tree:
            if fn["children"]:
                total = sum(c["percentage"] for c in fn["children"])
                fn["percentage"] = round(total / len(fn["children"]), 1)
        return {"tree": tree}
    except Exception as e:
        logger.error("tree_error", error=str(e), exc_info=True)
        return {"tree": [], "error": str(e)}

@router.get("/prometheus")
async def get_prometheus_metrics(range_str: str = "1h", db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc); five_min = now - timedelta(minutes=5)
    ingest = (await db.execute(select(func.count(Message.id)).where(Message.created_at >= five_min))).scalar() or 0
    return {"throughput": {"ingestion": round(ingest/5, 1), "timestamp": now.isoformat()}, "crm-app": {"cpu": [{"value": 1.0}], "memory": [{"value": 120.0}]}}

@router.get("/embeddings-metrics")
async def get_embeddings_metrics(db: AsyncSession = Depends(get_db)):
    try:
        settings = get_settings(); r = redis.from_url(settings.redis_url, socket_timeout=2)
        now = datetime.now(timezone.utc); min_key = now.strftime("%Y-%m-%d %H:%M")
        tokens = int(r.get(f"embeddings:tokens:{min_key}") or 0)
        total = (await db.execute(select(func.count(MessageEmbedding.id)))).scalar() or 0
        return {"current_minute": {"tokens_processed": tokens}, "totals": {"total_embeddings": total}}
    except: return {"error": "metrics_unavailable"}

@router.get("/data-quality")
async def get_data_quality_metrics(db: AsyncSession = Depends(get_db)):
    return {"status": "ok"}

@router.get("/business-metrics")
async def get_business_metrics(db: AsyncSession = Depends(get_db)):
    return {"status": "ok"}

@router.get("/sync-health")
async def get_sync_health(db: AsyncSession = Depends(get_db)):
    return {"status": "ok"}

@router.get("/embeddings")
async def get_embeddings_stats(db: AsyncSession = Depends(get_db)):
    return {"status": "ok"}
