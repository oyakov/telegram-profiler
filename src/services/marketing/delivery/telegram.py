"""Telegram implementation of the delivery provider."""

import structlog
from src.services.marketing.base import BaseDeliveryProvider
from src.connectors.telegram_connector import TelegramConnector

logger = structlog.get_logger()

class TelegramDeliveryProvider(BaseDeliveryProvider):
    """Delivers messages via Telegram."""

    def __init__(self, connector: TelegramConnector):
        self.connector = connector

    async def send_message(self, recipient_id: str, text: str) -> bool:
        """Send message via TelegramConnector."""
        return await self.connector.send_message(recipient_id, text)
