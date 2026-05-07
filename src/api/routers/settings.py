from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.core.config import SettingsService
from src.core.config import get_settings
from src.api.schemas import SettingUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])

# Known settings schema: key → {category, type, description, env_attr}
_KNOWN: dict[str, dict] = {
    # LLM
    "llm_provider":        {"category": "llm",        "type": "string", "description": "LLM provider (google | lmstudio)",             "env_attr": "llm_provider"},
    "google_llm_model":    {"category": "llm",        "type": "string", "description": "Google LLM model name",                         "env_attr": "google_llm_model"},
    "lmstudio_base_url":   {"category": "llm",        "type": "string", "description": "LMStudio API base URL",                         "env_attr": "lmstudio_base_url"},
    "lmstudio_llm_model":  {"category": "llm",        "type": "string", "description": "LMStudio model name",                           "env_attr": "lmstudio_llm_model"},
    "llm_temperature":     {"category": "llm",        "type": "float",  "description": "LLM sampling temperature (0.0 – 2.0)",          "env_attr": "llm_temperature"},
    "llm_max_tokens":      {"category": "llm",        "type": "int",    "description": "Max tokens per LLM request",                    "env_attr": "llm_max_tokens"},
    # Embeddings
    "embed_provider":      {"category": "embeddings", "type": "string", "description": "Embedding provider (google | lmstudio)",        "env_attr": "embed_provider"},
    "google_embed_model":  {"category": "embeddings", "type": "string", "description": "Google embedding model name",                   "env_attr": "google_embed_model"},
    "lmstudio_embed_model":{"category": "embeddings", "type": "string", "description": "LMStudio embedding model name",                 "env_attr": "lmstudio_embed_model"},
    "embed_dimensions":    {"category": "embeddings", "type": "int",    "description": "Embedding vector dimensions",                   "env_attr": "embed_dimensions"},
    # Whisper
    "whisper_url":         {"category": "whisper",    "type": "string", "description": "Whisper STT service URL",                       "env_attr": "whisper_url"},
    "whisper_model":       {"category": "whisper",    "type": "string", "description": "Whisper model size (tiny/base/small/medium/large)", "env_attr": "whisper_model"},
    "whisper_language":    {"category": "whisper",    "type": "string", "description": "Transcription language code or 'auto'",         "env_attr": "whisper_language"},
    # System
    "log_level":           {"category": "system",     "type": "string", "description": "Log level (DEBUG/INFO/WARNING/ERROR)",          "env_attr": "log_level"},
    "enable_metrics":      {"category": "system",     "type": "bool",   "description": "Enable Prometheus metrics collection",          "env_attr": "enable_metrics"},
    "enable_json_logging": {"category": "system",     "type": "bool",   "description": "Enable structured JSON log output",             "env_attr": "enable_json_logging"},
}


@router.get("")
async def list_settings(category: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List all settings."""
    svc = SettingsService(db)
    return {"settings": await svc.get_all(category=category)}


@router.get("/effective")
async def effective_settings(db: AsyncSession = Depends(get_db)):
    """Return all known settings merged: env defaults overridden by DB values."""
    cfg = get_settings()
    svc = SettingsService(db)
    db_rows = {s["key"]: s for s in await svc.get_all()}

    result = []
    for key, meta in _KNOWN.items():
        env_value = getattr(cfg, meta["env_attr"], None)
        db_entry = db_rows.get(key)
        result.append({
            "key": key,
            "value": db_entry["value"] if db_entry else env_value,
            "env_value": env_value,
            "value_type": meta["type"],
            "description": meta["description"],
            "category": meta["category"],
            "source": "db" if db_entry else "env",
            "updated_at": db_entry["updated_at"] if db_entry else None,
        })

    return {"settings": result}


@router.put("/{key}")
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """Update a setting."""
    svc = SettingsService(db)
    meta = _KNOWN.get(key, {})
    setting = await svc.set(
        key=key,
        value=data.value,
        value_type=data.value_type or meta.get("type", "string"),
        description=data.description or meta.get("description"),
        category=data.category or meta.get("category", "general"),
    )
    return {"key": setting.key, "value": setting.get_typed_value()}


@router.delete("/{key}")
async def reset_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Delete a DB override — setting reverts to env default."""
    svc = SettingsService(db)
    existed = await svc.delete(key)
    if not existed:
        raise HTTPException(status_code=404, detail="Setting not in DB (already using env default)")
    return {"key": key, "source": "env"}
