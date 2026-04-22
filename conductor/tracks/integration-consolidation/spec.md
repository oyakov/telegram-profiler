# Track Specification: Integration & Consolidation

## Objective
Unify fragmented components into a cohesive, modular product. This track addresses the redundancy between the general message processing pipeline and the specialized ad-buyer pipeline, unifies AI extraction logic, modularizes the API, and consolidates the infrastructure.

## Key Goals
1. **Pipeline Unification:** Merge `ad_processor.py` and `processor.py` into a single `MessageProcessor` that can run multiple analyzers (Contact Extractor, Ad-Buyer Detector).
2. **AI Logic Consolidation:** Unify LLM extraction patterns from `extraction.py` and `ad_buyer_detector.py` into a modular `ExtractionService`.
3. **API Modularization:** Refactor `src/api/main.py` using FastAPI Routers for better maintainability and scalability.
4. **Shared Schemas:** Establish a directory for shared Pydantic schemas used by both the Backend and Frontend (Streamlit Dashboard).
5. **Infrastructure Consolidation:** Unified `Dockerfile` and `requirements.txt` for all services (API, Dashboard, Worker).

## Architecture Changes

### Unified Message Processor
Current:
- `processor.py`: General contact extraction and embedding generation.
- `ad_processor.py`: Specialized ad-buyer detection and lead scoring.

Target:
- `MessageProcessor`: Orchestrates a chain of processors.
    - `ContactExtractor`: Extracts contact details from message text.
    - `AdBuyerDetector`: Evaluates if the message indicates an ad buyer.
    - `EmbeddingGenerator`: Generates vector embeddings for semantic search.
- All processors will use the single `deduplication.py` service for contact merging.

### Modular API
Current:
- Monolithic `src/api/main.py`.

Target:
- `src/api/routers/`:
    - `contacts.py`: Contact management endpoints.
    - `messages.py`: Message history and processing status.
    - `telegram.py`: Telegram authentication and session management.
    - `leads.py`: Lead scoring and ad-buyer specific insights.

### Consolidated Docker & Requirements
Current:
- `Dockerfile`, `Dockerfile.dashboard`.
- `requirements.txt`, `requirements-dashboard.txt`.

Target:
- Single `Dockerfile` (multi-stage) for API, Worker, and Dashboard.
- Single `requirements.txt` with optional dependency groups if necessary.

## Non-Functional Requirements
- **Test-Driven:** All unified logic must have unit tests covering both the general and specialized cases.
- **Backwards Compatibility:** Database models should remain compatible, or migrations must be provided for schema changes.
- **Maintainability:** Clear separation of concerns between AI logic, database operations, and API routing.
