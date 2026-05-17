# Implementation Plan: Embedding Provider Pattern

## Goal
Formalize the embedding provider pattern to match the LLM provider structure, eliminating hardcoded provider logic in `src/ai/analysis.py`.

## Phase 1: Provider Infrastructure
- [ ] Create `src/ai/providers/embeddings/` directory.
- [ ] Define `BaseEmbeddingProvider` interface.
- [ ] Implement `OpenAICompatibleEmbeddingProvider`.

## Phase 2: Integration
- [ ] Update `src/ai/providers/factory.py` to include embedding providers.
- [ ] Refactor `src/ai/analysis.py` to use the provider factory.
- [ ] Update `src/core/config.py` if necessary to support unified provider config.

## Phase 3: Validation
- [ ] Verify embeddings work with both Google and LMStudio.
- [ ] Run `test_embeddings.py`.