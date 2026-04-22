# Specification: Data Architecture & API Efficiency

## Context
The application suffers from N+1 query patterns in the API and performs redundant similarity calculations in Python that could be handled more efficiently in PostgreSQL with pgvector.

## Goals
- Eliminate N+1 query bottlenecks in API endpoints.
- Offload fuzzy deduplication filtering to the database level.
- Standardize database session management (Dependency Injection).

## Technical Requirements
- **Query Optimization:** Use `selectinload` or manual `IN` queries for related records in `leads.py`.
- **SQL Similarity:** Refactor `find_duplicate` to use `cosine_distance` filter directly in the SQLAlchemy query.
- **Session Decoupling:** Services should receive a session as an argument instead of managing their own session lifecycle.

## Affected Components
- `src/api/routers/leads.py`
- `src/ai/deduplication.py` (`find_duplicate`)
- `src/db/database.py` (Session handling)
