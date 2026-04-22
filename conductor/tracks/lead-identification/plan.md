# Implementation Plan: Lead Identification (Ad Buyers)

## Phase 1: Infrastructure & Data Acquisition
*Goal: Extend core capabilities to support channel monitoring and ad buyer fields.*

- [x] **Task 1: Database Migration.**
  - Add `is_ad_buyer`, `ad_buyer_score`, and `ad_context` to the `Contact` model.
  - Create an Alembic migration for these changes.
- [x] **Task 2: Extend Telegram Connector.**
  - Modify `TelegramConnector._sync_chat` to handle channels and distinguish between direct messages and channel posts.
  - Add support for a `telegram_channel_whitelist` in settings.
- [x] **Task 3: Implement Ad Buyer Detection Logic.**
  - Create a new AI prompt specifically for ad buyer identification.
  - Implement a specialized extraction function `extract_ad_buyer(text: str)`.

## Phase 2: Core Logic & AI Integration
*Goal: Process messages and identify ad buyers.*

- [x] **Task 4: Celery Task for Ad Processing.**
  - Create a background task that periodically scans new channel messages for ad buyers.
  - Update `Contact` records when a buyer is identified.
- [x] **Task 5: Initial Ranking Heuristic.**
  - Implement a simple service to update `ad_buyer_score` based on purchase frequency and recency.
- [x] **Task 6: Verification & Edge Case Handling.**
  - Ensure duplicate mentions or non-ad messages (e.g., "Shared from...") are not misclassified as ads.

## Phase 3: Dashboard & User Experience
*Goal: Visualize and interact with the identified leads.*

- [x] **Task 7: Ad Buyer Insights Dashboard.**
  - Add a new page/tab to the Streamlit app showing ranked ad buyers.
  - Display a table of top leads with their score and most recent ad.
- [x] **Task 8: Detail View.**
  - Implement a drill-down view to show all messages related to a specific ad buyer.
- [x] **Task 9: Final Quality Gate.**
  - Verify overall system performance, accuracy, and ensure >80% code coverage for new modules.
