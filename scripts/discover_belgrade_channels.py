import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
from telethon.tl.types import Channel, Chat
from telethon.errors import FloodWaitError
from sqlalchemy import select

sys.path.append(os.getcwd())
from src.db.database import get_session
from src.db.models import TrackedChannel, TrackedFolder
from src.core.config import get_settings

async def main():
    settings = get_settings()
    # Use dedicated discovery session to avoid locks
    client = TelegramClient("sessions/bg_discovery.session", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    keywords = ["Белград", "Сербия", "Belgrade", "Serbia", "Понаехали", "ВНЖ Сербия", "Работа Сербия", "Аренда Белград", "Белград объявления"]
    
    async with client:
        # 1. Get current count
        async with get_session(db_name="crm") as session:
            res = await session.execute(select(TrackedFolder).where(TrackedFolder.name == "BG Intel"))
            folder = res.scalar_one_or_none()
            if not folder:
                print("Folder BG Intel not found.")
                return
            
            res = await session.execute(select(TrackedChannel.telegram_id).where(TrackedChannel.folder_id == folder.id))
            existing_ids = {row[0] for row in res.all()}
        
        current_count = len(existing_ids)
        target_to_add = 100 - current_count
        print(f"Current channels in BG Intel: {current_count}. Target: 100.")
        
        if target_to_add <= 0:
            print("Limit reached.")
            return

        # 2. Search for candidates
        candidates = []
        seen_search_ids = set()
        for kw in keywords:
            print(f"Searching for '{kw}'...")
            try:
                search_res = await client(SearchRequest(q=kw, limit=50))
                for chat in search_res.chats:
                    if not isinstance(chat, (Channel, Chat)): continue
                    tg_id = str(chat.id)
                    if tg_id in existing_ids or tg_id in seen_search_ids: continue
                    
                    try:
                        full = await client(GetFullChannelRequest(chat))
                        count = full.full_chat.participants_count
                        candidates.append({"entity": chat, "id": tg_id, "title": chat.title, "participants": count})
                        seen_search_ids.add(tg_id)
                    except Exception: continue
            except Exception as e: print(f"Search error: {e}")
        
        candidates.sort(key=lambda x: x["participants"], reverse=True)
        to_join = candidates[:target_to_add]
        
        if not to_join:
            print("No new candidates found.")
            return

        # 4. Sequential Join with logic for FloodWait
        joined_count = 0
        for c in to_join:
            try:
                print(f"Joining {c['title']} ({c['participants']} members)...")
                await client(JoinChannelRequest(c['entity']))
                joined_count += 1
                await asyncio.sleep(5)
            except FloodWaitError as e:
                print(f"Flood wait: need to wait {e.seconds} seconds. Stopping for now.")
                break
            except Exception as e:
                print(f"Error joining {c['title']}: {e}")

        print(f"\nJoined {joined_count} new channels.")
        
if __name__ == "__main__":
    asyncio.run(main())
