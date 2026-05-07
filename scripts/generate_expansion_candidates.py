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

async def search_candidates(client, cat_name, keywords, limit=100):
    seen_ids = set()
    candidates = []
    
    for kw in keywords:
        if len(candidates) >= limit:
            break
            
        print(f"[{cat_name}] Searching for '{kw}'...", file=sys.stderr)
        try:
            search_res = await client(SearchRequest(q=kw, limit=100))
            for chat in search_res.chats:
                if not isinstance(chat, (Channel, Chat)): continue
                if chat.id in seen_ids: continue
                
                participants = getattr(chat, 'participants_count', 0)
                username = f"@{chat.username}" if getattr(chat, 'username', None) else "Private"
                
                # Logic for "Reason"
                reason = f"Matched keyword '{kw}'"
                if participants > 50000:
                    reason += " | High authority (50k+ subs)"
                elif participants > 10000:
                    reason += " | Established community (10k+ subs)"
                
                candidates.append({
                    "title": chat.title.replace("|", "-"), # Avoid breaking MD table
                    "username": username,
                    "participants": participants or 0,
                    "id": chat.id,
                    "reason": reason
                })
                seen_ids.add(chat.id)
                
                if len(candidates) >= limit:
                    break
        except FloodWaitError as e:
            print(f"Flood wait: {e.seconds}s", file=sys.stderr)
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            
    candidates.sort(key=lambda x: x["participants"], reverse=True)
    return candidates[:limit]

async def main():
    settings = get_settings()
    client = TelegramClient(f"sessions/{settings.telegram_session_name}", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    categories = {
        "BG Intel": ["Белград", "Сербия", "Belgrade", "Serbia", "ВНЖ Сербия", "Релокация Сербия", "Балканы", "Гайд Белград", "Чат Белграда", "Сербия Чат", "Белград Чат"],
        "Crypto": ["Crypto", "Bitcoin", "Solana", "DEX", "Meme coins", "Crypto News", "Alpha", "DeFi", "Ethereum", "Trading Signals", "Binance News", "Crypto Gems", "NFT Alpha"],
        "BG - Rent": ["Аренда Белград", "Stanovi Beograd", "Rent Belgrade", "Белград Снять", "Nekretnine Srbija", "Izdavanje Beograd", "Apartments Belgrade", "Flat share Belgrade", "Smeštaj Beograd"],
        "BG - Cars": ["Авто Сербия", "Белград Машины", "Autopijaca", "Serbia Cars", "Prodaja auta Srbija", "Polovni automobili", "Auto oglasi Srbija", "Delovi Srbija", "Kupujem Prodajem Auto"],
        "BG - Work": ["Работа Белград", "Jobs Serbia", "Белград Вакансии", "IT Serbia", "Poslovi Beograd", "Работа в Сербии", "Belgrade Jobs", "IT Jobs Belgrade", "Serbia Freelance"],
        "BG - News": ["Новости Сербия", "Белград Новости", "Vesti Beograd", "Serbia News", "Blic", "N1", "Danas", "Telegraf.rs", "Kurir", "Balkan News", "Srbija Danas"]
    }
    
    output_file = "expansion_candidates.md"
    
    async with client:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Telegram Expansion Candidates\n\n")
            f.write("Generated for manual review to expand folders to 100 channels each.\n\n")
            
            for cat_name, kws in categories.items():
                print(f"Processing category: {cat_name}...", file=sys.stderr)
                candidates = await search_candidates(client, cat_name, kws, limit=100)
                
                f.write(f"## {cat_name}\n\n")
                f.write(f"| # | Title | Username | Subscribers | Why Selected |\n")
                f.write(f"|---|-------|----------|-------------|--------------|\n")
                
                for i, c in enumerate(candidates, 1):
                    f.write(f"| {i} | {c['title']} | {c['username']} | {c['participants']} | {c['reason']} |\n")
                
                f.write("\n")
                await asyncio.sleep(3) # Anti-flood
                
    print(f"Successfully generated {output_file}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
