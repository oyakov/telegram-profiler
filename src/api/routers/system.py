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
    checks = {"api": "ok"}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e: checks["database"] = f"error: {str(e)}"
    return {"status": "healthy" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}

@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_contacts = (await db.execute(select(func.count(Contact.id)))).scalar() or 0
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    return {"total_contacts": total_contacts, "total_messages": total_messages}

@router.get("/celery-tasks")
async def get_celery_tasks(db: AsyncSession = Depends(get_db)):
    from src.pipeline.celery_app import celery_app
    from sqlalchemy.orm import joinedload
    import ast
    try:
        inspect = celery_app.control.inspect(timeout=1.0)
        active = inspect.active() or {}
        running = []
        for w, tasks in active.items():
            for t in tasks:
                running.append({"id": t.get("id"), "name": t.get("name"), "worker": w, "status": "running"})
        
        # Fallback to DB
        if not running:
            active_syncs = await db.execute(select(ChannelSyncState).options(joinedload(ChannelSyncState.channel)).where(ChannelSyncState.phase.in_(["metadata", "syncing", "reconciling"])).limit(10))
            for s in active_syncs.scalars().all():
                running.append({"id": f"db_{s.id}", "name": "SYNC", "status": "running", "context": f"Канал: {s.channel.title if s.channel else '...'}", "progress": round(s.progress_percent or 0, 1)})
        
        return {"running": running, "summary": {"total_running": len(running), "total_queued": 0}}
    except: return {"running": [], "summary": {"total_running": 0, "total_queued": 0}}

@router.post("/celery-tasks/purge")
async def purge_celery_tasks():
    import redis as redis_lib
    r = redis_lib.from_url(get_settings().redis_url)
    r.flushdb()
    return {"status": "success"}

@router.get("/tree")
async def get_hierarchical_tree(db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    try:
        folders = (await db.execute(select(TrackedFolder).order_by(TrackedFolder.created_at))).scalars().all()
        channels = (await db.execute(select(TrackedChannel).options(selectinload(TrackedChannel.sync_state)))).scalars().all()
        
        # FACTUAL COUNTS FROM DB
        counts_res = await db.execute(select(Message.group_id, func.count(Message.id)).group_by(Message.group_id))
        counts_map = {str(r[0]): r[1] for r in counts_res.all()}

        tree = []
        fnodes = {}
        for f in folders:
            fn = {"id": str(f.id), "name": f.name, "type": "folder", "children": [], "files": 0, "percentage": 0}
            fnodes[str(f.id)] = fn
            tree.append(fn)

        for ch in channels:
            fid = str(ch.folder_id)
            if fid not in fnodes: continue
            
            # FACTUAL PROGRESS
            tgid = str(ch.telegram_id)
            # Try all common ID variants to match database
            variants = [tgid, f"-100{tgid}", tgid.replace("-100", "")]
            ch_msg_count = sum(counts_map.get(v, 0) for v in set(variants))
            
            progress = 0.0
            status = "idle"
            
            if ch.sync_state:
                status = ch.sync_state.phase
                est = ch.sync_state.estimated_total_messages or 0
                if est > 0:
                    progress = (ch_msg_count / est) * 100
                else:
                    progress = ch.sync_state.progress_percent or 0.1
                
                # FACTUAL UI FIX: If we have messages, we are SYNCING, not Preparing
                if ch_msg_count > 0 and status == "metadata": status = "syncing"
                if status == "complete": progress = 100.0
                if status == "reconciling": progress = max(99.0, progress)
            elif ch_msg_count > 0:
                status = "complete"
                progress = 100.0

            cn = {
                "id": str(ch.id), "name": ch.title or tgid, "type": "channel", 
                "files": ch_msg_count, "percentage": round(min(100, progress), 1), "status": status
            }
            fnodes[fid]["children"].append(cn)
            fnodes[fid]["files"] += ch_msg_count

        for fn in tree:
            if fn["children"]:
                fn["percentage"] = round(sum(c["percentage"] for c in fn["children"]) / len(fn["children"]), 1)
        
        return {"tree": tree}
    except Exception as e:
        logger.error("tree_error", error=str(e), exc_info=True)
        return {"tree": [], "error": str(e)}

@router.get("/prometheus")
async def get_prometheus_metrics(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc); five_min = now - timedelta(minutes=5)
    ingest = (await db.execute(select(func.count(Message.id)).where(Message.created_at >= five_min))).scalar() or 0
    return {"throughput": {"ingestion": round(ingest/5, 1), "timestamp": now.isoformat()}, "crm-app": {"cpu": [{"value": 0.5}], "memory": [{"value": 150.0}]}}

# Placeholder endpoints for frontend compatibility
@router.get("/embeddings")
async def get_embeddings_stats(): return {"total_messages": 0, "messages_with_embeddings": 0, "progress_percent": 0}
@router.get("/embeddings-metrics")
async def get_embeddings_metrics(): return {"current_minute": {"tokens_processed": 0}}
@router.get("/data-quality")
async def get_data_quality_metrics(): return {"status": "ok"}
@router.get("/business-metrics")
async def get_business_metrics(): return {"lead_quality": {"total_leads": 0}}
@router.get("/sync-health")
async def get_sync_health(): return {"total_channels": 0, "healthy": 0}
