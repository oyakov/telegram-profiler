# Implementation Plan: Telegram Connector Decoupling

## Goal
Decouple `src/connectors/telegram_connector.py` into specialized services to improve maintainability and testability.

## Phase 1: Preparation
- [ ] Create `src/services/telegram/` directory.
- [ ] Define interfaces for Auth, Sync, and Management.

## Phase 2: Extraction
- [ ] Extract Authentication logic to `TelegramAuthService`.
- [ ] Extract Contact/Entity resolution to `TelegramEntityService`.
- [ ] Extract Sync/Polling logic to `TelegramSyncService`.

## Phase 3: Integration
- [ ] Update `PipelineService` and Celery tasks to use new services.
- [ ] Refactor `TelegramConnector` to be a thin wrapper or deprecated proxy.
- [ ] Verify existing tests pass.