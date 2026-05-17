# Implementation Plan: Sync Orchestrator Consolidation

## Goal
Eliminate redundant logic in `SyncOrchestrator` by delegating to specialized Telegram services and centralizing sync state tracking.

## Phase 1: Service Integration
- [ ] Refactor `_sync_folders` to use `TelegramManagementService`.
- [ ] Update `SyncOrchestrator` to use `TelegramSyncService` for metadata and batch queueing triggers.

## Phase 2: State Centralization
- [ ] Create `SyncStateRepository` in `src/db/repository.py`.
- [ ] Move state update logic (ETA, status, last_sync_at) from orchestrator and services into the repository.

## Phase 3: Cleanup & Validation
- [ ] Remove deprecated `TelegramConnector` method calls from orchestrator.
- [ ] Verify automated sync cycle with integrated services.