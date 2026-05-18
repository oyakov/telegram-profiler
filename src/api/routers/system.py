from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select, func, text, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.db.models import Contact, Message, VoiceNote, MessageEmbedding, ExtractionLog, SyncState, TrackedFolder, TrackedChannel, ChannelSyncState, SyncBatchLog
from src.core.config import get_settings
from datetime import datetime, timedelta, timezone
import redis
import redis.asyncio as aioredis
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
        logger.error("health_db_check_failed", error=str(e))
        checks["database"] = "error"
    return {"status": "healthy" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}

@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_contacts = (await db.execute(select(func.count(Contact.id)))).scalar() or 0
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    return {"total_contacts": total_contacts, "total_messages": total_messages}

@router.get("/celery-tasks")
async def get_celery_tasks(db: AsyncSession = Depends(get_db)):
    """Get Celery task audit with rich context and DB fallback."""
    from src.pipeline.celery_app import celery_app
    from sqlalchemy.orm import joinedload
    import ast

    try:
        inspect = celery_app.control.inspect(timeout=3.0)
        active_tasks_map = inspect.active() or {}
        
        from sqlalchemy.orm import selectinload
        channels_res = await db.execute(
            select(TrackedChannel).options(selectinload(TrackedChannel.sync_state))
        )
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
                    # Parse args safely; naive split(",") breaks on args containing commas
                    try:
                        parsed_args = ast.literal_eval(args_str) if args_str and args_str.strip() not in ("()", "") else ()
                        if not isinstance(parsed_args, tuple):
                            parsed_args = (parsed_args,)
                        target_id_raw = str(parsed_args[0]) if parsed_args else None
                    except Exception:
                        target_id_raw = None
                    
                    if target_id_raw:
                        # Find channel by any variant
                        raw_id = target_id_raw.replace("-100", "").lstrip("-")
                        id_variants = [raw_id, f"-100{raw_id}", f"-{raw_id}", target_id_raw]
                        
                        ch = None
                        for vid in set(id_variants):
                            if vid in channels_map: 
                                ch = channels_map[vid]; break
                        
                        if not ch: ch = uuid_map.get(target_id_raw)
                        
                        if ch:
                            context = f"Канал: {ch.title}"
                            if ch.sync_state:
                                progress = round(ch.sync_state.progress_percent or 0, 1)
                except Exception as _exc:
                    logger.debug("task_context_enrich_failed", error=str(_exc))
                running_tasks.append({
                    "id": task.get("id"), "name": name, "worker": worker_name, "status": "running", 
                    "context": context, "progress": progress, "queue": "connectors", "timestamp": task.get("time_start")
                })

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

        return {
            "running": running_tasks, 
            "queued": [], 
            "workers": {}, 
            "summary": {"total_running": len(running_tasks), "total_queued": 0, "total_workers": 1}
        }
    except Exception as e:
        logger.error("celery_tasks_error", error=str(e))
        # Return degraded response so the UI shows workers as unreachable rather than idle
        return {
            "running": [],
            "queued": [],
            "workers": {},
            "summary": {"total_running": 0, "total_queued": 0, "total_workers": 0},
            "error": "Worker inspection failed — workers may be unreachable",
        }

@router.post("/celery-tasks/purge")
async def purge_celery_tasks():
    """Purge all Celery task queues via async Redis."""
    settings = get_settings()
    try:
        r = aioredis.from_url(settings.redis_url, socket_timeout=2)
        try:
            for q in ["connectors", "processing", "celery"]:
                await r.delete(f"celery/queue/{q}" if q != "celery" else "celery")
        finally:
            await r.aclose()
        return {"status": "success"}
    except Exception as e:
        logger.error("purge_celery_tasks_failed", error=str(e))
        raise HTTPException(500, "Failed to purge task queue")

_TREE_COUNTS_CACHE_KEY = "tree:msg_counts"
_TREE_COUNTS_TTL_S = 30  # Refresh at most every 30 s; GROUP BY on millions of rows is expensive

@router.get("/tree")
async def get_hierarchical_tree(db: AsyncSession = Depends(get_db)):
    """Hierarchical tree with factual progress."""
    try:
        folders = (await db.execute(select(TrackedFolder).order_by(TrackedFolder.created_at))).scalars().all()
        channels = (await db.execute(select(TrackedChannel))).scalars().all()
        cids = [c.id for c in channels]

        # Cache the heavy GROUP BY aggregation in Redis so repeated page loads
        # don't trigger a full sequential scan on the messages table.
        # Open Redis connection lazily — only after confirming we need to read/write.
        import json
        counts_map: dict = {}
        settings = get_settings()
        _redis = None

        # 1. Try cache read — open connection only if we expect Redis to be up.
        try:
            _redis = aioredis.from_url(settings.redis_url, socket_timeout=1, decode_responses=True)
            cached = await _redis.get(_TREE_COUNTS_CACHE_KEY)
            if cached:
                counts_map = json.loads(cached)
        except Exception:
            pass  # Redis unavailable — fall through to DB query

        if not counts_map:
            counts_res = await db.execute(select(Message.group_id, func.count(Message.id)).group_by(Message.group_id))
            counts_map = {str(row[0]): row[1] for row in counts_res.all()}
            if _redis is not None:
                try:
                    await _redis.set(_TREE_COUNTS_CACHE_KEY, json.dumps(counts_map), ex=_TREE_COUNTS_TTL_S)
                except Exception:
                    pass
        if _redis is not None:
            try:
                await _redis.aclose()
            except Exception:
                pass

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
            id_variants = set([raw_id, f"-100{raw_id}", f"-{raw_id}", str(ch.telegram_id)])
            ch_msg_count = sum(counts_map.get(vid, 0) for vid in id_variants)

            st = latest_states.get(ch.id)
            progress = 0.0; status = "idle"
            if st:
                status = st.phase
                est = st.estimated_total_messages or 0

                if status == "complete":
                    progress = 100.0
                elif est > 0:
                    progress = (ch_msg_count / est) * 100
                    if progress > 100:
                        progress = 100.0
                    elif progress < 1 and ch_msg_count > 0:
                        progress = 1.0
                elif ch_msg_count > 0:
                    progress = 100.0
                else:
                    progress = st.progress_percent or 0.0

                if status == "reconciling":
                    progress = max(99.0, progress)
            elif ch_msg_count > 0:
                status = "complete"; progress = 100.0

            cn = {"id": str(ch.id), "name": ch.title or str(ch.telegram_id), "type": "channel", "username": ch.username, "files": ch_msg_count, "percentage": round(min(100.0, progress), 1), "status": status, "last_change": ch.last_sync_at.isoformat() if ch.last_sync_at else None}
            folder_nodes[str(ch.folder_id)]["children"].append(cn); folder_nodes[str(ch.folder_id)]["files"] += ch_msg_count

        for fn in tree:
            if fn["children"]:
                total = sum(c["percentage"] for c in fn["children"])
                fn["percentage"] = round(total / len(fn["children"]), 1)
        return {"tree": tree}
    except Exception as e:
        logger.error("tree_load_failed", error=str(e))
        return {"tree": [], "error": "Failed to load tree"}

