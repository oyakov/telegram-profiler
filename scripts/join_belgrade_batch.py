import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetDialogFiltersRequest, UpdateDialogFilterRequest
from telethon.tl.functions.folders import EditPeerFoldersRequest
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.types import DialogFilter, InputFolderPeer, InputPeerNotifySettings, InputNotifyPeer, Channel, Chat, TextWithEntities
from telethon.errors import FloodWaitError
from sqlalchemy import select

sys.path.append(os.getcwd())
from src.db.database import get_session
from src.db.models import TrackedChannel, TrackedFolder
from src.core.config import get_settings

async def main():
    settings = get_settings()
    client = TelegramClient("sessions/bg_discovery.session", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    # Список кандидатов (usernames)
    usernames = [
        "ruserbia", "sputniksrbija", "ponaehali_official", "serbia_news", "rs_vesti",
        "pets_belgrade", "vstrechi_v_belgrade", "serbia_biz", "news_serbia", "rs_vesti_chat",
        "rabota_v_serbii_daily", "poisk_serbia", "zhili_byli_serbia", "remont_serbia", "vnz_serbia_pro",
        "talents_serbia", "ohmybelgrade", "nekretnine_srb", "serbia_live_chat", "belgrade_petsitting",
        "adaptacija_bg", "beograd_notes", "belgrade_memes", "serbia_money_live", "selo_serbia",
        "visarun_ns", "oglasi_beograd_rus", "sw_serbia", "oglasi_srbija_private", "srbija_news_all",
        "dr_borisov_serbia", "askme_serbia", "vnz_guide_srb", "rent_belgrade_rs", "serbialive_vesti",
        "vnz_serbia_chat", "vnz_ip_serbia", "afisha_serbia", "serbialive_beograd_group"
    ]
    
    folder_name = "BG Intel"
    db_name = "crm"
    
    async with client:
        # 1. Получаем папку из Telegram
        res = await client(GetDialogFiltersRequest())
        filters = res.filters if hasattr(res, 'filters') else res
        def gtitle(f):
            t = getattr(f, 'title', '')
            return t.text if hasattr(t, 'text') else str(t)
        target_folder = next((f for f in filters if isinstance(f, DialogFilter) and gtitle(f) == folder_name), None)

        # 2. Получаем ID папки из DB
        async with get_session(db_name=db_name) as session:
            res = await session.execute(select(TrackedFolder).where(TrackedFolder.name == folder_name))
            folder_db = res.scalar_one_or_none()
            if not folder_db:
                folder_db = TrackedFolder(name=folder_name)
                session.add(folder_db); await session.flush()
            folder_id = folder_db.id

        print(f"Starting batch join for {len(usernames)} candidates...")

        for username in usernames:
            try:
                print(f"Processing @{username}...")
                entity = await client.get_entity(username)
                
                # Join
                await client(JoinChannelRequest(entity))
                print(f"  - Joined.")
                
                # Unarchive
                peer = await client.get_input_entity(entity)
                await client(EditPeerFoldersRequest(folder_peers=[InputFolderPeer(peer=peer, folder_id=0)]))
                
                # Mute
                await client(UpdateNotifySettingsRequest(
                    peer=InputNotifyPeer(peer),
                    settings=InputPeerNotifySettings(mute_until=2147483647)
                ))
                
                # Add to Telegram Folder
                if target_folder:
                    from telethon.utils import get_peer_id
                    curr_ids = {get_peer_id(p) for p in target_folder.include_peers}
                    if get_peer_id(peer) not in curr_ids:
                        target_folder.include_peers.append(peer)
                        await client(UpdateDialogFilterRequest(id=target_folder.id, filter=target_folder))
                
                # Add to DB
                async with get_session(db_name=db_name) as session:
                    tid = str(entity.id)
                    res = await session.execute(select(TrackedChannel).where(TrackedChannel.telegram_id == tid))
                    if not res.scalar_one_or_none():
                        e_type = "channel" if isinstance(entity, Channel) and entity.broadcast else "group"
                        chan = TrackedChannel(
                            telegram_id=tid, folder_id=folder_id, title=entity.title,
                            username=entity.username, entity_type=e_type
                        )
                        session.add(chan); await session.commit()
                        print(f"  - Added to DB.")
                
                await asyncio.sleep(15) # Safety delay
                
            except FloodWaitError as e:
                print(f"FloodWait: Need to wait {e.seconds}s. Sleeping...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"Error @{username}: {e}")

if __name__ == "__main__":
    from telethon.tl.functions.messages import UpdateDialogFilterRequest
    asyncio.run(main())
