from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.db.models import SyncState

router = APIRouter(prefix="/connectors", tags=["Connectors"])

@router.post("/{connector}/sync")
async def trigger_sync(connector: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Manually trigger a connector sync."""
    db_name = request.headers.get("X-Database")
    from src.pipeline.tasks import import_excel, sync_crm, sync_telegram
    from datetime import datetime, timezone

    task_map = {"telegram": sync_telegram, "excel": import_excel, "crm": sync_crm}
    task_fn = task_map.get(connector)
    if not task_fn: raise HTTPException(400, f"Unknown connector: {connector}")

    # Update status to running
    sync_state = await db.execute(select(SyncState).where(SyncState.connector == connector))
    state = sync_state.scalar()
    if state:
        state.status = "running"
        state.updated_at = datetime.now(timezone.utc)
    else:
        state = SyncState(connector=connector, status="running", updated_at=datetime.now(timezone.utc))
        db.add(state)
    await db.commit()

    result = task_fn.delay(db_name=db_name)
    return {"task_id": result.id, "connector": connector, "status": "queued"}

@router.get("/status")
async def connector_status(db: AsyncSession = Depends(get_db)):
    """Get status of all connectors."""
    result = await db.execute(select(SyncState))
    states = result.scalars().all()
    return {"connectors": [{"connector": s.connector, "status": s.status, "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None, "messages_fetched": s.metadata_json.get("messages_fetched", 0) if s.metadata_json else 0, "error_message": s.error_message} for s in states]}

