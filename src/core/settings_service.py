"""Settings service — DB-backed config with priority over .env."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Setting


class SettingsService:
    """CRUD operations for the settings table. DB values override .env."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value, cast to its declared type."""
        result = await self.session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting is None:
            return default
        return setting.get_typed_value()

    async def set(self, key: str, value: Any, value_type: str = "string",
                  description: str | None = None, category: str = "general") -> Setting:
        """Set a setting value (upsert)."""
        result = await self.session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()

        str_value = json.dumps(value) if value_type == "json" else str(value)

        if setting:
            setting.value = str_value
            setting.value_type = value_type
            if description:
                setting.description = description
        else:
            setting = Setting(
                key=key,
                value=str_value,
                value_type=value_type,
                description=description or "",
                category=category,
            )
            self.session.add(setting)

        await self.session.flush()
        return setting

    async def get_all(self, category: Optional[str] = None) -> list[dict]:
        """Get all settings, optionally filtered by category."""
        query = select(Setting)
        if category:
            query = query.where(Setting.category == category)
        query = query.order_by(Setting.category, Setting.key)

        result = await self.session.execute(query)
        settings = result.scalars().all()

        return [
            {
                "key": s.key,
                "value": s.get_typed_value(),
                "raw_value": s.value,
                "value_type": s.value_type,
                "description": s.description,
                "category": s.category,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in settings
        ]

    async def delete(self, key: str) -> bool:
        """Delete a setting. Returns True if it existed."""
        result = await self.session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            await self.session.delete(setting)
            await self.session.flush()
            return True
        return False
