import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.types import DialogFilter, Channel, Chat, InputFolderPeer
from telethon.tl.functions.folders import EditPeerFoldersRequest
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.types import InputPeerNotifySettings, InputNotifyPeer
from sqlalchemy import select, update

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.pipeline.tasks import deep_sync_telegram
from src.core.config import get_settings
from src.db.models import TrackedFolder, TrackedChannel

async def sync_folder(client, session, tg_filter, db_name):
    title = tg_filter.title.text if hasattr(tg_filter.title, 'text') else str(tg_filter.title)
    print(f"\nProcessing folder: '{title}'...")
    
    # 1. Get or create folder in DB
    res = await session.execute(select(TrackedFolder).where(TrackedFolder.name == title))
    folder = res.scalar_one_or_none()
    if not folder:
        print(f"  - Creating new folder in DB: {title}")
        folder = TrackedFolder(name=title)
        session.add(folder)
        await session.flush()
    
    # 2. Resolve peers in folder
    print(f"  - Resolving {len(tg_filter.include_peers)} items...")
    peers_data = []
    input_peers = []
    for peer in tg_filter.include_peers:
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
        except Exception as e:
            print(f"    - Skipping peer {peer}: {e}")

    # 3. Mute all (as per existing project patterns)
    for p in input_peers:
        try:
            await client(UpdateNotifySettingsRequest(
                peer=InputNotifyPeer(p),
                settings=InputPeerNotifySettings(mute_until=2147483647)
            ))
        except Exception: pass

    # 4. Update channels in DB
    print(f"  - Updating {len(peers_data)} channels in DB...")
    current_tg_ids = {p["id"] for p in peers_data}
    
    # Get currently active IDs for this folder in DB
    res = await session.execute(
        select(TrackedChannel.telegram_id)
        .where(TrackedChannel.folder_id == folder.id)
        .where(TrackedChannel.is_active == True)
    )
    old_active_ids = {row[0] for row in res.all()}
    
    new_ids = []
    for p_data in peers_data:
        tg_id = p_data["id"]
        res = await session.execute(select(TrackedChannel).where(TrackedChannel.telegram_id == tg_id))
        chan = res.scalar_one_or_none()
        
        if not chan:
            chan = TrackedChannel(
                telegram_id=tg_id,
                folder_id=folder.id,
                title=p_data["title"],
                username=p_data["username"],
                entity_type=p_data["type"],
                is_active=True
            )
            session.add(chan)
            new_ids.append(tg_id)
        else:
            chan.folder_id = folder.id
            chan.title = p_data["title"]
            chan.username = p_data["username"]
            chan.is_active = True
            
    # 5. Deactivate removed channels
    removed_ids = old_active_ids - current_tg_ids
    if removed_ids:
        print(f"  - Deactivating {len(removed_ids)} removed channels...")
        await session.execute(
            update(TrackedChannel)
            .where(TrackedChannel.telegram_id.in_(list(removed_ids)))
            .where(TrackedChannel.folder_id == folder.id)
            .values(is_active=False)
        )
    
    await session.flush()
    return new_ids

import re

def sanitize_db_name(folder_name: str) -> str:
    """Convert folder name to a valid PostgreSQL database name with 'crm_' prefix."""
    # Convert to lowercase
    name = folder_name.lower()
    # Replace spaces, dashes and special chars with underscores
    name = re.sub(r'[^a-z0-t0-9]', '_', name)
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name)
    # Strip underscores from ends
    name = name.strip('_')
    return f"crm_{name}"

async def main():
    settings = get_settings()
    client = TelegramClient(f"sessions/{settings.telegram_session_name}", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    async with client:
        print("Reading all folders from Telegram...")
        res = await client(GetDialogFiltersRequest())
        filters = res.filters if hasattr(res, 'filters') else res
        
        def get_title(f):
            t = getattr(f, 'title', '')
            return t.text if hasattr(t, 'text') else str(t)

        # Filter BG folders and Crypto
        target_filters = [
            f for f in filters 
            if isinstance(f, DialogFilter) and (get_title(f).startswith("BG") or get_title(f) == "Crypto")
        ]
        
        print(f"Found {len(target_filters)} target folders.")
        
        from src.db.database import ensure_database_exists, init_database_schema
        
        for tf in target_filters:
            folder_title = get_title(tf)
            db_name = sanitize_db_name(folder_title)
            
            print(f"\n>>> SYNCING FOLDER: '{folder_title}' -> DATABASE: '{db_name}'")
            
            # Ensure DB exists and is initialized
            await ensure_database_exists(db_name)
            await init_database_schema(db_name)
            
            async with get_session(db_name=db_name) as session:
                new_ids = await sync_folder(client, session, tf, db_name)
                
                if new_ids:
                    print(f"  - Triggering historical sync for {len(new_ids)} new channels...")
                    try:
                        if not os.path.exists('/.dockerenv'):
                            os.environ["REDIS_URL"] = os.getenv("REDIS_URL", "").replace("redis://redis:", "redis://localhost:")
                        deep_sync_telegram.delay(
                            chat_ids=new_ids,
                            limit=10000,
                            days=365,
                            db_name=db_name
                        )
                    except Exception as e:
                        print(f"  - Warning: Could not trigger historical sync: {e}")

        print(f"\nFinal Success! All target folders synced to dedicated databases.")

if __name__ == "__main__":
    asyncio.run(main())
