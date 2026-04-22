import asyncio
import os
import sys
import structlog
from sqlalchemy import select, func, and_

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Message, MessageEmbedding, Contact
from src.ai.embeddings import generate_embedding

logger = structlog.get_logger()

async def index_messages(batch_size: int = 100):
    print("🚀 Starting Massive Message Embedding Indexing...")
    
    while True:
        async with get_session() as session:
            # Find messages that don't have embeddings yet
            # We use a subquery to find message IDs not in MessageEmbedding
            processed_ids = select(MessageEmbedding.message_id)
            query = (
                select(Message)
                .where(Message.id.not_in(processed_ids))
                .where(Message.content.isnot(None))
                .where(func.length(Message.content) > 10)
                .limit(batch_size)
            )
            
            result = await session.execute(query)
            messages = result.scalars().all()
            
            if not messages:
                print("✅ All messages indexed.")
                break
                
            print(f"Processing batch of {len(messages)} messages...")
            
            for msg in messages:
                try:
                    # Clean content
                    text = msg.content.strip()
                    if not text: continue
                    
                    # Generate embedding
                    vector = await generate_embedding(text)
                    
                    # Save
                    emb = MessageEmbedding(
                        message_id=msg.id,
                        embedding=vector,
                        chunk_text=text[:1000] # Store preview
                    )
                    session.add(emb)
                except Exception as e:
                    logger.error("embedding_error", message_id=str(msg.id), error=str(e))
            
            await session.commit()
            print(f"Batch committed. Continuing...")

async def index_contacts(batch_size: int = 50):
    print("\n🚀 Starting Contact Embedding Indexing (Dirty ones)...")
    from src.pipeline.unified_processor import maintenance_reindex_dirty
    
    while True:
        result = await maintenance_reindex_dirty(batch_size=batch_size)
        if result["processed"] == 0:
            print("✅ All contacts indexed.")
            break
        print(f"Processed {result['processed']} contacts. Errors: {result['errors']}")

async def main():
    # Run both
    await index_messages(batch_size=100)
    await index_contacts(batch_size=50)

if __name__ == "__main__":
    asyncio.run(main())
