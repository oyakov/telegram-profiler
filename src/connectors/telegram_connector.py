"""Telegram connector — Telethon-based sync with listener and polling."""

from __future__ import annotations

import os
import structlog
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.connectors.base import BaseConnector, SyncResult
from src.connectors.whisper_client import WhisperClient
from src.core.config import get_settings
from src.db.database import get_session
from src.db.models import Contact, Message, SyncState, VoiceNote, MessageContact

from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel, Chat, MessageMediaDocument

logger = structlog.get_logger()


class TelegramConnector(BaseConnector):
    """Telegram data connector using Telethon."""

    name = "telegram"

    def __init__(self, enable_transcription: bool = False, db_name: str | None = None):
        self.settings = get_settings()
        self.whisper = WhisperClient()
        self.enable_transcription = enable_transcription
        self.db_name = db_name or os.getenv('POSTGRES_DB', 'crm')

    def _get_client(self):
        """Create a new Telethon client instance."""
        from telethon import TelegramClient
        
        # Determine the base session name
        session_name = self.settings.telegram_session_name
        
        # Use the base session name for all databases to avoid re-authorization
        session_name = self.settings.telegram_session_name
        
        docker_path = f"/app/sessions/{session_name}"
        local_path = f"sessions/{session_name}"
        session_path = docker_path if os.path.exists("/app") else local_path
        os.makedirs(os.path.dirname(session_path), exist_ok=True)
        return TelegramClient(session_path, int(self.settings.telegram_api_id), self.settings.telegram_api_hash)


    async def is_authorized(self) -> bool:
        client = self._get_client()
        await client.connect()
        try:
            return await client.is_user_authorized()
        finally:
            await client.disconnect()

    async def send_code_request(self, phone: str) -> str:
        client = self._get_client()
        await client.connect()
        try:
            result = await client.send_code_request(phone)
            return result.phone_code_hash
        finally:
            await client.disconnect()

    async def sign_in(self, phone: str, code: str, phone_code_hash: str) -> dict:
        from telethon.errors import SessionPasswordNeededError
        client = self._get_client()
        await client.connect()
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            return {"status": "success"}
        except SessionPasswordNeededError:
            return {"status": "requires_2fa"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await client.disconnect()

    async def sign_in_2fa(self, password: str) -> dict:
        client = self._get_client()
        await client.connect()
        try:
            await client.sign_in(password=password)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await client.disconnect()

    async def logout(self):
        client = self._get_client()
        await client.connect()
        try:
            await client.log_out()
        finally:
            await client.disconnect()

    async def sync(self, chat_ids: list[int] | None = None, limit: int = 100, offset_date: datetime | None = None, **kwargs) -> SyncResult:
        result = SyncResult(connector=self.name, started_at=datetime.now(timezone.utc))
        client = self._get_client()
        try:
            async with client:
                if not await client.is_user_authorized():
                    result.status = "error"; result.errors.append("Not authorized"); return result
                async with get_session(db_name=self.db_name) as session:
                    sync_state = await self._get_sync_state(session)
                    sync_state.status = "running"
                    await session.commit()
                    
                    # Fetch tracked channels from new model
                    from src.db.models import TrackedChannel
                    res = await session.execute(select(TrackedChannel.telegram_id).where(TrackedChannel.is_active == True))
                    target_ids = [int(row[0]) for row in res.all()]
                    
                    if not target_ids:
                        # Fallback for DMs if no tracked channels
                        dialogs = await client.get_dialogs(); target_ids = [d.id for d in dialogs if d.is_user]
                    
                    for target_id in target_ids:
                        try:
                            count = await self._sync_chat(client, session, target_id, limit, sync_state, offset_date=offset_date)
                            result.messages_fetched += count
                        except Exception as e: logger.error("telegram_sync_error", target_id=target_id, error=str(e))
                    sync_state = await self._get_sync_state(session)
                    sync_state.last_sync_at = datetime.now(timezone.utc); sync_state.status = "idle"; await session.commit()
        except Exception as e:
            result.status = "error"; result.errors.append(str(e))
        result.completed_at = datetime.now(timezone.utc)
        return result


    async def deep_sync(self, chat_ids: list[str | int], limit: int = 500, days: int = 90) -> SyncResult:
        """Fetch historical messages from specific chats/channels."""
        result = SyncResult(connector=self.name, started_at=datetime.now(timezone.utc))
        min_date = datetime.now(timezone.utc) - timedelta(days=days)
        client = self._get_client()
        try:
            async with client:
                if not await client.is_user_authorized():
                    result.status = "error"; result.errors.append("Not authorized"); return result
                async with get_session(db_name=self.db_name) as session:
                    for chat_id in chat_ids:
                        try:
                            # For deep sync we want to fetch up to 'limit' messages, 
                            # but stop if we go further back than 'min_date'
                            count = await self._sync_chat(client, session, chat_id, limit, None, min_date=min_date)
                            result.messages_fetched += count

                            # Note: _sync_chat now updates last_sync_at automatically
                            await session.commit() 
                        except Exception as e: 
                            logger.error("telegram_deep_sync_error", chat_id=chat_id, error=str(e))
                            result.errors.append(f"{chat_id}: {str(e)}")
        except Exception as e:
            result.status = "error"; result.errors.append(str(e))
        result.completed_at = datetime.now(timezone.utc)
        return result

    async def enrich_contact(self, contact_id: str) -> bool:
        """Fetch full profile info (bio, photo) for a contact."""
        async with get_session(db_name=self.db_name) as session:
            stmt = select(Contact).where(Contact.id == contact_id)
            result = await session.execute(stmt)
            contact = result.scalar_one_or_none()
            if not contact or not contact.telegram_id or contact.telegram_id == "system":
                return False

            client = self._get_client()
            try:
                async with client:
                    # Resolve entity
                    try:
                        entity = await client.get_entity(int(contact.telegram_id))
                    except ValueError:
                        entity = await client.get_entity(contact.telegram_id)
                    
                    # Get full info for bio
                    full_user = await client(GetFullUserRequest(id=entity))
                    contact.bio = full_user.full_user.about
                    
                    # Update other fields if they changed
                    contact.first_name = getattr(entity, "first_name", contact.first_name)
                    contact.last_name = getattr(entity, "last_name", contact.last_name)
                    contact.telegram_username = getattr(entity, "username", contact.telegram_username)
                    contact.is_bot = getattr(entity, "bot", False)
                    contact.is_verified = getattr(entity, "verified", False)
                    
                    # Download photo
                    photo_path = await self._download_photo(client, entity)
                    if photo_path:
                        contact.profile_photo_path = photo_path
                    
                    contact.last_enriched_at = datetime.now(timezone.utc)
                    await session.commit()
                    return True
            except Exception as e:
                logger.error("telegram_enrich_error", contact_id=contact_id, error=str(e))
                return False

    async def _download_photo(self, client, entity) -> str | None:
        """Download profile photo and return local path."""
        try:
            output_dir = Path("uploads/avatars")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Use entity ID as filename to keep it consistent
            filename = f"{entity.id}.jpg"
            file_path = output_dir / filename
            
            # Download
            path = await client.download_profile_photo(entity, file=str(file_path))
            if path:
                # Return relative path for web serving
                return f"uploads/avatars/{filename}"
            return None
        except Exception as e:
            logger.warning("telegram_photo_download_error", entity_id=entity.id, error=str(e))
            return None

    async def _sync_chat(self, client, session, chat_id, limit, sync_state, offset_date=None, min_date=None) -> int:
        try:
            # Handle string IDs that are numeric
            if isinstance(chat_id, str) and chat_id.lstrip('-').isdigit():
                chat_id = int(chat_id)
            entity = await client.get_entity(chat_id)
        except Exception:
            # Try with -100 prefix if it's a positive ID
            if isinstance(chat_id, int) and chat_id > 0:
                try:
                    entity = await client.get_entity(int(f"-100{chat_id}"))
                except Exception:
                    # Try as a string/username if it was an int but failed
                    entity = await client.get_entity(str(chat_id))
            else:
                raise

        is_channel = isinstance(entity, Channel) and entity.broadcast
        messages_synced = 0
        last_id = (sync_state.metadata_json or {}).get(f"chat_{entity.id}_last_id") if sync_state else 0
        async for msg in client.iter_messages(entity, limit=limit, min_id=last_id or 0, offset_date=offset_date):
            if min_date and msg.date < min_date:
                break
            existing = await session.execute(select(Message).where(Message.source_message_id == f"{entity.id}_{msg.id}"))
            if existing.scalar_one_or_none(): continue
            sender_entity = msg.sender or entity if not is_channel else entity
            contact = await self._get_or_create_contact(session, sender_entity, is_channel=is_channel)
            content = msg.text or ""
            message = Message(contact_id=contact.id, source="telegram", source_message_id=f"{entity.id}_{msg.id}",
                            direction="outgoing" if msg.out else "incoming", content=content, group_id=str(entity.id),
                            group_name=getattr(entity, "title", "Unknown"), timestamp=msg.date)
            session.add(message)
            session.add(MessageContact(message=message, contact=contact, role="sender"))
            messages_synced += 1
        
        # Update TrackedChannel status
        from src.db.models import TrackedChannel
        await session.execute(
            update(TrackedChannel)
            .where(TrackedChannel.telegram_id == str(entity.id))
            .values(last_sync_at=datetime.now(timezone.utc))
        )
        
        await session.flush()
        return messages_synced

    async def _get_or_create_contact(self, session, sender, is_channel=False) -> Contact:
        if sender is None: return Contact(first_name="System", telegram_id="system", source="telegram")
        tg_id = str(sender.id)
        result = await session.execute(select(Contact).where(Contact.telegram_id == tg_id).limit(1))
        contact = result.scalar_one_or_none()
        if not contact:
            contact = Contact(first_name=getattr(sender, "title", "Unknown") if is_channel else getattr(sender, "first_name", ""),
                            telegram_id=tg_id, telegram_username=getattr(sender, "username", None), source="telegram")
            session.add(contact); await session.flush()
        return contact

    async def _get_sync_state(self, session) -> SyncState:
        result = await session.execute(select(SyncState).where(SyncState.connector == self.name))
        state = result.scalar_one_or_none()
        if not state: state = SyncState(connector=self.name, status="idle"); session.add(state); await session.flush()
        return state

    async def search_communities(self, query: str, limit: int = 50) -> list[dict]:
        from telethon.tl.functions.contacts import SearchRequest
        from telethon.tl.functions.channels import GetFullChannelRequest
        from telethon.tl.types import Channel, Chat
        client = self._get_client()
        communities = []
        try:
            async with client:
                if not await client.is_user_authorized(): return []
                monitored_ids = set()
                async with get_session(db_name=self.db_name) as session:
                    res = await session.execute(select(Message.group_id).distinct())
                    monitored_ids = {str(row[0]) for row in res.all() if row[0]}
                result = await client(SearchRequest(q=query, limit=limit))
                for chat in result.chats:
                    if str(chat.id) in monitored_ids: continue
                    is_channel = isinstance(chat, Channel) and chat.broadcast
                    if not (is_channel or isinstance(chat, (Channel, Chat))): continue
                    participants = 0; about = ""
                    try:
                        if is_channel:
                            full = await client(GetFullChannelRequest(channel=chat))
                            participants = getattr(full.full_chat, 'participants_count', 0); about = getattr(full.full_chat, 'about', "")
                    except Exception: pass
                    communities.append({"id": chat.id, "title": getattr(chat, "title", "Unknown"), "username": getattr(chat, "username", None),
                                      "participants": participants, "about": about})
                communities.sort(key=lambda x: x["participants"], reverse=True)
                return communities
        except Exception as e: logger.error("telegram_search_error", error=str(e)); return []

    async def join_community(self, chat_id, username=None, folder_name=None) -> tuple[bool, Any]:
        from telethon.tl.functions.channels import JoinChannelRequest
        client = self._get_client()
        try:
            async with client:
                identifier = username if username else chat_id
                if isinstance(identifier, str) and identifier.lstrip('-').isdigit(): identifier = int(identifier)
                try: entity = await client.get_entity(identifier)
                except Exception:
                    if isinstance(identifier, int) and identifier > 0: entity = await client.get_entity(int(f"-100{identifier}"))
                    else: raise
                await client(JoinChannelRequest(entity))
                await self._mute_entity(client, entity)
                # Determine target folder
                target_folder = folder_name
                if not target_folder:
                    target_folder = os.getenv("TARGET_FOLDER", "BG Intel")
                    if self.db_name == "crm_crypto":
                        target_folder = "Crypto"
                
                await self._add_to_folder(client, entity, folder_name=target_folder)
                return True, entity
        except Exception as e: logger.error("telegram_join_error", error=str(e)); return False, None

    async def _mute_entity(self, client, entity):
        from telethon.tl.functions.account import UpdateNotifySettingsRequest
        from telethon.tl.types import InputPeerNotifySettings, InputNotifyPeer
        try:
            peer = await client.get_input_entity(entity)
            await client(UpdateNotifySettingsRequest(
                peer=InputNotifyPeer(peer),
                settings=InputPeerNotifySettings(mute_until=2147483647)
            ))
        except Exception as e: logger.warning("telegram_mute_error", error=str(e))

    async def _add_to_folder(self, client, entity, folder_name):
        from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
        from telethon.tl.types import DialogFilter
        try:
            # Use input entity for all operations
            peer = await client.get_input_entity(entity)
            res = await client(GetDialogFiltersRequest())
            filters = res.filters if hasattr(res, 'filters') else res
            
            def get_title(f):
                t = getattr(f, 'title', '')
                return t.text if hasattr(t, 'text') else str(t)

            target = next((f for f in filters if isinstance(f, DialogFilter) and get_title(f) == folder_name), None)
            
            if target:
                # Store the IDs already in folder to avoid duplicates
                from telethon.utils import get_peer_id
                current_ids = {get_peer_id(p) for p in target.include_peers}
                new_peer_id = get_peer_id(peer)
                
                if new_peer_id not in current_ids:
                    target.include_peers.append(peer)
                    await client(UpdateDialogFilterRequest(id=target.id, filter=target))
            else:
                nid = max([f.id for f in filters if hasattr(f, 'id')] + [10]) + 1
                await client(UpdateDialogFilterRequest(id=nid, filter=DialogFilter(
                    id=nid, title=folder_name, include_peers=[peer], 
                    pinned_peers=[], exclude_peers=[], emoticon="🧠"
                )))
            logger.info("telegram_added_to_folder", folder=folder_name)
        except Exception as e: logger.warning("telegram_folder_error", error=str(e))

    async def list_telegram_folders(self) -> list[dict]:
        """Return list of Telegram dialog filters (folders) with their channel IDs."""
        from telethon.tl.functions.messages import GetDialogFiltersRequest
        from telethon.tl.types import DialogFilter
        from telethon.utils import get_peer_id
        client = self._get_client()
        await client.connect()
        try:
            if not await client.is_user_authorized():
                return []
            res = await client(GetDialogFiltersRequest())
            filters = res.filters if hasattr(res, 'filters') else res
            result = []
            for f in filters:
                if not isinstance(f, DialogFilter):
                    continue
                title = f.title
                if hasattr(title, 'text'):
                    title = title.text
                peer_ids = []
                for peer in f.include_peers:
                    try:
                        peer_ids.append(str(abs(get_peer_id(peer))))
                    except Exception:
                        pass
                result.append({"name": title, "id": f.id, "channel_count": len(peer_ids), "peer_ids": peer_ids})
            return result
        finally:
            await client.disconnect()

    async def import_folder_channels(self, peer_ids: list[str]) -> list[dict]:
        """Resolve peer IDs to channel info (title, username, type)."""
        from telethon.tl.types import Channel, Chat
        client = self._get_client()
        await client.connect()
        try:
            if not await client.is_user_authorized():
                return []
            channels = []
            for pid in peer_ids:
                try:
                    # Try as negative channel id first
                    entity = await client.get_entity(int(f"-100{pid}"))
                except Exception:
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
                    "entity_type": "channel" if is_channel else "group",
                })
            return channels
        finally:
            await client.disconnect()

    async def reorganize_all_tracked(self, folder_name=None) -> dict:
        folder_name = folder_name or os.getenv("TARGET_FOLDER", "BG Intel")
        from src.core.config import SettingsService
        from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
        from telethon.tl.types import DialogFilter
        stats = {"muted": 0, "moved": 0, "errors": 0}
        async with get_session(db_name=self.db_name) as session:
            svc = SettingsService(session)
            ids = list(set(await svc.get("telegram_channel_whitelist", []) + await svc.get("telegram_chat_whitelist", [])))
        if not ids: return stats
        client = self._get_client()
        try:
            async with client:
                if not await client.is_user_authorized(): return {"error": "Not authorized"}
                input_peers = []
                for cid in ids:
                    try:
                        ident = int(cid) if str(cid).lstrip('-').isdigit() else cid
                        peer = await client.get_input_entity(ident)
                        input_peers.append(peer)
                        # Mute using existing method
                        await self._mute_entity(client, peer)
                        stats["muted"] += 1
                    except Exception: stats["errors"] += 1
                
                if not input_peers: return stats
                
                res = await client(GetDialogFiltersRequest())
                filters = res.filters if hasattr(res, 'filters') else res
                def get_title(f):
                    t = getattr(f, 'title', '')
                    return t.text if hasattr(t, 'text') else str(t)

                target = next((f for f in filters if isinstance(f, DialogFilter) and get_title(f) == folder_name), None)
                
                if target:
                    from telethon.utils import get_peer_id
                    current_ids = {get_peer_id(p) for p in target.include_peers}
                    for p in input_peers:
                        if get_peer_id(p) not in current_ids: target.include_peers.append(p)
                    await client(UpdateDialogFilterRequest(id=target.id, filter=target))
                else:
                    nid = max([f.id for f in filters if hasattr(f, 'id')] + [10]) + 1
                    await client(UpdateDialogFilterRequest(id=nid, filter=DialogFilter(
                        id=nid, title=folder_name, include_peers=input_peers, 
                        pinned_peers=[], exclude_peers=[], emoticon="🧠"
                    )))
                stats["moved"] = len(input_peers); return stats
        except Exception as e: logger.error("reorganize_error", error=str(e)); return {"error": str(e)}

    async def get_status(self) -> dict[str, Any]:
        async with get_session(db_name=self.db_name) as session:
            state = await self._get_sync_state(session)
            return {
                "connector": self.name,
                "status": state.status,
                "last_sync_at": state.last_sync_at.isoformat() if state.last_sync_at else None,
                "messages_fetched": state.metadata_json.get("messages_fetched", 0) if state.metadata_json else 0,
                "error_message": state.error_message,
            }

    async def test_connection(self) -> bool:
        try:
            async with self._get_client() as client: return (await client.get_me()) is not None
        except Exception: return False
