# Plan: Refactor: Modular Models & Async Infrastructure

## Phase 1: Models Modularization
- [x] Create `src/db/models/base.py` with `Base` class.
- [x] Extract `identity`, `tracking`, `content`, `sync`, `marketing`, and `system` models.
- [x] Create `__init__.py` for seamless imports.

## Phase 2: Async Infrastructure
- [x] Implement `src/pipeline/base_task.py` with `AsyncDBTask`.
- [x] Update `celery_app.py` or tasks to utilize the new base class.
