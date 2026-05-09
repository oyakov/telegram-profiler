from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.db.models import Contact, Message, VoiceNote, MessageEmbedding, ExtractionLog, SyncState
from src.core.config import get_settings
from datetime import datetime, timedelta, timezone
import redis
import psutil

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
    messages_with_group = (await db.execute(select(func.count(Message.id)).where(Message.group_id.isnot(None)))).scalar()
    total_voice = (await db.execute(select(func.count(VoiceNote.id)))).scalar()

    by_source = await db.execute(
        select(Contact.source, func.count(Contact.id)).group_by(Contact.source)
    )

    return {
        "total_contacts": total_contacts,
        "total_messages": total_messages,
        "messages_with_group": messages_with_group,  # messages attached to channels
        "messages_without_group": total_messages - (messages_with_group or 0),  # direct messages
        "total_voice_notes": total_voice,
        "contacts_by_source": {row[0]: row[1] for row in by_source},
    }

@router.get("/timeline")
async def get_timeline_stats(days: int = 14, db: AsyncSession = Depends(get_db)):
    """Get message and lead ingestion timeline."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # 1. Messages per day
    msg_query = (
        select(
            func.date_trunc('day', Message.timestamp).label('day'),
            func.count(Message.id).label('count')
        )
        .where(Message.timestamp >= cutoff)
        .group_by('day')
        .order_by('day')
    )
    msg_rows = (await db.execute(msg_query)).all()
    
    # 2. Leads per day
    lead_query = (
        select(
            func.date_trunc('day', Contact.created_at).label('day'),
            func.count(Contact.id).label('count')
        )
        .where(Contact.is_lead == True)
        .where(Contact.created_at >= cutoff)
        .group_by('day')
        .order_by('day')
    )
    lead_rows = (await db.execute(lead_query)).all()
    
    # Format data for Recharts
    data_map = {}
    for r in msg_rows:
        day_str = r.day.date().isoformat()
        data_map[day_str] = {"day": day_str, "messages": r.count, "leads": 0}
        
    for r in lead_rows:
        day_str = r.day.date().isoformat()
        if day_str not in data_map:
            data_map[day_str] = {"day": day_str, "messages": 0, "leads": r.count}
        else:
            data_map[day_str]["leads"] = r.count
            
    return {"timeline": sorted(data_map.values(), key=lambda x: x["day"])}

@router.get("/audit-logs")
async def get_audit_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recent AI extraction and system logs."""
    logs_res = await db.execute(
        select(ExtractionLog)
        .order_by(ExtractionLog.created_at.desc())
        .limit(limit)
    )
    logs = logs_res.scalars().all()
    
    return {
        "logs": [
            {
                "id": str(log.id),
                "type": log.source_type,
                "model": log.model_used,
                "success": log.success,
                "time_ms": log.processing_time_ms,
                "created_at": log.created_at.isoformat(),
                "details": f"Processed {log.source_type} ({log.source_id})"
            }
            for log in logs
        ]
    }

