"""Interfaces for marketing and delivery services."""

from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseDeliveryProvider(ABC):
    """Base interface for message delivery (Telegram, Email, etc.)."""
    
    @abstractmethod
    async def send_message(self, recipient_id: str, text: str) -> bool:
        """Send a message to a recipient."""
        pass

class PersonalizerInterface(ABC):
    """Interface for message personalization."""
    
    @abstractmethod
    def personalize(self, template: str, context: dict) -> str:
        """Personalize a message template using the provided context."""
        pass
