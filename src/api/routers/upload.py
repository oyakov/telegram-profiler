import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException

router = APIRouter(prefix="/upload", tags=["Upload"])

@router.post("/excel")
async def upload_excel(file: UploadFile = File(...)):
    """Upload an Excel/CSV file for import."""
    allowed = {".xlsx", ".xls", ".csv", ".tsv"}
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in allowed: raise HTTPException(400, f"Unsupported file type: {ext}")
    
    upload_dir = Path("/app/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = upload_dir / filename
    
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    from src.pipeline.tasks import import_excel
    result = import_excel.delay(file_path=str(filepath))
    
    return {"task_id": result.id, "filename": filename, "status": "queued"}

@router.post("/audio")
async def upload_audio(file: UploadFile = File(...), contact_id: Optional[str] = None):
    """Upload a voice note for transcription."""
    upload_dir = Path("/app/uploads/voice")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = upload_dir / filename
    
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    from src.connectors.whisper_client import WhisperClient
    whisper = WhisperClient()
    transcript = await whisper.transcribe(filepath)
    
    return {
        "filename": filename,
        "transcript": transcript,
        "contact_id": contact_id,
    }
