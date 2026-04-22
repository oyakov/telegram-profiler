"""Social media connector — stub for Apify-based scraping."""

from __future__ import annotations

import structlog
import os
from datetime import datetime, timezone
from typing import Any

from src.connectors.base import BaseConnector, SyncResult

logger = structlog.get_logger()


class SocialConnector(BaseConnector):
    """Social media scraping connector (Apify-based).

    This is a stub implementation. To enable:
    1. Get an Apify API key
    2. Configure actors for each platform
    3. Implement the scraping logic
    """

    name = "social"

    def __init__(self, db_name: str | None = None):
        self.db_name = db_name or os.getenv('POSTGRES_DB', 'crm')


    async def sync(self, **kwargs) -> SyncResult:
        logger.warning("social_connector_stub", message="Social connector not yet implemented")
        return SyncResult(
            connector=self.name,
            status="error",
            errors=["Social connector is a stub — configure Apify API key to enable"],
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

    async def get_status(self) -> dict[str, Any]:
        return {
            "connector": self.name,
            "status": "disabled",
            "message": "Stub — requires Apify API key",
        }

    async def test_connection(self) -> bool:
        return False
