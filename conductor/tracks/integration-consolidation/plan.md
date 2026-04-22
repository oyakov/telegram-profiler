# Implementation Plan: Integration & Consolidation

## Phase 1: Shared Infrastructure & Schemas [checkpoint: ]
Establish the foundation for a unified codebase.

- [x] Task 1.1: Create `src/api/schemas/` directory and extract common Pydantic models.
- [x] Task 1.2: Refactor `src/api/main.py` and `dashboard/app.py` to use shared schemas.
- [x] Task 1.3: Consolidate `requirements.txt` and `requirements-dashboard.txt` into a single `requirements.txt`.
- [x] Task 1.4: Unify `Dockerfile` and `Dockerfile.dashboard` into a multi-stage `Dockerfile`.
- [x] Task 1.5: Clean up redundant scripts (`scripts/tg_login.py`, `scripts/tg_login_local.py`).

## Phase 2: AI & Pipeline Unification [checkpoint: ]
Unify message processing and AI extraction services.

- [x] Task 2.1: Refactor `src/ai/extraction.py` and `src/ai/ad_buyer_detector.py` into a modular `ExtractionService` in `src/ai/services.py`.
- [x] Task 2.2: Implement `src/pipeline/unified_processor.py` (merging `processor.py` and `ad_processor.py`).
- [x] Task 2.3: Ensure `src/ai/deduplication.py` is the single point of entry for all contact merges.
- [x] Task 2.4: Update Celery tasks in `src/pipeline/tasks.py` to use the `unified_processor.py`.
- [x] Task 2.5: Remove deprecated `src/pipeline/processor.py` and `src/pipeline/ad_processor.py`.

## Phase 3: API Modularization [checkpoint: ]
Refactor the API into a modular router-based structure.

- [x] Task 3.1: Create `src/api/routers/` and implement `contacts.py`, `messages.py`, `telegram.py`, and `leads.py`.
- [x] Task 3.2: Refactor `src/api/main.py` to mount the routers.
- [x] Task 3.3: Verify all API endpoints remain functional via automated tests.

## Phase 4: Frontend Alignment & Cleanup
Align the Dashboard with the refactored API and perform final cleanup.

- [x] Task 4.1: Update `dashboard/app.py` to use the modular API endpoints and shared schemas.
- [x] Task 4.2: Ensure consistent error handling between the API and Dashboard.
- [x] Task 4.3: Perform final code style checks and remove any remaining unused files. (Deleted redundant scripts).
