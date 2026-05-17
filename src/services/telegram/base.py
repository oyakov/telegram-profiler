"""Interfaces and base classes for Telegram services."""

from abc import ABC, abstractmethod
from typing import Any, Optional, List
from datetime import datetime

class TelegramAuthInterface(ABC):
    @abstractmethod
    async def is_authorized(self) -> bool:
        pass

    @abstractmethod
    async def send_code_request(self, phone: str) -> str:
        pass

    @abstractmethod
    async def sign_in(self, phone: str, code: str, phone_code_hash: str) -> dict:
        pass

class TelegramSyncInterface(ABC):
    @abstractmethod
    async def sync_recent(self, chat_ids: Optional[List[int]] = None, limit: int = 100) -> Any:
        pass

    @abstractmethod
    async def sync_historical(self, chat_id: int, limit: int = 1000, offset_date: Optional[datetime] = None) -> int:
        pass

class TelegramEntityInterface(ABC):
    @abstractmethod
    async def get_or_create_contact(self, session: Any, sender: Any, is_channel: bool = False) -> Any:
        pass

    @abstractmethod
    async def update_user_profile(self) -> None:
        pass

class TelegramManagementInterface(ABC):
    @abstractmethod
    async def list_folders(self) -> List[dict]:
        pass

    @abstractmethod
    async def import_folder_channels(self, peer_ids: List[str]) -> List[dict]:
        pass
