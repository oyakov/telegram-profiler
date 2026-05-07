# Specification: Architecture V2

## Motivation
The codebase has grown and certain modules (like `TelegramConnector` and `llm_client.py`) have become overloaded and tightly coupled. We need to introduce provider patterns and decouple services to improve testability, maintainability, and future extensibility.

## Core Objectives
1. **LLM Provider Pattern:** Refactor `llm_client.py` to use a formal provider pattern (Base, Gemini, LMStudio).
2. **Connector Decoupling:** Split `TelegramConnector` into specialized services (Auth, Sync, Management).
3. **Pipeline Orchestration:** Refactor `UnifiedProcessor` to use a plugin/registry model for analysis tasks.

## Constraints
- Maintain backward compatibility with existing databases and celery tasks.
- Keep external API endpoints unchanged.