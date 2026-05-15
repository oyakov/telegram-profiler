"""External data source connectors — CRM, social platforms, and REST APIs."""

from __future__ import annotations

import structlog
import os
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.connectors.base import BaseConnector, SyncResult
from src.core.config import SettingsService
from src.db.database import get_session
from src.db.models import Contact, SyncState

logger = structlog.get_logger()


class ExternalConnector(BaseConnector):
    """Unified connector for external REST APIs and integrations."""

    def __init__(
        self,
        connector_type: Literal["crm", "social"] = "crm",
        db_name: str | None = None,
        project_id: str | None = None,
    ):
        self.connector_type = connector_type
        self.name = connector_type
        from src.core.config import get_settings
        self.db_name = db_name or get_settings().postgres_db
        self.project_id = project_id

    async def sync(self, **kwargs) -> SyncResult:
        """Sync data from external source."""
        if self.connector_type == "crm":
            return await self._sync_crm(**kwargs)
        elif self.connector_type == "social":
            return await self._sync_social(**kwargs)
        return SyncResult(
            connector=self.name,
            status="error",
            errors=[f"Unknown connector type: {self.connector_type}"],
        )

    async def _sync_crm(self, **kwargs) -> SyncResult:
        """Sync contacts from external CRM API."""
        result = SyncResult(connector=self.name, started_at=datetime.now(timezone.utc))

        try:
            async with get_session(db_name=self.db_name) as session:
                svc = SettingsService(session)

                api_url = await svc.get("crm_api_url", "")
                api_key = await svc.get("crm_api_key", "")

                if not api_url:
                    result.status = "error"
                    result.errors.append("CRM API URL not configured")
                    return result

                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{api_url.rstrip('/')}/contacts",
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()

                contacts_list = (
                    data
                    if isinstance(data, list)
                    else data.get("contacts", data.get("data", []))
                )

                for item in contacts_list:
                    try:
                        await self._upsert_contact(session, item)
                        result.contacts_created += 1
                    except Exception as e:
                        result.errors.append(f"Contact import error: {str(e)}")

                # Update sync state
                sync_state = await self._get_or_create_state(session)
                sync_state.last_sync_at = datetime.now(timezone.utc)
                sync_state.status = "idle"
                await session.commit()

        except Exception as e:
            result.status = "error"
            result.errors.append(str(e))
            logger.error("external_sync_error", connector=self.name, error=str(e))

        result.completed_at = datetime.now(timezone.utc)
        return result

    async def _sync_social(self, **kwargs) -> SyncResult:
        """Sync from social platforms (Apify-based stub)."""
        logger.warning(
            "social_connector_stub",
            message="Social connector not yet implemented",
        )
        return SyncResult(
            connector=self.name,
            status="error",
            errors=["Social connector is a stub — configure Apify API key to enable"],
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

    async def _upsert_contact(self, session: AsyncSession, data: dict):
        """Insert or update a contact from external source data."""
        email = data.get("email")
        if email:
            res = await session.execute(
                select(Contact).where(Contact.email == email).limit(1)
            )
            existing = res.scalar_one_or_none()
            if existing:
                for field in ["first_name", "last_name", "company", "position", "phone"]:
                    val = data.get(field)
                    if val and not getattr(existing, field, None):
                        setattr(existing, field, val)
                existing.embedding_dirty = True
                return

        contact = Contact(
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            company=data.get("company"),
            position=data.get("position"),
            email=data.get("email"),
            phone=data.get("phone"),
            source=self.connector_type,
            embedding_dirty=True,
        )
        session.add(contact)

    async def _get_or_create_state(self, session: AsyncSession) -> SyncState:
        res = await session.execute(
            select(SyncState).where(SyncState.connector == self.name)
        )
        state = res.scalar_one_or_none()
        if not state:
            state = SyncState(connector=self.name, status="idle")
            session.add(state)
            await session.flush()
        return state

    async def get_status(self) -> dict[str, Any]:
        """Get connector status."""
        async with get_session(db_name=self.db_name) as session:
            state = await self._get_or_create_state(session)
            return {
                "connector": self.name,
                "status": state.status,
                "last_sync_at": state.last_sync_at.isoformat() if state.last_sync_at else None,
            }

    async def test_connection(self) -> bool:
        """Test connectivity to external source."""
        try:
            async with get_session(db_name=self.db_name) as session:
                svc = SettingsService(session)

                if self.connector_type == "crm":
                    api_url = await svc.get("crm_api_url", "")
                    api_key = await svc.get("crm_api_key", "")

                    if not api_url:
                        return False

                    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(api_url, headers=headers)
                        return response.status_code < 500
                elif self.connector_type == "social":
                    return False
        except Exception:
            return False
