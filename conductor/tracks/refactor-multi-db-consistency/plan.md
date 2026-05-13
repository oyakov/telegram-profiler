# Plan: Refactor: Multi-DB Consistency & Repository Pattern

## Phase 1: Repository Implementation
- [x] Create `src/db/repository.py` with `MessageRepository`.
- [x] Extract common message saving logic.

## Phase 2: Multi-DB Enforcement
- [x] Audit and update `src/pipeline/telegram_sync_tasks.py`.
- [x] Audit and update `src/connectors/telegram_connector.py`.
- [x] Audit and update `src/pipeline/tasks.py`.

## Phase 3: Engine Optimization
- [x] Implement `dispose_engines` in `src/db/database.py`.