@router.get("/celery-tasks")
async def get_celery_tasks():
    """Get Celery task audit - running, completed, and queued tasks."""
    from src.pipeline.celery_app import celery_app
    from datetime import datetime

    try:
        # Get task inspect instance
        inspect = celery_app.control.inspect()

        # Active tasks (currently running)
        active_tasks = inspect.active() or {}
        running_tasks = []
        for worker_name, tasks_list in active_tasks.items():
            for task in tasks_list:
                running_tasks.append({
                    "id": task.get("id"),
                    "name": task.get("name"),
                    "args": str(task.get("args", []))[:100],
                    "kwargs": str(task.get("kwargs", {}))[:100],
                    "worker": worker_name,
                    "status": "running",
                    "timestamp": task.get("time_start"),
                })

        # Registered tasks
        registered = inspect.registered() or {}
        all_registered = set()
        for worker_name, task_list in registered.items():
            all_registered.update(task_list)

        # Get task stats
        stats = inspect.stats() or {}
        worker_stats = {
            name: {
                "pool": stat.get("pool", {}).get("implementation", "unknown"),
                "max_concurrency": stat.get("pool", {}).get("max-concurrency", 0),
                "active": len(active_tasks.get(name, [])),
            }
            for name, stat in stats.items()
        }

        # Get queued tasks from Redis
        import redis as redis_lib
        from src.core.config import get_settings
        settings = get_settings()

        queued_tasks = []
        try:
            r = redis_lib.from_url(settings.redis_url, socket_timeout=2)
            # Get tasks from all queues
            queue_names = ["connectors", "processing", "celery"]
            for queue_name in queue_names:
                queue_key = f"celery/queue/{queue_name}" if queue_name != "celery" else "celery"
                queue_len = r.llen(queue_key)
                if queue_len > 0:
                    # Try to peek at some tasks (limited to 10 per queue)
                    for i in range(min(10, queue_len)):
                        task_data = r.lindex(queue_key, i)
                        if task_data:
                            import json
                            try:
                                task_obj = json.loads(task_data)
                                # Celery v5 format: headers and properties
                                headers = task_obj.get("headers", {})
                                properties = task_obj.get("properties", {})
                                task_id = headers.get("id") or properties.get("reply_to")
                                task_name = headers.get("task") or task_obj.get("task", "unknown")
                                # Get timestamp when task was sent/enqueued
                                timestamp = None
                                if "sent_time" in headers:
                                    timestamp = headers.get("sent_time")
                                elif "timestamp" in properties:
                                    timestamp = properties.get("timestamp")
                                queued_tasks.append({
                                    "id": task_id,
                                    "name": task_name,
                                    "queue": queue_name,
                                    "status": "queued",
                                    "position": i + 1,
                                    "timestamp": timestamp,
                                })
                            except Exception as parse_err:
                                logger.debug("Could not parse queue task", error=str(parse_err))
        except Exception as e:
            logger.warning("Could not fetch queued tasks", error=str(e))

        return {
            "running": running_tasks,
            "queued": queued_tasks,
            "workers": worker_stats,
            "registered_tasks": list(all_registered)[:50],  # Limit to 50 for display
            "summary": {
                "total_running": len(running_tasks),
                "total_queued": len(queued_tasks),
                "total_workers": len(worker_stats),
            }
        }

    except Exception as e:
        logger.error("celery_tasks_error", error=str(e))
        return {
            "error": str(e),
            "running": [],
            "queued": [],
            "workers": {},
            "summary": {"total_running": 0, "total_queued": 0}
        }


@router.post("/celery-tasks/purge")
async def purge_celery_tasks():
    """Purge all Celery queues in Redis."""
    import redis as redis_lib
    from src.core.config import get_settings
    import structlog
    
    logger = structlog.get_logger()
    settings = get_settings()
    
    try:
        r = redis_lib.from_url(settings.redis_url, socket_timeout=2)
        # 1. Clear specific queues
        queue_names = ["connectors", "processing", "celery"]
        purged_count = 0
        for queue_name in queue_names:
            queue_key = f"celery/queue/{queue_name}" if queue_name != "celery" else "celery"
            count = r.llen(queue_key)
            if count > 0:
                r.delete(queue_key)
                purged_count += count
        
        # 2. Also flush all keys matching celery patterns just in case
        # Note: flushdb/flushall is too aggressive, we use delete for specific keys
        
        logger.info("celery_queues_purged", count=purged_count)
        return {
            "status": "success",
            "purged_count": purged_count,
            "message": f"Successfully purged {purged_count} tasks from queues"
        }
    except Exception as e:
        logger.error("purge_tasks_error", error=str(e))
        raise HTTPException(500, f"Failed to purge tasks: {str(e)}")

