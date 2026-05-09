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
    """Get hierarchical tree of data (Project > Folder > Channel) with stats."""
    from src.db.models import SystemProject, TrackedFolder, TrackedChannel, Message

    # 1. Get all projects
    projects_res = await db.execute(select(SystemProject).order_by(SystemProject.name))
    projects = projects_res.scalars().all()

    tree = []

    for proj in projects:
        proj_node = {
            "id": str(proj.id),
            "name": proj.name,
            "type": "project",
            "children": [],
            "files": 0,
            "percentage": 0,
            "status": "active" if proj.is_active else "inactive"
        }

        try:
            # Get folders for this project
            folders_res = await db.execute(
                select(TrackedFolder).where(TrackedFolder.project_id == proj.id)
            )
            folders = folders_res.scalars().all()

            # Get message counts for this project
            msg_counts_res = await db.execute(
                select(Message.folder_id, func.count(Message.id))
                .where(Message.project_id == proj.id)
                .where(Message.folder_id.isnot(None))
                .group_by(Message.folder_id)
            )
            msg_counts = {str(row[0]): row[1] for row in msg_counts_res.all()}

            # Count messages without folder assignment
            unattached_count = (await db.execute(
                select(func.count(Message.id))
                .where(Message.project_id == proj.id)
                .where(Message.folder_id.is_(None))
            )).scalar() or 0

            proj_total_files = sum(msg_counts.values()) + unattached_count
            proj_node["files"] = proj_total_files

            # Build folder tree
            folder_nodes = {}
            for f in folders:
                f_node = {
                    "id": str(f.id),
                    "name": f.name,
                    "type": "folder",
                    "children": [],
                    "files": msg_counts.get(str(f.id), 0),
                    "percentage": 0,
                    "last_change": f.updated_at.isoformat() if f.updated_at else None
                }
                folder_nodes[str(f.id)] = f_node
                proj_node["children"].append(f_node)

            # Get channels for this project and add to folders
            channels_res = await db.execute(
                select(TrackedChannel)
                .where(TrackedChannel.folder_id.in_([f.id for f in folders]))
            )
            channels = channels_res.scalars().all()

            for ch in channels:
                if ch.folder_id:
                    ch_files = msg_counts.get(str(ch.folder_id), 0)
                    ch_node = {
                        "id": str(ch.id),
                        "name": ch.title or ch.telegram_id,
                        "type": "channel",
                        "username": ch.username,
                        "files": ch_files,
                        "percentage": 0,
                        "last_change": ch.last_sync_at.isoformat() if ch.last_sync_at else None
                    }
                    if str(ch.folder_id) in folder_nodes:
                        folder_nodes[str(ch.folder_id)]["children"].append(ch_node)

            # Add unattached messages node if any exist
            if unattached_count > 0:
                unattached_node = {
                    "id": f"{proj.id}_unattached",
                    "name": "Unattached Messages",
                    "type": "folder",
                    "children": [],
                    "files": unattached_count,
                    "percentage": 0,
                    "last_change": None
                }
                proj_node["children"].append(unattached_node)

            # Calculate percentages
            for fn in proj_node["children"]:
                if proj_total_files > 0:
                    fn["percentage"] = round((fn["files"] / proj_total_files) * 100, 1)

        except Exception as e:
            proj_node["error"] = str(e)
            proj_node["status"] = "error"

        tree.append(proj_node)

    return {"tree": tree}

@router.get("/prometheus")
async def get_prometheus_metrics(range_str: str = "1h", db: AsyncSession = Depends(get_db)):
    """Get Prometheus metrics and real-time throughput for all system containers."""
    import random
    from datetime import datetime, timedelta, timezone
    from src.db.models import SystemProject, Message, MessageEmbedding, ExtractionLog
    from src.db.database import get_session

    # 1. Calculate real throughput across ALL databases
    now = datetime.now(timezone.utc)
    one_min_ago = now - timedelta(minutes=1)
    
    # Get all projects
    projects_res = await db.execute(select(SystemProject).where(SystemProject.is_active == True))
    projects = projects_res.scalars().all()
    
    total_ingestion = 0  # msg/min
    total_extraction = 0 # tasks/min
    total_embeddings = 0 # vectors/min

    for proj in projects:
        try:
            async with get_session(db_name=proj.db_name) as proj_session:
                # Count recent messages
                m_count = (await proj_session.execute(
                    select(func.count(Message.id)).where(Message.created_at >= one_min_ago)
                )).scalar() or 0
                total_ingestion += m_count

                # Count recent extractions
                e_count = (await proj_session.execute(
                    select(func.count(ExtractionLog.id)).where(ExtractionLog.created_at >= one_min_ago)
                )).scalar() or 0
                total_extraction += e_count

                # Count recent embeddings
                v_count = (await proj_session.execute(
                    select(func.count(MessageEmbedding.id)).where(MessageEmbedding.created_at >= one_min_ago)
                )).scalar() or 0
                total_embeddings += v_count
        except Exception:
            continue

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
    from src.db.models import Message, Contact, SystemProject

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
