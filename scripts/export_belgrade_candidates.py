import asyncio
import os
import sys
import csv
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel, Chat
from sqlalchemy import select

sys.path.append(os.getcwd())
from src.db.database import get_session
from src.db.models import TrackedChannel
from src.core.config import get_settings

async def main():
    settings = get_settings()
    client = TelegramClient("sessions/bg_discovery.session", int(settings.telegram_api_id), settings.telegram_api_hash)
    
    # Расширенные категории поиска
    search_queries = {
        "Общие": ["Белград", "Сербия", "Beograd", "Belgrade", "Srbija", "Понаехали"],
        "Города": ["Нови Сад", "Novi Sad", "Zemun", "Земун"],
        "Услуги/ВНЖ": ["ВНЖ Сербия", "Боравак", "Релокация Сербия", "Юрист Сербия"],
        "Коммерция": ["Аренда Белград", "Работа Сербия", "Объявления Белград", "Барахолка Белград", "Oglasi"],
        "Досуг": ["Афиша Белград", "Рестораны Белград", "События Белград"]
    }
    
    async with client:
        # 1. Получаем список уже отслеживаемых
        async with get_session(db_name="crm") as session:
            res = await session.execute(select(TrackedChannel.telegram_id))
            existing_ids = {row[0] for row in res.all()}

        print(f"Исключаем {len(existing_ids)} уже отслеживаемых каналов...")
        
        candidates = []
        seen_ids = set()

        for category, keywords in search_queries.items():
            for kw in keywords:
                print(f"Поиск [{category}]: '{kw}'...")
                try:
                    res = await client(SearchRequest(q=kw, limit=100))
                    for chat in res.chats:
                        if not isinstance(chat, (Channel, Chat)): continue
                        
                        tid = str(chat.id)
                        if tid in existing_ids or tid in seen_ids: continue
                        
                        try:
                            full = await client(GetFullChannelRequest(chat))
                            p_count = full.full_chat.participants_count
                            about = full.full_chat.about or "Нет описания"
                            
                            if p_count > 300:
                                link = f"https://t.me/{chat.username}" if getattr(chat, 'username', None) else "Приватная ссылка"
                                candidates.append({
                                    "Название": chat.title,
                                    "Ссылка": link,
                                    "Описание": about.replace('\n', ' ').strip(),
                                    "Подписчики": p_count,
                                    "Почему в списке": f"Найден по запросу '{kw}' в категории '{category}'"
                                })
                                seen_ids.add(tid)
                                print(f"  + {chat.title} ({p_count} чел.)")
                        except Exception:
                            continue
                    await asyncio.sleep(1) # Защита от Flood
                except Exception as e:
                    print(f"Ошибка поиска '{kw}': {e}")

        # Сортировка по популярности
        candidates.sort(key=lambda x: x["Подписчики"], reverse=True)

        # Сохранение в CSV
        filename = "belgrade_candidates_300plus.csv"
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Название", "Ссылка", "Описание", "Подписчики", "Почему в списке"])
            writer.writeheader()
            writer.writerows(candidates)

        print(f"\nГотово! Найдено {len(candidates)} уникальных кандидатов.")
        print(f"Файл сохранен: {os.path.abspath(filename)}")

if __name__ == "__main__":
    asyncio.run(main())
