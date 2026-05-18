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

# Maximum accepted file sizes.
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024   # 50 MB for spreadsheets
_MAX_AUDIO_BYTES = 25 * 1024 * 1024    # 25 MB for audio

_ALLOWED_AUDIO_EXTENSIONS = {".ogg", ".mp3", ".wav", ".m4a", ".flac", ".opus", ".aac"}

# ========== Upload/Import Endpoints ==========

@router.post("/import/excel")
async def import_excel_file(file: UploadFile = File(...), request: Request = None):
    """Upload an Excel/CSV file for import."""
    from src.db.database import _DB_NAME_RE
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

    # Read with a size cap to prevent OOM on unbounded uploads.
    contents = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large. Maximum size is 50 MB.")
    await asyncio.get_running_loop().run_in_executor(None, filepath.write_bytes, contents)

    # Pass the tenant DB name so the import task runs against the correct database.
    db_name = None
    if request is not None:
        raw_db = request.headers.get("X-Database") or None
        if raw_db is not None and not _DB_NAME_RE.match(raw_db):
            raise HTTPException(400, "Invalid X-Database header value")
        db_name = raw_db

    from src.pipeline.tasks import import_excel
    result = import_excel.delay(file_path=str(filepath), db_name=db_name)

    return {"task_id": result.id, "filename": filename, "status": "queued"}


@router.post("/import/audio")
async def import_audio_file(file: UploadFile = File(...), contact_id: Optional[str] = None):
    """Upload a voice note for transcription."""
    from uuid import UUID as _UUID

    # Validate contact_id if provided — avoids propagating an invalid string to downstream code.
    if contact_id is not None:
        try:
            _UUID(contact_id)
        except (ValueError, AttributeError):
            raise HTTPException(400, "Invalid contact_id format")

    raw_name = (file.filename or "").replace("\x00", "")  # strip null bytes
    ext = Path(raw_name).suffix.lower() if raw_name else ""
    if ext not in _ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(400, f"Unsupported audio type. Allowed: {', '.join(sorted(_ALLOWED_AUDIO_EXTENSIONS))}")

    upload_dir = Path("/app/uploads/voice")
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(raw_name).name if raw_name else "upload"
    filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    filepath = upload_dir / filename

    # Enforce size cap before writing to disk.
    contents = await file.read(_MAX_AUDIO_BYTES + 1)
    if len(contents) > _MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio file too large. Maximum size is 25 MB.")
    await asyncio.get_running_loop().run_in_executor(None, filepath.write_bytes, contents)

    from src.connectors.audio import AudioProcessor
    processor = AudioProcessor()
    transcript = await processor.transcribe(filepath)

    return {
        "filename": filename,
        "transcript": transcript,
        # contact_id is returned for the caller's convenience but is not stored
        # automatically — the caller must PATCH the contact with the transcript if needed.
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
