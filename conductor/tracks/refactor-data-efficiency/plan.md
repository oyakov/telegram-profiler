# Implementation Plan: Data Architecture & API Efficiency

## Phase 1: API Optimization (N+1)
Improve the responsiveness of lead-related endpoints.

- [x] **Task 1.1: Optimize `get_ad_history`**
  Refactor the history retrieval to fetch all messages in a single query with an `IN` clause.
- [x] **Task 1.2: Global API Review**
  Check other routers (`contacts.py`, `messages.py`) for similar N+1 patterns. (Optimized core leads endpoint).

## Phase 2: Database Deduplication
Move logic closer to the data.

- [x] **Task 2.1: SQL-level Similarity Filter**
  Update `find_duplicate` to include a `WHERE distance < threshold` clause using pgvector's operators.
- [x] **Task 2.2: Remove Redundant Python Logic**
  Cleanup the post-query cosine similarity checks in `deduplication.py`.

## Phase 3: Session Management Refactor
Standardize how services interact with the DB.

- [x] **Task 3.1: Refactor `SettingsService`**
  (Already supported session injection).
- [x] **Task 3.2: Refactor Pipeline Functions**
  Updated `unified_processor.py` to support optional session injection for all main functions.
