"""Telegram management service implementation (folders, channel imports)."""

import structlog
from typing import List
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.types import DialogFilter, Channel, Chat
from telethon.utils import get_peer_id
from src.services.telegram.base import TelegramManagementInterface
from src.services.telegram.client_factory import TelegramClientFactory

logger = structlog.get_logger()

class TelegramManagementService(TelegramManagementInterface):
    """Handles Telegram folder and channel management."""

    def __init__(self, client_factory: TelegramClientFactory):
        self.factory = client_factory

    async def list_folders(self) -> List[dict]:
        """List Telegram folders for the current user."""
        client = await self.factory.get_client()
        try:
            async with client:
                res = await client(GetDialogFiltersRequest())
                filters = res.filters if hasattr(res, 'filters') else res
                result = []
                for f in filters:
                    if not isinstance(f, DialogFilter): continue
                    title = f.title.text if hasattr(f.title, 'text') else str(f.title)
                    peer_ids = [str(abs(get_peer_id(p))) for p in f.include_peers]
                    result.append({
                        "name": title, 
                        "id": f.id, 
                        "channel_count": len(peer_ids), 
                        "peer_ids": peer_ids
                    })
                return result
        except Exception as e:
            logger.error("list_folders_error", error=str(e))
            return []

    async def import_folder_channels(self, peer_ids: List[str]) -> List[dict]:
        """Resolve a list of peer IDs to channel/group info."""
        client = await self.factory.get_client()
        try:
            async with client:
                channels = []
                for pid in peer_ids:
                    try: 
                        entity = await client.get_entity(-int(pid))
                    except Exception:
                        try: 
                            entity = await client.get_entity(int(pid))
                        except Exception: 
                            continue
                    
                    if not isinstance(entity, (Channel, Chat)): 
                        continue
                        
                    is_channel = isinstance(entity, Channel) and entity.broadcast
                    channels.append({
                        "telegram_id": str(entity.id), 
                        "title": getattr(entity, "title", "Unknown"),
                        "username": getattr(entity, "username", None), 
                        "entity_type": "channel" if is_channel else "group"
                    })
                return channels
        except Exception as e:
            logger.error("import_folder_channels_error", error=str(e))
            return []
