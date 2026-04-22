# Implementation Plan: Many-to-Many Linking for Messages and Contacts

## Objective
Implement a robust linking mechanism between messages and contacts to support multiple roles (sender, ad buyer, mention). This will allow for precise filtering of messages by user (as either a sender or a mentioned subject) across different Telegram channels.

## Key Files & Context
- `src/db/models.py`: Update with `MessageContact` association table and relationship.
- `src/connectors/telegram_connector.py`: Link messages to senders during sync.
- `src/pipeline/unified_processor.py`: Link messages to ad buyers during AI processing.
- `src/api/routers/messages.py`: Update filtering logic to use the new relationship and support channel filtering.

## Implementation Steps

### Phase 1: Schema Updates
1.  **Add `MessageContact` model in `src/db/models.py`**:
    - `id`: UUID (Primary Key)
    - `message_id`: UUID (Foreign Key to `messages.id`)
    - `contact_id`: UUID (Foreign Key to `contacts.id`)
    - `role`: String (e.g., "sender", "ad_buyer", "mention")
    - `created_at`: DateTime
2.  **Update `Message` and `Contact` models**:
    - Add `secondary` relationships via `MessageContact`.
    - `Message.associated_contacts`
    - `Contact.associated_messages`

### Phase 2: Pipeline & Connector Updates
1.  **`src/connectors/telegram_connector.py`**:
    - In `_sync_chat`, after creating a `Message`, create a `MessageContact` entry with `role="sender"` linking the message to the sender contact.
2.  **`src/pipeline/unified_processor.py`**:
    - In `_sync_ad_buyer`, after linking the message to the buyer in the JSON context, create a `MessageContact` entry with `role="ad_buyer"`.
    - Ensure duplicate links are not created if processing is re-run.

### Phase 3: API & Filtering
1.  **`src/api/routers/messages.py`**:
    - Update `search_messages` to accept a `contact_id` and/or `telegram_id`.
    - If `contact_id` or `telegram_id` is provided, join with `MessageContact` (and `Contact` if using `telegram_id`) to find all messages where the user is involved in any role (or a specific role if requested).
    - Add `group_id` (Channel ID) as an explicit filter parameter to `search_messages`.

### Phase 4: Migration (Optional but Recommended)
1.  Create an Alembic migration for the new table.
2.  (Optional) A script to populate the `MessageContact` table from existing `Message.contact_id` (as "sender").

## Verification & Testing
1.  **Manual Sync**: Run a Telegram sync and verify `MessageContact` entries are created for senders.
2.  **AI Processing**: Run `process_unprocessed_messages` on a channel message with an ad buyer and verify an `ad_buyer` link is created.
3.  **API Test**:
    - Query `/messages/search?contact_id=<Buyer_UUID>` and verify it returns messages where they are the buyer.
    - Query `/messages/search?contact_id=<User_UUID>&group_id=<Channel_ID>` to test cross-filtering.
