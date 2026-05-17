# Implementation Plan: Final Service Layer Alignment

## Goal
Ensure all high-level services use the decoupled provider and configuration patterns.

## Phase 1: PipelineService Refactoring
- [ ] Refactor `PipelineService` to use `TelegramSyncService` and `TelegramAuthService`.
- [ ] Move "complete history" iteration logic into `TelegramSyncService`.

## Phase 2: ExtractionService Modernization
- [ ] Update `ExtractionService` to use `ConfigurationProvider`.
- [ ] Refactor extraction loops to use `get_llm_provider()` directly.
- [ ] Clean up redundant mapping logic in `extract()`.

## Phase 3: Validation
- [ ] Verify AI extractions still work with environment and DB settings.
- [ ] Ensure multi-tenant DB sync still functions correctly.