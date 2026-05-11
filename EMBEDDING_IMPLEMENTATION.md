# Embeddings & Search Implementation Summary

## What Was Done

### 1. **Implemented Celery Tasks** (`src/pipeline/tasks.py`)
Replaced placeholder implementations with actual working code:

#### `process_message_embeddings()` 
- Finds all messages without embeddings
- Generates vector embeddings using configured provider (Google/LM Studio)
- Stores in `MessageEmbedding` table with pgvector
- Tracks tokens used and errors

#### `reindex_dirty_contacts()`
- Processes contacts marked as `embedding_dirty=True`
- Generates embeddings from contact profile + recent messages
- Updates contact vector in database
- Marks as clean after processing

#### `process_unified_messages()`
- Processes new messages through AI pipeline
- Extracts contacts and leads using LLM
- Deduplicates and syncs to database
- Triggers follow-up embedding and reindexing

#### `orchestrate_multi_db_message_processing()`
- Dispatches processing tasks across all databases
- Chains: process messages → generate embeddings → re-index contacts

### 2. **Vector Search Implementation** (Already Implemented in `src/api/routers/search.py`)
The semantic search endpoint was already implemented and includes:
- **Semantic search**: Uses `cosine_distance()` on embeddings
- **Keyword fallback**: Falls back to LIKE search if semantic finds few results
- **Evidence extraction**: Shows relevant message quotes for each contact
- **Hybrid scoring**: Combines semantic + keyword results

### 3. **Test Coverage**
Created comprehensive test scripts:
- `tests/test_embeddings_search.py` - Full pytest suite
- `test_embeddings_quick.py` - Quick integration test

## Database Schema

```sql
-- Message embeddings
CREATE TABLE message_embeddings (
    id UUID PRIMARY KEY,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    chunk_index INTEGER DEFAULT 0,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,  -- pgvector column
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contact embeddings
ALTER TABLE contacts ADD COLUMN embedding VECTOR(1024);
ALTER TABLE contacts ADD COLUMN embedding_dirty BOOLEAN DEFAULT TRUE;
```

## Configuration

### Environment Variables
```bash
# Embedding provider
EMBED_PROVIDER=google              # or 'lmstudio'
GOOGLE_EMBED_MODEL=text-embedding-004
EMBED_DIMENSIONS=1024
```

### Celery Queue Configuration
All embedding tasks run in the `processing` queue:
```python
@celery_app.task(name="...", queue="processing")
```

## Usage

### Trigger Embedding Generation
```python
# Single database
from src.pipeline.tasks import process_message_embeddings
result = process_message_embeddings.delay(batch_size=100, db_name="crm")

# All databases
from src.pipeline.tasks import orchestrate_multi_db_message_processing
orchestrate_multi_db_message_processing.delay()
```

### Search with Embeddings
```python
from src.api.schemas import SearchRequest
from src.api.routers.search import semantic_search

result = await semantic_search(
    SearchRequest(query="machine learning investments", limit=10),
    db=session
)

# Result structure:
{
    "query": "...",
    "contacts": [
        {
            "id": "...",
            "first_name": "...",
            "similarity": 0.87,           # Cosine similarity
            "search_type": "semantic",    # or "keyword"
            "evidence": [                 # Most relevant message chunks
                {"text": "...", "relevance": 0.92}
            ]
        }
    ],
    "messages": [
        {
            "message_id": "...",
            "content": "...",
            "contact_name": "...",
            "similarity": 0.85
        }
    ]
}
```

## Performance Notes

### Embedding Generation
- **Batch Size**: Default 100 messages per task
- **Rate Limiting**: Integrated token tracking via Redis
- **Cost**: ~1 token per 4 characters

### Search Performance
- **Index**: pgvector handles similarity search efficiently
- **Threshold**: 0.52 cosine distance (0.48 similarity)
- **Fallback**: Keyword search if < 5 semantic results

## Testing

### Run Quick Integration Test
```bash
POSTGRES_HOST=localhost python test_embeddings_quick.py
```

### Run Full Test Suite
```bash
pytest tests/test_embeddings_search.py -v -s
```

## Next Steps

1. **Schedule Automatic Embedding Generation**
   - Add to Celery beat schedule for regular updates
   - Process new messages every 5 minutes

2. **Improve Search UX**
   - Add filters by date, company, etc.
   - Implement faceted search
   - Add search analytics/logging

3. **Optimize Costs**
   - Use smaller embedding models for batch processing
   - Implement caching layer for common queries
   - Consider incremental embeddings

## Troubleshooting

### No embeddings generated
Check:
1. Redis connection (for token tracking)
2. Embedding provider API key
3. Message table has content

### Search returns no results
1. Run `maintenance_index_messages()` to generate embeddings
2. Check similarity threshold (currently 0.52)
3. Verify embedding dimensions match model output