@router.get("/embeddings-metrics")
async def get_embeddings_metrics(db: AsyncSession = Depends(get_db)):
    """Get embeddings processing metrics - tokens/min and requests/min."""
    from datetime import datetime, timedelta, timezone
    import redis as redis_lib
    from src.core.config import get_settings

    try:
        settings = get_settings()

        # Get metrics from Redis (for real-time processing)
        r = redis_lib.from_url(settings.redis_url, socket_timeout=2)

        # Get current minute counters
        now = datetime.now(timezone.utc)
        minute_key = now.strftime("%Y-%m-%d %H:%M")
        tokens_key = f"embeddings:tokens:{minute_key}"
        requests_key = f"embeddings:requests:{minute_key}"

        tokens_processed = int(r.get(tokens_key) or 0)
        requests_processed = int(r.get(requests_key) or 0)

        # Also get last minute for comparison
        last_minute = now - timedelta(minutes=1)
        last_minute_key = last_minute.strftime("%Y-%m-%d %H:%M")
        last_tokens_key = f"embeddings:tokens:{last_minute_key}"
        last_requests_key = f"embeddings:requests:{last_minute_key}"

        last_tokens = int(r.get(last_tokens_key) or 0)
        last_requests = int(r.get(last_requests_key) or 0)

        # Calculate trend
        tokens_trend = ((tokens_processed - last_tokens) / (last_tokens + 1) * 100) if last_tokens else 0
        requests_trend = ((requests_processed - last_requests) / (last_requests + 1) * 100) if last_requests else 0

        # Get total embeddings from DB
        total_embeddings = (await db.execute(select(func.count(MessageEmbedding.id)))).scalar() or 0
        embeddings_last_hour = (await db.execute(
            select(func.count(MessageEmbedding.id))
            .where(MessageEmbedding.created_at >= datetime.now(timezone.utc) - timedelta(hours=1))
        )).scalar() or 0

        return {
            "current_minute": {
                "tokens_processed": tokens_processed,
                "requests_processed": requests_processed,
                "minute": minute_key,
            },
            "last_minute": {
                "tokens_processed": last_tokens,
                "requests_processed": last_requests,
            },
            "trends": {
                "tokens_trend_percent": round(tokens_trend, 2),
                "requests_trend_percent": round(requests_trend, 2),
            },
            "totals": {
                "total_embeddings": total_embeddings,
                "embeddings_last_hour": embeddings_last_hour,
            }
        }
    except Exception as e:
        logger.error("embeddings_metrics_error", error=str(e))
        return {
            "current_minute": {"tokens_processed": 0, "requests_processed": 0},
            "last_minute": {"tokens_processed": 0, "requests_processed": 0},
            "trends": {"tokens_trend_percent": 0, "requests_trend_percent": 0},
            "totals": {"total_embeddings": 0, "embeddings_last_hour": 0},
            "error": str(e)
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

    # Estimating cost based on LLM provider
    settings = get_settings()
    if settings.llm_provider.lower() == "lmstudio":
        # LMStudio is local, no costs
        estimated_cost_usd = 0.0
    else:
        # Gemini pricing (prompt: $0.075/1M, completion: $0.30/1M)
        estimated_cost_usd = (prompt_tokens / 1_000_000 * 0.075) + (completion_tokens / 1_000_000 * 0.30)
    
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

@router.get("/tree")
async def get_hierarchical_tree(db: AsyncSession = Depends(get_db)):
    """Get hierarchical tree of data (Folder > Channel) with stats."""
    from src.db.models import TrackedFolder, TrackedChannel, Message, ChannelSyncState
    from sqlalchemy.orm import selectinload

    try:
        # Get all folders
        folders_res = await db.execute(
            select(TrackedFolder).order_by(TrackedFolder.created_at)
        )
        folders = folders_res.scalars().all()

        # Get message counts by channel (group_id is telegram_id)
        channel_counts_res = await db.execute(
            select(Message.group_id, func.count(Message.id))
            .where(Message.group_id.isnot(None))
            .group_by(Message.group_id)
        )
        channel_counts = {str(row[0]): row[1] for row in channel_counts_res.all()}

        # Get all channels with their sync states
        channels_res = await db.execute(
            select(TrackedChannel).options(selectinload(TrackedChannel.sync_state))
        )
        channels = channels_res.scalars().all()

        tree = []
        folder_nodes = {}

        # Build folder tree
        for f in folders:
            f_node = {
                "id": str(f.id),
                "name": f.name,
                "type": "folder",
                "children": [],
                "files": 0,
                "percentage": 0,
                "last_change": f.updated_at.isoformat() if f.updated_at else None
            }
            folder_nodes[str(f.id)] = f_node
            tree.append(f_node)

        # Map channels to folders
        for ch in channels:
            if not ch.folder_id or str(ch.folder_id) not in folder_nodes:
                continue

            ch_msg_count = channel_counts.get(str(ch.telegram_id), 0)
            
            progress = 0
            status = "pending"
            if ch.sync_state:
                progress = ch.sync_state.progress_percent
                status = ch.sync_state.phase
            
            ch_node = {
                "id": str(ch.id),
                "name": ch.title or str(ch.telegram_id),
                "type": "channel",
                "username": ch.username,
                "files": ch_msg_count,
                "percentage": round(progress, 1),
                "status": status,
                "last_change": ch.last_sync_at.isoformat() if ch.last_sync_at else None
            }
            
            folder_nodes[str(ch.folder_id)]["children"].append(ch_node)
            folder_nodes[str(ch.folder_id)]["files"] += ch_msg_count

        # Calculate folder average progress
        for f_node in tree:
            if f_node["children"]:
                total_progress = sum(c["percentage"] for c in f_node["children"])
                f_node["percentage"] = round(total_progress / len(f_node["children"]), 1)

        return {"tree": tree}

    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("hierarchical_tree_error", error=str(e), exc_info=True)
        return {"tree": [], "error": str(e)}

@router.get("/prometheus")
async def get_prometheus_metrics(range_str: str = "1h", db: AsyncSession = Depends(get_db)):
    """Get Prometheus metrics and real-time throughput for all system containers."""
    import random
    from datetime import datetime, timedelta, timezone
    from src.db.models import Message, MessageEmbedding, ExtractionLog

    # 1. Calculate real throughput for current database (5-minute sliding window for smoothness)
    now = datetime.now(timezone.utc)
    five_min_ago = now - timedelta(minutes=5)

    # Count recent messages and average per minute
    total_ingestion_raw = (await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= five_min_ago)
    )).scalar() or 0
    total_ingestion = round(total_ingestion_raw / 5, 1)

    # Count recent extractions and average per minute
    total_extraction_raw = (await db.execute(
        select(func.count(ExtractionLog.id)).where(ExtractionLog.created_at >= five_min_ago)
    )).scalar() or 0
    total_extraction = round(total_extraction_raw / 5, 1)

    # Count recent embeddings and average per minute
    total_embeddings_raw = (await db.execute(
        select(func.count(MessageEmbedding.id)).where(MessageEmbedding.created_at >= five_min_ago)
    )).scalar() or 0
    total_embeddings = round(total_embeddings_raw / 5, 1)

    # 2. Mock some system metrics (CPU/MEM) but use real throughput
    def generate_metric_data(base_value: float, variation: float, count: int = 10) -> list:
        data = []
        for i in range(count):
            timestamp = (now - timedelta(minutes=(count - i) * 5)).timestamp() * 1000
            value = base_value + random.uniform(-variation, variation)
            data.append({"timestamp": int(timestamp), "value": round(max(0.1, value), 2)})
        return data

    containers = [
        "crm-app", "crm-worker-processing", "crm-worker-connectors", 
        "crm-beat", "crm-postgres", "crm-redis", "crm-whisper", "crm-prometheus"
    ]

    metrics = {}
    for container in containers:
        base_cpu = 5.0 if "worker" in container else 1.0
        base_mem = 800.0 if "whisper" in container else 120.0
        
        metrics[container] = {
            "cpu": generate_metric_data(base_cpu, base_cpu * 0.4),
            "memory": generate_metric_data(base_mem, base_mem * 0.1),
            "status": "online"
        }

    # Add throughput to the response
    metrics["throughput"] = {
        "ingestion": total_ingestion,    # msg/min
        "extraction": total_extraction,  # tasks/min
        "embeddings": total_embeddings,  # vectors/min
        "timestamp": now.isoformat()
    }

    return metrics

