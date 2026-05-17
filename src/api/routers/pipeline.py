"""Unified import/sync pipeline router — consolidates uploads and connector sync."""

from __future__ import annotations

import uuid
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import SyncState

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

# ========== Upload/Import Endpoints ==========

@router.post("/import/excel")
async def import_excel_file(file: UploadFile = File(...)):
    """Upload an Excel/CSV file for import."""
    allowed = {".xlsx", ".xls", ".csv", ".tsv"}
    raw_name = (file.filename or "").replace("\x00", "")  # strip null bytes
    ext = Path(raw_name).suffix.lower() if raw_name else ""
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    upload_dir = Path("/app/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(raw_name).name if raw_name else "upload"
    filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    filepath = upload_dir / filename

    contents = await file.read()
    await asyncio.get_running_loop().run_in_executor(None, filepath.write_bytes, contents)

    from src.pipeline.tasks import import_excel
    result = import_excel.delay(file_path=str(filepath))

    return {"task_id": result.id, "filename": filename, "status": "queued"}


@router.post("/import/audio")
async def import_audio_file(file: UploadFile = File(...), contact_id: Optional[str] = None):
    """Upload a voice note for transcription."""
    upload_dir = Path("/app/uploads/voice")
    upload_dir.mkdir(parents=True, exist_ok=True)

    raw_name = (file.filename or "").replace("\x00", "")  # strip null bytes
    safe_name = Path(raw_name).name if raw_name else "upload"
    filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    filepath = upload_dir / filename

    contents = await file.read()
    await asyncio.get_running_loop().run_in_executor(None, filepath.write_bytes, contents)

    from src.connectors.audio import AudioProcessor
    processor = AudioProcessor()
    transcript = await processor.transcribe(filepath)

    return {
        "filename": filename,
        "transcript": transcript,
        "contact_id": contact_id,
    }


# ========== Connector Sync Endpoints ==========

@router.post("/sync/{connector}")
async def trigger_sync(connector: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Manually trigger a connector sync."""
    from src.db.database import _DB_NAME_RE
    db_name = request.headers.get("X-Database") or None
    if db_name is not None and not _DB_NAME_RE.match(db_name):
        raise HTTPException(400, "Invalid X-Database header value")
    from src.pipeline.tasks import import_excel, sync_crm, sync_telegram
    from datetime import datetime, timezone

    task_map = {"telegram": sync_telegram, "excel": import_excel, "crm": sync_crm}
    task_fn = task_map.get(connector)
    if not task_fn:
        raise HTTPException(400, f"Unknown connector: {connector}")

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


@router.get("/sync/status")
async def connector_status(db: AsyncSession = Depends(get_db)):
    """Get status of all connectors."""
    result = await db.execute(select(SyncState))
    states = result.scalars().all()
    return {
        "connectors": [
            {
                "connector": s.connector,
                "status": s.status,
                "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
                "messages_fetched": s.metadata_json.get("messages_fetched", 0) if s.metadata_json else 0,
                "error_message": s.error_message,
            }
            for s in states
        ]
    }
