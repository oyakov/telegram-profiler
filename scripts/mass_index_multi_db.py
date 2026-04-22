import asyncio
import os
import sys
import structlog
from typing import List

sys.path.append(os.getcwd())

from src.ai.embeddings import generate_embeddings_batch
from src.db.database import get_session, get_engine
from src.db.models import Message, MessageEmbedding
import sqlalchemy as sa
from sqlalchemy import select, func, exists

logger = structlog.get_logger()

# Force UTF-8 on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def get_tracked_databases() -> List[str]:
    engine = get_engine("postgres", use_pooling=False)
    async with engine.connect() as conn:
        res = await conn.execute(sa.text("SELECT datname FROM pg_database WHERE datname LIKE 'crm_%'"))
        return [row[0] for row in res.fetchall()]

async def process_db_embeddings(db_name: str, batch_size: int = 10):
    """Process a single batch for a database with optimized query."""
    
    # Override LM Studio base URL for host execution
    os.environ["LMSTUDIO_BASE_URL"] = "http://localhost:1234/v1"

    try:
        async with get_session(db_name=db_name) as session:
            # OPTIMIZED QUERY: Find messages without recordings in MessageEmbedding
            # Use ~exists for better performance on large tables
            query = (
                select(Message)
                .where(~exists().where(MessageEmbedding.message_id == Message.id))
                .where(Message.content.isnot(None))
                .where(func.length(Message.content) > 10)
                .limit(batch_size)
            )
            
            result = await session.execute(query)
            messages = result.scalars().all()
            
            if not messages:
                return 0

            texts = [m.content.strip()[:2000] for m in messages]
            try:
                vectors = await generate_embeddings_batch(texts)
                
                for i, vector in enumerate(vectors):
                    msg = messages[i]
                    emb = MessageEmbedding(
                        message_id=msg.id,
                        embedding=vector,
                        chunk_text=texts[i][:500],
                        chunk_index=0
                    )
                    session.add(emb)
                
                await session.commit()
                return len(vectors)
            except Exception as e:
                print(f"  [!] {db_name}: Embedding error: {str(e)[:100]}")
                return 0
    except Exception as e:
        print(f"  [!] {db_name}: Session error: {str(e)[:100]}")
        return 0

async def main():
    BATCH_SIZE = 10
    print("--- Mass Indexing: Slow & Steady (Optimized) ---")
    
    dbs = await get_tracked_databases()
    print(f"Detected databases: {', '.join(dbs)}")
    
    overall_total = 0
    
    while True:
        work_done_this_loop = False
        for db in dbs:
            # Process one batch per DB per loop to keep it "steady" across all folders
            count = await process_db_embeddings(db, batch_size=BATCH_SIZE)
            if count > 0:
                overall_total += count
                work_done_this_loop = True
                print(f"  [OK] {db:15} | Batch: {count:2} | Total this run: {overall_total}")
                # Short sleep between batches to avoid overloading LM Studio
                await asyncio.sleep(1)
        
        if not work_done_this_loop:
            print("[INFO] No more messages found. Waiting 60s...")
            await asyncio.sleep(60)
        else:
            await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Stopped by user.")
