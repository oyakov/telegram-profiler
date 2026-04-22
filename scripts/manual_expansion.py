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
    client = TelegramClient("sessions/bg_discovery.session", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    keywords = [
        "Белград", "Сербия", "Beograd", "Belgrade", "Srbija", 
        "Понаехали", "ВНЖ Сербия", "Аренда Белград", "Новости Сербии", 
        "Serbia Live", "Relocation Serbia", "Belgrade Expats", "Афиша Белград",
        "Белград объявления", "Oglasi Beograd", "Posao Srbija"
    ]
    
    async with client:
        # 1. Получаем текущий список
        async with get_session(db_name="crm") as session:
            res = await session.execute(select(TrackedFolder).where(TrackedFolder.name == "BG Intel"))
            folder = res.scalar_one_or_none()
            if not folder:
                print("Папка BG Intel не найдена.")
                return
            
            res = await session.execute(select(TrackedChannel.telegram_id).where(TrackedChannel.folder_id == folder.id))
            existing_ids = {row[0] for row in res.all()}
        
        current_count = len(existing_ids)
        target = 100 - current_count
        print(f"Сейчас в базе: {current_count}. Нужно добавить: {target}")
        
        if target <= 0:
            print("Лимит в 100 каналов достигнут.")
            return

        # 2. Ищем кандидатов
        candidates = []
        seen_ids = set()
        
        for kw in keywords:
            print(f"Поиск по запросу: '{kw}'...")
            try:
                search_res = await client(SearchRequest(q=kw, limit=100))
                for chat in search_res.chats:
                    if not isinstance(chat, (Channel, Chat)): continue
                    tid = str(chat.id)
                    if tid in existing_ids or tid in seen_ids: continue
                    
                    try:
                        full = await client(GetFullChannelRequest(chat))
                        p_count = full.full_chat.participants_count
                        # Берем только те, где больше 500 участников для качества
                        if p_count > 500:
                            candidates.append({"entity": chat, "id": tid, "title": chat.title, "p": p_count})
                            seen_ids.add(tid)
                            print(f"  - Подходит: {chat.title} ({p_count} чел.)")
                    except: continue
            except Exception as e:
                print(f"Ошибка поиска: {e}")
        
        # 3. Сортируем по размеру
        candidates.sort(key=lambda x: x["p"], reverse=True)
        top_candidates = candidates[:target]
        
        if not top_candidates:
            print("Новых кандидатов не найдено.")
            return

        print(f"\n--- ВЫБРАНО {len(top_candidates)} ЛУЧШИХ КАНАЛОВ ---")
        for i, c in enumerate(top_candidates, 1):
            print(f"{i}. {c['title']} ({c['p']} чел.)")

        # 4. Вступаем
        joined = 0
        for c in top_candidates:
            try:
                print(f"Вступаю в: {c['title']}...")
                await client(JoinChannelRequest(c['entity']))
                joined += 1
                await asyncio.sleep(10) # Пауза между вступлениями
            except FloodWaitError as e:
                print(f"Flood Wait! Нужно подождать {e.seconds} сек. Завершаю на сегодня.")
                break
            except Exception as e:
                print(f"Не удалось вступить в {c['title']}: {e}")

        print(f"\nИтог: Вступили в {joined} новых каналов.")

if __name__ == "__main__":
    asyncio.run(main())
