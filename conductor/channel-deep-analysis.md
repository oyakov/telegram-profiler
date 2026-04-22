# Channel Deep Analysis & History Deepening

## Objective
Implement a mechanism to gradually deepen the message history for whitelisted Telegram channels, run a "deep analysis" extraction (focusing on topics and entities) on channel messages, and specifically add `https://t.me/serbska_baraholka` to the whitelist to pull a few months of its historical data.

## Key Files & Context
- `src/ai/services.py`: Needs a new extraction schema and prompt for deep analysis.
- `src/pipeline/unified_processor.py`: Needs to incorporate the new deep analysis extraction step.
- `src/connectors/telegram_connector.py`: Needs a `deep_sync` method utilizing Telethon's `offset_id` or `offset_date` to fetch older messages.
- `src/pipeline/tasks.py`: Needs a Celery task to orchestrate the deep sync asynchronously.
- `src/api/routers/telegram.py`: Needs a manual trigger endpoint for deep sync.

## Implementation Steps

### Phase 1: AI Deep Analysis Setup
1. **Schema & Prompts (`src/ai/services.py`)**:
   - Define `ChannelDeepAnalysis` schema with fields for `topics` (list), `mentioned_companies` (list), `mentioned_products` (list), and `sentiment` (string).
   - Add `DEEP_ANALYSIS_SYSTEM_PROMPT` tailored to extract this specific information.
   - Update the `ExtractionService.extract` method to support the `deep_analysis` extraction type.

### Phase 2: Pipeline Integration
1. **Unified Processor (`src/pipeline/unified_processor.py`)**:
   - Modify `MessageProcessor.process_batch` to conditionally execute the new `deep_analysis` on channel messages.
   - Save the deep analysis results into the `ExtractionLog` table.

### Phase 3: History Deepening Engine
1. **Telegram Connector (`src/connectors/telegram_connector.py`)**:
   - Create a new method `deep_sync(chat_ids, limit)`.
   - The method will query the database to find the oldest message ID we have for each channel, and use Telethon's `offset_id` to paginate backwards and fetch historical messages.
2. **Celery Task (`src/pipeline/tasks.py`)**:
   - Implement `deepen_telegram_history_task(limit=500)` to run `deep_sync` in the background.
3. **API Endpoint (`src/api/routers/telegram.py`)**:
   - Add a `POST /deep-sync` endpoint to manually trigger the deepening task.

### Phase 4: Target Channel Setup & Execution
1. **Whitelist Configuration**:
   - Use the `SettingsService` or an SQL query to add `serbska_baraholka` to the `telegram_channel_whitelist`.
2. **Initial Sync**:
   - Trigger a sync for `serbska_baraholka` with an `offset_date` spanning back a few months to seed the initial historical data.

## Verification & Testing
- Ensure the API endpoint successfully triggers the Celery task.
- Verify `ExtractionLog` entries are created with topics and entity data for channel messages.
- Confirm `serbska_baraholka` messages from the past few months appear in the database.
