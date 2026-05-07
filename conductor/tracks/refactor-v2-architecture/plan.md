# Implementation Plan: Architecture V2

## Phase 1: LLM Decoupling & Providers
- [ ] Create `src/ai/providers/base.py`
- [ ] Create `src/ai/providers/gemini.py`
- [ ] Create `src/ai/providers/lmstudio.py`
- [ ] Refactor `src/ai/llm_client.py` to use providers.
- [ ] Update `src/ai/services.py` to leverage native structured outputs if possible.

## Phase 2: Telegram Connector Split
- [ ] Create `TelegramAuthService`
- [ ] Create `TelegramSyncService`
- [ ] Create `TelegramManagementService`
- [ ] Deprecate monolithic `TelegramConnector`.

## Phase 3: Pipeline Refactoring
- [ ] Introduce Analysis Registry in `UnifiedProcessor`.
- [ ] Migrate contact/lead extraction to registered tasks.