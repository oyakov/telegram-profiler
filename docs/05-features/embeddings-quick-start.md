# Embeddings Quick Start Guide

## Prerequisites

```bash
# 1. Ensure LM Studio is running
# Default: http://localhost:1234/v1

# 2. Ensure PostgreSQL and Redis are running
docker-compose up -d postgres redis

# 3. Install dependencies
pip install -r requirements.txt
```

## Running Embedding Generation

### Option 1: Direct Generation (Fastest for testing)

```bash
POSTGRES_HOST=localhost LMSTUDIO_BASE_URL=http://localhost:1234/v1 python << 'EOF'
import asyncio
from src.pipeline.unified_processor import maintenance_index_messages

async def generate():
    result = await maintenance_index_messages(batch_size=500, db_name="crm")
    print(f"Generated {result['processed']} embeddings, {result['errors']} errors")

asyncio.run(generate())
EOF
```

### Option 2: Celery Worker (Production)

```bash
# Terminal 1: Start worker (processes embeddings)
REDIS_URL=redis://localhost:6379/0 POSTGRES_HOST=localhost \
  celery -A src.pipeline.celery_app worker --loglevel=info -Q processing -c 2

# Terminal 2: Start scheduler (periodic tasks)
POSTGRES_HOST=localhost \
  celery -A src.pipeline.celery_app beat --loglevel=info

# Terminal 3: Queue tasks
REDIS_URL=redis://localhost:6379/0 python << 'EOF'
from src.pipeline.tasks import orchestrate_multi_db_message_processing
orchestrate_multi_db_message_processing.delay()
EOF
```

## Monitoring Progress

```bash
# Quick check - count embeddings
POSTGRES_HOST=localhost python << 'EOF'
import asyncio
from src.db.database import get_session
from src.db.models import MessageEmbedding, Message
from sqlalchemy import func, select

async def check():
    async with get_session(db_name="crm") as s:
        msgs = await s.execute(select(func.count(Message.id)))
        embs = await s.execute(select(func.count(MessageEmbedding.message_id.distinct())))
        total = await s.execute(select(func.count(MessageEmbedding.id)))
        
        total_msgs = msgs.scalar() or 0
        total_embs = embs.scalar() or 0
        total_recs = total.scalar() or 0
        
        coverage = (total_embs / total_msgs * 100) if total_msgs > 0 else 0
        print(f"Messages: {total_msgs}")
        print(f"With embeddings: {total_embs} ({coverage:.1f}%)")
        print(f"Total records: {total_recs}")

asyncio.run(check())
EOF
```

## Testing Search with Embeddings

```bash
# Test semantic search endpoint
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning investments",
    "limit": 10
  }'
```

## Performance Tips

1. **Batch Size**: Start with 100-500, increase for better throughput
2. **Worker Concurrency**: Default 2, increase to 4-8 on multi-core systems
3. **LM Studio**: Ensure model is downloaded and ready
4. **Redis**: Required for Celery, use `redis://localhost:6379/0` locally

## Troubleshooting

### "Connection error" when generating embeddings
- Check LM Studio is running: `curl http://localhost:1234/v1/models`
- Fix LMSTUDIO_BASE_URL: should be `http://localhost:1234/v1` (not `host.docker.internal`)

### Redis connection failures
- Use `redis://localhost:6379/0` (not `redis://redis:6379/0`)
- Ensure Redis is running: `docker-compose up -d redis`

### No embeddings in database
- Check PostgreSQL is running: `docker-compose up -d postgres`
- Verify DB connection: `POSTGRES_HOST=localhost psql -U crm -d crm -c "SELECT COUNT(*) FROM message_embeddings;"`

### Slow generation
- LM Studio processes sequentially by default
- Reduce batch size to see progress faster
- Monitor with `tail -f` on logs while running

## Architecture

```
Message → LM Studio (1024-dim) → PostgreSQL (pgvector)
                                 ↓
                          Semantic Search (cosine_distance)
                          + Keyword Fallback
```

## API Reference

### Search Endpoint
```
POST /search
Content-Type: application/json

{
  "query": "string",      # Search text
  "limit": integer        # Max results (default 10)
}

Response:
{
  "query": "...",
  "contacts": [
    {
      "id": "uuid",
      "first_name": "...",
      "similarity": 0.87,
      "search_type": "semantic|keyword",
      "evidence": [
        {"text": "...", "relevance": 0.92}
      ]
    }
  ],
  "messages": [...]
}
```

## Next Steps

1. Generate embeddings for all messages (see Options 1-2 above)
2. Set up periodic generation with Celery beat
3. Configure alert thresholds for new messages
4. Optimize batch size based on your hardware
5. Add search UI to frontend
