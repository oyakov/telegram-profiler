import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.types import DialogFilter, Channel, Chat, InputFolderPeer
from telethon.tl.functions.folders import EditPeerFoldersRequest
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.types import InputPeerNotifySettings, InputNotifyPeer
from sqlalchemy import select

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.pipeline.tasks import deep_sync_telegram
from src.core.config import get_settings
from src.db.models import TrackedFolder, TrackedChannel

async def main():
    db_name = os.getenv("POSTGRES_DB", "crm")
    folder_name = os.getenv("TARGET_FOLDER", "BG Intel")
    
    settings = get_settings()
    session_name = settings.telegram_session_name
    if db_name == "crm_crypto":
        session_name = f"{session_name}_crm_crypto"
    elif db_name != "crm":
        session_name = f"{session_name}_{db_name}"

    client = TelegramClient(f"sessions/{session_name}", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    async with client:
        print(f"Reading folder '{folder_name}' from Telegram...")
        res = await client(GetDialogFiltersRequest())
        filters = res.filters if hasattr(res, 'filters') else res
        
        def get_title(f):
            t = getattr(f, 'title', '')
            return t.text if hasattr(t, 'text') else str(t)

        target = next((f for f in filters if isinstance(f, DialogFilter) and get_title(f) == folder_name), None)
        
        if not target:
            print(f"Error: Folder '{folder_name}' not found.")
            return

        print(f"Found {len(target.include_peers)} items in folder. Resolving types...")
        
        input_peers = []
        peers_data = []
        
        for peer in target.include_peers:
            try:
                entity = await client.get_entity(peer)
                input_peer = await client.get_input_entity(entity)
                input_peers.append(input_peer)
                
                e_type = "channel" if isinstance(entity, Channel) and entity.broadcast else "group"
                peers_data.append({
                    "id": str(entity.id),
                    "title": getattr(entity, 'title', 'Unknown'),
                    "username": getattr(entity, 'username', None),
                    "type": e_type
                })
                print(f"  - Verified: {peers_data[-1]['title']} (ID: {peers_data[-1]['id']}, Type: {e_type})")
            except Exception as e:
                print(f"  - Skipping peer: {e}")

        # 1. Ensure all are unarchived
        print("\n1. Ensuring all are unarchived...")
        folder_peers = [InputFolderPeer(peer=p, folder_id=0) for p in input_peers]
        if folder_peers:
            try:
                await client(EditPeerFoldersRequest(folder_peers=folder_peers))
            except Exception as e:
                print(f"  - Could not unarchive all at once: {e}. Trying individually...")
                for fp in folder_peers:
                    try: await client(EditPeerFoldersRequest(folder_peers=[fp]))
                    except Exception: pass

        # 2. Ensure all are muted
        print("2. Ensuring all are muted...")
        for p in input_peers:
            try:
                await client(UpdateNotifySettingsRequest(
                    peer=InputNotifyPeer(p),
                    settings=InputPeerNotifySettings(mute_until=2147483647)
                ))
            except Exception: pass


        # 3. Update tracked entities in DB
        print("\n3. Updating tracked folders and channels in database...")
        async with get_session(db_name=db_name) as session:
            # Get or create folder
            res = await session.execute(select(TrackedFolder).where(TrackedFolder.name == folder_name))
            folder = res.scalar_one_or_none()
            if not folder:
                folder = TrackedFolder(name=folder_name)
                session.add(folder)
                await session.flush()
            
            # Get current tracked IDs for this folder
            res = await session.execute(select(TrackedChannel.telegram_id).where(TrackedChannel.folder_id == folder.id))
            old_ids = {row[0] for row in res.all()}
            
            new_ids = []
            for p_data in peers_data:
                tg_id = p_data["id"]
                # Upsert tracked channel
                res = await session.execute(select(TrackedChannel).where(TrackedChannel.telegram_id == tg_id))
                chan = res.scalar_one_or_none()
                
                if not chan:
                    chan = TrackedChannel(
                        telegram_id=tg_id,
                        folder_id=folder.id,
                        title=p_data["title"],
                        username=p_data["username"],
                        entity_type=p_data["type"]
                    )
                    session.add(chan)
                    new_ids.append(tg_id)
                else:
                    chan.folder_id = folder.id
                    chan.title = p_data["title"]
                    chan.username = p_data["username"]
                    chan.is_active = True

            await session.commit()
            
            print(f"Success! Database updated for {db_name}.")
            print(f"- Tracks Folder: {folder_name}")
            print(f"- Total Tracked Channels: {len(peers_data)} (New: {len(new_ids)})")

            if new_ids:
                print(f"\nTriggering historical sync (365 days) for {len(new_ids)} new channels...")
                deep_sync_telegram.delay(
                    chat_ids=new_ids,
                    limit=10000,
                    days=365,
                    db_name=db_name
                )

if __name__ == "__main__":
    asyncio.run(main())
