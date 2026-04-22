import asyncio
import os
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import MessageEmbedding, Contact, Message
from src.ai.embeddings import generate_embedding

async def semantic_search(query: str, limit: int = 5):
    print(f"\n🔎 СЕМАНТИЧЕСКИЙ ПОИСК: '{query}'")
    print("-" * 50)
    
    query_vector = await generate_embedding(query)
    
    async with get_session() as session:
        # Search messages by cosine similarity
        # 1 - distance = similarity
        query_stmt = (
            select(MessageEmbedding, Message)
            .join(Message, Message.id == MessageEmbedding.message_id)
            .order_by(MessageEmbedding.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        
        res = await session.execute(query_stmt)
        for emb, msg in res.all():
            similarity = 1 - (emb.embedding @ query_vector) # Quick check, pgvector is more accurate
            print(f"[{similarity:.1%}] ({msg.group_name}) {msg.content[:150]}...")

async def find_experts(persona_query: str, limit: int = 3):
    print(f"\n👤 ПОИСК ЭКСПЕРТОВ (Persona Match): '{persona_query}'")
    print("-" * 50)
    
    query_vector = await generate_embedding(persona_query)
    
    async with get_session() as session:
        query_stmt = (
            select(Contact)
            .where(Contact.embedding.isnot(None))
            .order_by(Contact.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        
        res = await session.execute(query_stmt)
        for contact in res.scalars().all():
            print(f"- {contact.first_name} {contact.last_name or ''} (@{contact.telegram_username or 'Н/Д'})")
            print(f"  Био/Интересы: {contact.bio or 'Нет био'} | {', '.join(contact.interests[:5])}")

async def main():
    # ТЕСТ 1: Поиск конкретной услуги (смысловой)
    await semantic_search("ремонт ноутбуков и техники apple")
    
    # ТЕСТ 2: Поиск специфического запроса на переезд
    await semantic_search("помощь с перевозкой вещей из рф в сербию")

    # ТЕСТ 3: Поиск людей по профессиональному профилю
    await find_experts("разработчик на python или аналитик данных")

if __name__ == "__main__":
    asyncio.run(main())
