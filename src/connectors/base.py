"""Base connector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class SyncResult:
    """Result of a connector sync operation."""
    connector: str
    status: str = "success"  # success | error | partial
    messages_fetched: int = 0
    contacts_created: int = 0
    contacts_updated: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """Abstract base for all data connectors."""

    name: str = "base"

    @abstractmethod
    async def sync(self, **kwargs) -> SyncResult:
        """Run the sync operation. Returns a SyncResult."""
        ...

    @abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """Return current status of the connector."""
        ...

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connector can reach its data source."""
        ...
