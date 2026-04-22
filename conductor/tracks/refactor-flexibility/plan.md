# Implementation Plan: System Flexibility & Final Consolidation

## Phase 1: Dynamic Settings
Decouple code from business configuration.

- [x] **Task 1.1: Migration for Lead Settings**
  Created `scripts/init_scoring_settings.py` to seed scoring weights and channel IDs.
- [x] **Task 1.2: Refactor `update_all_lead_scores`**
  Modified the scoring logic in `unified_processor.py` to fetch weights from `SettingsService`.

## Phase 2: Dashboard Alignment
Complete the "Integration & Consolidation" track's final phase.

- [x] **Task 2.1: Update Dashboard API Calls**
  Dashboard `app.py` already uses modular API endpoints.
- [x] **Task 2.2: Consistent Schemas**
  Removed hardcoded channel ID in Search page and linked it to DB settings.

## Phase 3: Final Cleanup
Clean the workspace.

- [x] **Task 3.1: Remove Deprecated Wrappers**
  Deleted legacy AI wrappers: `src/ai/extraction.py` and `src/ai/ad_buyer_detector.py`. Updated tests to use `ExtractionService`.
- [x] **Task 3.2: Script Audit**
  Identified redundant tools. Created migration script for scoring settings.
