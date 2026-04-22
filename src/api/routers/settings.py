from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.core.settings_service import SettingsService
from src.api.schemas import SettingUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("")
async def list_settings(category: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List all settings."""
    svc = SettingsService(db)
    return {"settings": await svc.get_all(category=category)}

@router.put("/{key}")
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """Update a setting."""
    svc = SettingsService(db)
    setting = await svc.set(
        key=key, value=data.value, value_type=data.value_type,
        description=data.description, category=data.category,
    )
    return {"key": setting.key, "value": setting.get_typed_value()}
