"""Script to re-generate embeddings for all messages using local LM Studio."""

import asyncio
import os
import sys
from sqlalchemy import select, func

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Message, MessageEmbedding
from src.ai.embeddings import generate_embeddings_batch

async def reindex_messages(batch_size: int = 100):
    # Ensure POSTGRES_HOST is set to localhost if running from host
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    print("Starting message re-indexing with LM Studio...")
    
    total_indexed = 0
    
    async with get_session() as session:
        # Get count of messages that don't have embeddings yet
        processed_ids = select(MessageEmbedding.message_id)
        count_query = select(func.count(Message.id)).where(Message.id.not_in(processed_ids))
        res = await session.execute(count_query)
        total_to_process = res.scalar() or 0
        print(f"Total messages to index: {total_to_process}")

    while True:
        async with get_session() as session:
            # Fetch batch of messages without embeddings
            processed_ids = select(MessageEmbedding.message_id)
            query = (
                select(Message)
                .where(Message.id.not_in(processed_ids))
                .where(Message.content.is_not(None))
                .limit(batch_size)
            )
            result = await session.execute(query)
            messages = result.scalars().all()
            
            if not messages:
                break
            
            texts = [m.content for m in messages]
            try:
                vectors = await generate_embeddings_batch(texts)
                
                for msg, vector in zip(messages, vectors):
                    embedding = MessageEmbedding(
                        message_id=msg.id,
                        chunk_text=msg.content,
                        embedding=vector
                    )
                    session.add(embedding)
                
                await session.commit()
                total_indexed += len(messages)
                print(f"Indexed {total_indexed}/{total_to_process} messages...")
            except Exception as e:
                print(f"Error generating embeddings: {e}")
                await asyncio.sleep(5)
                continue

    print(f"Re-indexing complete. Total messages indexed: {total_indexed}")

if __name__ == "__main__":
    asyncio.run(reindex_messages())