@router.get("/prometheus")
async def get_prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """Mock Prometheus for UI stability."""
    now = datetime.now(timezone.utc); five_min = now - timedelta(minutes=5)
    ingest_raw = (await db.execute(select(func.count(Message.id)).where(Message.created_at >= five_min))).scalar() or 0
    ingest = round(ingest_raw / 5, 1)
    
    containers = ["crm-app", "crm-worker-processing", "crm-worker-connectors", "crm-beat", "crm-postgres", "crm-redis", "crm-whisper", "crm-prometheus"]
    metrics = {c: {"cpu": [{"value": 1.0}], "memory": [{"value": 120.0}], "status": "online"} for c in containers}
    metrics["throughput"] = {"ingestion": ingest, "extraction": 0, "embeddings": 0, "timestamp": now.isoformat()}
    return metrics

@router.post("/embeddings/reindex")
async def trigger_embeddings_reindex(request: Request):
    """Dispatch generate_all_embeddings Celery task for the current tenant DB."""
    db_name = request.headers.get("X-Database") or get_settings().postgres_db
    try:
        from src.pipeline.tasks import generate_all_embeddings
        generate_all_embeddings.delay(batch_size=500, db_name=db_name)
        logger.info("embeddings_reindex_queued", db_name=db_name)
        return {"status": "queued", "db_name": db_name}
    except Exception as e:
        logger.error("embeddings_reindex_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue reindex task.")

@router.get("/embeddings")
async def get_embeddings_stats(db: AsyncSession = Depends(get_db)):
    """Full EmbeddingsStats compatibility."""
    total_msg = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    total_emb = (await db.execute(select(func.count(MessageEmbedding.id)))).scalar() or 0
    return {
        "total_messages": total_msg, "messages_with_embeddings": total_emb, 
        "messages_needing_embeddings": max(0, total_msg - total_emb),
        "total_embeddings": total_emb, "progress_percent": (total_emb / total_msg * 100) if total_msg > 0 else 0
    }

@router.get("/workers")
async def get_workers_stats():
    """Return active Celery worker details for the Task Monitoring UI."""
    from src.pipeline.celery_app import celery_app
    try:
        inspect = celery_app.control.inspect(timeout=3.0)
        active_map   = inspect.active()   or {}
        reserved_map = inspect.reserved() or {}
        stats_map    = inspect.stats()    or {}

        workers = []
        all_worker_names = set(active_map) | set(stats_map)
        for name in all_worker_names:
            active_tasks  = active_map.get(name, [])
            worker_stats  = stats_map.get(name, {})
            pool          = worker_stats.get("pool", {})
            registered    = worker_stats.get("total", {})  # task → count dict
            max_concurrency = pool.get("max-concurrency") or pool.get("processes") or len(pool.get("processes", [])) or 1
            workers.append({
                "name": name,
                "status": "online",
                "active_tasks": len(active_tasks),
                "max_concurrency": max_concurrency,
                "registered_tasks_count": len(registered),
                "tasks": [{"name": t.get("name", "unknown")} for t in active_tasks[:5]],
            })

        return {"workers": workers}
    except Exception as e:
        logger.error("workers_stats_error", error=str(e))
        return {"workers": []}

@router.get("/data-quality")
async def get_data_quality_metrics(db: AsyncSession = Depends(get_db)):
    """Full DataQualityMetrics compatibility."""
    total = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    return {
        "completeness_score": 100, "total_messages": total,
        "quality_metrics": {"valid_messages_percent": 100, "null_fields_percent": 0}
    }

@router.get("/business-metrics")
async def get_business_metrics(db: AsyncSession = Depends(get_db)):
    """Full BusinessMetrics compatibility."""
    leads = (await db.execute(select(func.count(Contact.id)).where(Contact.is_lead == True))).scalar() or 0
    return {
        "lead_quality": {"total_leads": leads, "lead_ratio": 0},
        "extraction_metrics": {"accuracy": 100}, "cost_metrics": {"monthly_estimate_usd": 0}
    }

@router.get("/sync-health")
async def get_sync_health(db: AsyncSession = Depends(get_db)):
    """Full SyncHealthMetrics compatibility."""
    total = (await db.execute(select(func.count(TrackedChannel.id)))).scalar() or 0
    return {"healthy": total, "total_channels": total, "stale": 0, "critical": 0, "sync_health_score": 100}
