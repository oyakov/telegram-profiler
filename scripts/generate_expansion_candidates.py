import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel, Chat
from telethon.errors import FloodWaitError

# Add project root to sys.path
sys.path.append(os.getcwd())
from src.core.config import get_settings

async def search_candidates(client, keywords, limit=100):
    seen_ids = set()
    candidates = []
    
    for kw in keywords:
        print(f"Searching for '{kw}'...", file=sys.stderr)
        try:
            search_res = await client(SearchRequest(q=kw, limit=100))
            for chat in search_res.chats:
                if not isinstance(chat, (Channel, Chat)): continue
                if chat.id in seen_ids: continue
                
                # Use basic info from entity to avoid GetFullChannelRequest flood
                participants = getattr(chat, 'participants_count', 0)
                # Note: participants_count is often not present in basic entity
                # But search results for channels usually have it if they are public
                
                username = f"@{chat.username}" if getattr(chat, 'username', None) else "Private"
                
                candidates.append({
                    "title": chat.title,
                    "username": username,
                    "participants": participants or 0,
                    "id": chat.id
                })
                seen_ids.add(chat.id)
            
            if len(candidates) >= limit + 50: # Get a bit more to filter better
                break
        except FloodWaitError as e:
            print(f"Flood wait: {e.seconds}s", file=sys.stderr)
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            
    # Sort by participants
    candidates.sort(key=lambda x: x["participants"], reverse=True)
    return candidates[:limit]

async def main():
    settings = get_settings()
    client = TelegramClient(f"sessions/{settings.telegram_session_name}", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    categories = {
        "BG Intel": ["Белград", "Сербия", "Belgrade", "Serbia", "Понаехали", "ВНЖ Сербия"],
        "Crypto": ["Crypto", "Bitcoin", "Solana", "DEX", "Meme coins", "Crypto News", "Alpha", "DeFi"],
        "BG - Rent": ["Аренда Белград", "Stanovi Beograd", "Rent Belgrade", "Белград Снять", "Nekretnine Srbija"],
        "BG - Cars": ["Авто Сербия", "Белград Машины", "Autopijaca", "Serbia Cars", "Prodaja auta Srbija"],
        "BG - Work": ["Работа Белград", "Jobs Serbia", "Белград Вакансии", "IT Serbia", "Poslovi Beograd"],
        "BG - News": ["Новости Сербия", "Белград Новости", "Vesti Beograd", "Serbia News", "Blic", "N1"]
    }
    
    async with client:
        for cat_name, kws in categories.items():
            print(f"\n### {cat_name} Candidates", flush=True)
            candidates = await search_candidates(client, kws, limit=100)
            
            print(f"| # | Title | Username | Subscribers |", flush=True)
            print(f"|---|-------|----------|-------------|", flush=True)
            for i, c in enumerate(candidates, 1):
                print(f"| {i} | {c['title']} | {c['username']} | {c['participants']} |", flush=True)
            
            # Brief pause between categories to avoid flood
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
