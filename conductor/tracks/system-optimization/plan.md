# Implementation Plan: System Optimization & Scaling

## Objective
Implement recommendations from the deep code review to improve data processing speed, ensure reliable database migrations across multiple databases, and optimize Telegram data ingestion.

## Key Files & Context
- `scripts/migrate_all.py` (New file)
- `src/pipeline/unified_processor.py` (LLM processing)
- `src/connectors/telegram_connector.py` (Telegram sync)
- `conductor/tech-stack.md` (Documentation)
- `src/pipeline/tasks.py` (Celery tasks for cleanup)
- `tests/test_integration.py` (New integration test)

## Proposed Solution & Trade-offs
Based on consultation:
1.  **DB Migrations**: We will use a wrapper script (`scripts/migrate_all.py`) that loops over all `crm_*` databases and applies migrations. This avoids modifying the core `alembic/env.py` and provides better isolation and error handling per database.
2.  **LLM Batching**: We will process messages concurrently using `asyncio.gather` with a semaphore (e.g., 5 concurrent requests) in `MessageProcessor.process_batch`. This maximizes speed and accuracy while staying within reasonable API rate limits.

## Implementation Steps

### Phase 1: Multi-Database Migrations
1.  Create `scripts/migrate_all.py`.
2.  Implement logic to query `pg_database` for all databases starting with `crm`.
3.  For each database, override the `POSTGRES_DB` environment variable and run the Alembic programmatic API (`alembic.command.upgrade(config, "head")`) or via subprocess.

### Phase 2: Parallel LLM Processing
1.  Modify `src/pipeline/unified_processor.py` (`MessageProcessor.process_batch`).
2.  Introduce `asyncio.Semaphore(5)` to limit concurrency.
3.  Wrap the individual message extraction logic in an async function `_process_single_message`.
4.  Use `asyncio.gather` to execute these functions in parallel for the input batch.
5.  Aggregate the statistics correctly.

### Phase 3: Parallel Telegram Sync
1.  Modify `src/connectors/telegram_connector.py` (`sync` method).
2.  Introduce `asyncio.Semaphore(3)` to prevent flood waits from Telegram API.
3.  Use `asyncio.gather` with `return_exceptions=True` to fetch multiple channels concurrently.

### Phase 4: Maintenance & Documentation
1.  Create a Celery task in `src/pipeline/tasks.py` to delete `ExtractionLog` entries older than 30 days.
2.  Update `conductor/tech-stack.md` to reflect React + Vite instead of Streamlit.

### Phase 5: Integration Testing
1.  Create `tests/test_integration.py` focusing on parallel message processing and multi-DB wrapper execution.

## Verification & Testing
- Run `python scripts/migrate_all.py` and verify it targets multiple databases.
- Run tests: `pytest tests/test_integration.py`.
- Check logs for concurrent extraction execution and parallel Telegram sync completion.