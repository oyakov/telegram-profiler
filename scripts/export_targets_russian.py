"""Экспорт расширенных данных по рекламным целям (Sales Targets) на русском языке."""

import asyncio
import os
import sys
import csv
import json
from datetime import datetime
from sqlalchemy import select, func

# Добавляем текущую директорию в путь
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Contact, Message

async def export_full_targets():
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    print("Генерация расширенного отчета по целям (рекламодатели, которых нет в нашем канале)...")
    
    async with get_session() as session:
        # Ищем всех рекламодателей с 0% активностью в нашем канале
        query = (
            select(Contact)
            .where(Contact.is_lead == True)
            .where(Contact.our_channel_ratio == 0)
            .order_by(Contact.lead_score.desc())
            .limit(1000)
        )
        
        result = await session.execute(query)
        contacts = result.scalars().all()
        
    if not contacts:
        print("Цели не найдены. Проверьте статус сканирования.")
        return

    filename = f"reklamodately_targets_full_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # Заголовки на русском
        writer.writerow([
            "Имя / Название", 
            "Telegram Username", 
            "Очки активности", 
            "Описание (Bio)", 
            "Что рекламируют (Контекст)", 
            "Где размещаются (Каналы)",
            "Кол-во рекламы в базе",
            "Пример последнего поста"
        ])
        
        for c in contacts:
            full_name = f"{c.first_name or ''} {c.last_name or ''}".strip()
            ctx = c.ad_context or {}
            history = ctx.get("ad_history", [])
            
            # Анализируем контекст
            summaries = list(set([h.get("summary", "") for h in history if h.get("summary")]))
            ad_context = " | ".join(summaries[:5]) # Берем первые 5 уникальных тематик
            
            # Собираем список каналов (в эвристике мы храним group_id, но для отчета лучше имена)
            # В данном контексте мы просто выведем количество каналов
            channels_count = len(set([h.get("group_id") for h in history if h.get("group_id")]))
            
            # Берем текст последнего объявления для примера
            last_evidence = history[-1].get("evidence", "Нет данных") if history else "Н/Д"
            
            writer.writerow([
                full_name,
                f"@{c.telegram_username}" if c.telegram_username else "N/A",
                c.lead_score,
                c.bio or "Не заполнено",
                ad_context,
                f"Активен в {channels_count} каналах",
                len(history),
                last_evidence
            ])

    print(f"Готово! Экспортировано {len(contacts)} контактов в файл: {filename}")

if __name__ == "__main__":
    asyncio.run(export_full_targets())