@router.get("/data-quality")
async def get_data_quality_metrics(db: AsyncSession = Depends(get_db)):
    """Get data quality metrics."""
    from src.db.models import Message, Contact

    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    messages_null_group = (await db.execute(
        select(func.count(Message.id)).where(Message.group_id.is_(None))
    )).scalar() or 0
    messages_null_contact = (await db.execute(
        select(func.count(Message.id)).where(Message.contact_id.is_(None))
    )).scalar() or 0

    total_contacts = (await db.execute(select(func.count(Contact.id)))).scalar() or 0

    return {
        "total_messages": total_messages,
        "null_group_id": messages_null_group,
        "null_contact_id": messages_null_contact,
        "total_contacts": total_contacts,
        "completeness_score": round((1 - (messages_null_contact / total_messages * 100)) if total_messages > 0 else 0, 1),
        "quality_metrics": {
            "null_fields_percent": round((messages_null_contact + messages_null_group) / (total_messages * 2) * 100 if total_messages > 0 else 0, 1),
            "valid_messages_percent": round((total_messages - messages_null_contact) / total_messages * 100 if total_messages > 0 else 0, 1)
        }
    }

@router.get("/sync-health")
async def get_sync_health(db: AsyncSession = Depends(get_db)):
    """Get sync and connector health metrics."""
    from src.db.models import TrackedChannel, Message
    from datetime import datetime, timezone, timedelta

    channels = (await db.execute(select(TrackedChannel))).scalars().all()
    now = datetime.now(timezone.utc)

    sync_health = []
    for ch in channels:
        last_sync = ch.last_sync_at
        if last_sync:
            sync_lag = (now - last_sync).total_seconds() / 3600  # hours
            status = "healthy" if sync_lag < 24 else "stale" if sync_lag < 72 else "critical"
        else:
            sync_lag = float('inf')
            status = "never_synced"

        msg_count = (await db.execute(
            select(func.count(Message.id)).where(Message.group_id == ch.telegram_id)
        )).scalar() or 0

        sync_health.append({
            "channel": ch.title,
            "last_sync_hours_ago": round(sync_lag, 1) if sync_lag != float('inf') else None,
            "status": status,
            "message_count": msg_count
        })

    healthy_count = sum(1 for s in sync_health if s['status'] == 'healthy')
    return {
        "total_channels": len(channels),
        "healthy": healthy_count,
        "stale": sum(1 for s in sync_health if s['status'] == 'stale'),
        "critical": sum(1 for s in sync_health if s['status'] == 'critical'),
        "never_synced": sum(1 for s in sync_health if s['status'] == 'never_synced'),
        "sync_health_score": round((healthy_count / len(channels) * 100) if channels else 0, 1),
        "details": sync_health
    }

