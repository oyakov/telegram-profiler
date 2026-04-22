# Specification: Belgrade Discovery & Ingestion

## Context
To build a comprehensive networking brain for Belgrade, we need to automatically identify, monitor, and ingest data from the most relevant local Telegram communities.

## Goals
- Automate the discovery of Belgrade-related Telegram channels and chats.
- Implement automatic subscription/joining for identified sources.
- Perform a one-time historical sync (1 year) for all new sources.
- Maintain a list of "monitored sources" to avoid duplicates.

## Technical Requirements
- **Discovery Engine:** Use Telethon's `SearchRequest` or keyword-based global search.
- **Filtering:** Rank by member count and verify relevance via keywords in titles/descriptions.
- **Automated Joining:** Use `JoinChannelRequest` for groups/channels.
- **Deep Sync Integration:** Trigger the existing `deep_sync_telegram` task for new IDs.

## Affected Components
- `src/connectors/telegram_connector.py` (New discovery methods)
- `src/pipeline/tasks.py` (New orchestration task)
- `dashboard/app.py` (UI to trigger discovery and see candidates)
