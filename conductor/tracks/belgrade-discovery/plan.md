# Implementation Plan: Belgrade Data Expansion

## Phase 1: Discovery Mechanism
Identify potential sources.

- [ ] **Task 1.1: Implement Keyword Search in `TelegramConnector`**
  Add a method to search for channels/chats by keywords (Belgrade, Beograd, etc.) and return metadata (ID, title, member count).
- [ ] **Task 1.2: Candidate Filtering Logic**
  Create a utility to filter candidates based on member thresholds (e.g., > 500 members) and title relevance.

## Phase 2: Automated Ingestion
Subscribe and fetch history.

- [ ] **Task 2.1: Automated Joining**
  Implement logic to join/subscribe to found sources. Use delays and small batches to avoid Telegram flood limits.
- [ ] **Task 2.2: Historical Batch Sync**
  Orchestrate a pipeline that joins a channel and immediately queues a `deep_sync` for 365 days.

## Phase 3: UI & Monitoring
Control the expansion from the Dashboard.

- [ ] **Task 3.1: Discovery Page**
  Add a "Discovery" tab in the Dashboard to search for new communities and see a list of "Candidates" before joining.
- [ ] **Task 3.2: Stats Update**
  Ensure new channels are properly reflected in the Analytics page.