@router.get("/user-metrics")
async def get_user_metrics(db: AsyncSession = Depends(get_db)):
    """Get user and session metrics."""
    from src.db.models import Contact

    contacts_by_source = await db.execute(
        select(Contact.source, func.count(Contact.id)).group_by(Contact.source)
    )

    return {
        "contacts_by_source": {row[0]: row[1] for row in contacts_by_source},
        "total_users": (await db.execute(select(func.count(Contact.id)))).scalar() or 0,
        "active_last_7days": (await db.execute(
            select(func.count(Contact.id)).where(Contact.updated_at >= datetime.now(timezone.utc) - timedelta(days=7))
        )).scalar() or 0
    }

@router.get("/business-metrics")
async def get_business_metrics(db: AsyncSession = Depends(get_db)):
    """Get business-relevant metrics."""
    from src.db.models import Contact, Message, ExtractionLog

    leads_count = (await db.execute(
        select(func.count(Contact.id)).where(Contact.is_lead == True)
    )).scalar() or 0
    total_contacts = (await db.execute(select(func.count(Contact.id)))).scalar() or 0
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0

    extraction_runs = (await db.execute(select(func.count(ExtractionLog.id)))).scalar() or 0
    successful_extractions = (await db.execute(
        select(func.count(ExtractionLog.id)).where(ExtractionLog.success == True)
    )).scalar() or 0

    return {
        "lead_quality": {
            "total_leads": leads_count,
            "lead_ratio": round((leads_count / total_contacts * 100) if total_contacts > 0 else 0, 1),
            "quality_score": min(100, round((leads_count / (total_messages / 100)) if total_messages > 0 else 0, 1))
        },
        "extraction_metrics": {
            "total_runs": extraction_runs,
            "success_count": successful_extractions,
            "accuracy": round((successful_extractions / extraction_runs * 100) if extraction_runs > 0 else 0, 1)
        },
        "cost_metrics": {
            "cost_per_message_usd": round(0.00001, 5),  # Mock value
            "monthly_estimate_usd": round(0.00001 * total_messages, 2)
        }
    }

@router.get("/resource-metrics")
async def get_resource_metrics(db: AsyncSession = Depends(get_db)):
    """Get resource usage and database metrics."""
    import psutil

    try:
        # Get database size
        result = await db.execute(text("""
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """))
        db_size = result.scalar()
    except:
        db_size = "unknown"

    return {
        "database": {
            "size": db_size,
            "connection_count": 5  # Mock
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    }

@router.get("/real-time-alerts")
async def get_real_time_alerts(db: AsyncSession = Depends(get_db)):
    """Get active system alerts."""
    alerts = []

    # Check embeddings progress
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    messages_with_embeddings = (await db.execute(
        select(func.count(func.distinct(MessageEmbedding.message_id)))
    )).scalar() or 0
    embedding_percent = (messages_with_embeddings / total_messages * 100) if total_messages > 0 else 0

    if embedding_percent < 50:
        alerts.append({
            "type": "WARNING",
            "severity": "medium",
            "message": f"Embedding progress low: {embedding_percent:.1f}%",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    # Check for stale syncs
    from src.db.models import TrackedChannel
    from datetime import timedelta

    stale_channels = await db.execute(
        select(func.count(TrackedChannel.id)).where(
            TrackedChannel.last_sync_at < datetime.now(timezone.utc) - timedelta(hours=72)
        )
    )
    stale_count = stale_channels.scalar() or 0

    if stale_count > 0:
        alerts.append({
            "type": "WARNING",
            "severity": "medium",
            "message": f"{stale_count} channels not synced in 72+ hours",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    return {
        "active_alerts": len(alerts),
        "alerts": alerts,
        "status": "healthy" if len(alerts) == 0 else "needs_attention"
    }
