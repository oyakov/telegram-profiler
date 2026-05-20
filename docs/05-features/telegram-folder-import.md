# Telegram Folder Import Feature

## Overview

The Telegram Folder Import feature allows users to bulk-import channels from their Telegram folder structure into Networking Brain's folder organization system. This streamlines the onboarding process and helps users quickly populate their tracked channels.

## How It Works

### User Flow

1. **Navigate to Folders**: User opens the "Папки" (Folders) section in the dashboard
2. **Select Import**: Click the "Import" button on any tracked folder
3. **Load Telegram Folders**: System fetches user's Telegram folders (dialog filters)
4. **Select Channels**: User selects which Telegram folder's channels to import
5. **Confirm Import**: System imports selected channels into the chosen tracked folder

### System Architecture

```
Frontend (React)
    ↓
POST /api/telegram/folders/import
    ↓
Backend (FastAPI)
    ├─ Validate folder_id (UUID conversion)
    ├─ Retrieve peer_ids from request
    ├─ Import channels via TelegramConnector
    │   ├─ Retry logic (exponential backoff)
    │   ├─ Handle database locks
    │   └─ Deduplicate channels
    ├─ Save to TrackedChannel table
    └─ Return import results (added, moved, total)
```

## Technical Details

### Endpoints

#### 1. List Telegram Folders
```http
GET /api/telegram/folders
Headers: X-Database: crm
```

**Response**:
```json
{
  "folders": [
    {
      "name": "Personal",
      "id": 4,
      "channel_count": 1,
      "peer_ids": ["728556838"]
    },
    {
      "name": "IT",
      "id": 2,
      "channel_count": 4,
      "peer_ids": ["1001528034935", "1185216597", ...]
    }
  ]
}
```

#### 2. Import Channels from Telegram Folder
```http
POST /api/telegram/folders/import
Headers: X-Database: crm
Content-Type: application/json

{
  "folder_id": "550e8400-e29b-41d4-a716-446655440000",
  "peer_ids": ["1001528034935", "1185216597", "1001926137427"]
}
```

**Response**:
```json
{
  "status": "success",
  "added": 2,
  "moved": 1,
  "total": 3
}
```

### Database Schema

#### TrackedFolder Table
- `id` (UUID, Primary Key)
- `name` (String)
- `description` (String, optional)
- `tags` (Array of Strings)
- `created_at` (Timestamp)
- `updated_at` (Timestamp)

#### TrackedChannel Table
- `id` (String, Primary Key)
- `folder_id` (UUID, Foreign Key to TrackedFolder)
- `telegram_id` (String) — Telegram's internal ID
- `title` (String)
- `username` (String, optional)
- `entity_type` (Enum: "channel" | "group")
- `created_at` (Timestamp)
- `last_sync` (Timestamp)

### Error Handling & PostgreSQL Sessions

Previously, when multiple celery workers accessed Telethon's SQLite session files simultaneously, they would encounter `sqlite3.OperationalError: database is locked` errors.

To address this, the system was refactored to use **PostgreSQL-backed sessions** (`PostgresTelegramSession`). StringSession data is loaded directly from each workspace's database and cached in-memory with asyncio locks. 

#### Modern Architecture Highlights
- **No SQLite Files**: No lock-contention issues on the filesystem.
- **Asyncio Locks**: In-process operations are coordinated via `asyncio.Lock()` to avoid race conditions.
- **Robust Client Factory**: The `TelegramClientFactory` handles client creation dynamically per database workspace.

#### Code Location
File: `src/services/telegram/management_service.py`

```python
async def import_folder_channels(self, peer_ids: List[str]) -> List[dict]:
    """Resolve a list of peer IDs to channel/group info."""
    client = await self.factory.get_client()
    try:
        async with client:
            channels = []
            for pid in peer_ids:
                try: 
                    entity = await client.get_entity(-int(pid))
                except Exception:
                    try: 
                        entity = await client.get_entity(int(pid))
                    except Exception: 
                        continue
                
                if not isinstance(entity, (Channel, Chat)): 
                    continue
                    
                is_channel = isinstance(entity, Channel) and entity.broadcast
                channels.append({
                    "telegram_id": str(entity.id), 
                    "title": getattr(entity, "title", "Unknown"),
                    "username": getattr(entity, "username", None), 
                    "entity_type": "channel" if is_channel else "group"
                })
            return channels
    except Exception as e:
        logger.error("import_folder_channels_error", error=str(e))
        return []
```

## Known Limitations & Edge Cases

### 1. Partial Imports
Some peer_ids may fail to import due to:
- **Archived channels**: Channels archived by user cannot be accessed
- **Type mismatches**: Non-Channel/Chat entities (e.g., Bot communities)
- **Permission issues**: Channels where user lost access rights
- **Network issues**: Transient Telegram API failures

**Mitigation**: The system logs which peer_ids fail and why, allowing users to retry or manually add channels.

### 2. Database Locking
With the deprecated SQLite session system, multiple workers accessing the session file simultaneously would cause database locks. This has been fully resolved by adopting `PostgresTelegramSession`, which manages sessions inside PostgreSQL with in-memory asyncio locks.

### 3. UUID Type Handling
The `folder_id` is sent from frontend as a string UUID but must be converted to Python UUID object for database queries.

```python
# In telegram_import_folder endpoint:
try:
    if isinstance(folder_id, str):
        folder_id = UUID(folder_id)
except ValueError:
    raise HTTPException(400, "Invalid folder_id format")
```

## Monitoring & Debugging

### Logging
Detailed logs are emitted during import:
```
logger.info("telegram_auto_tracked", chat_id=tg_id, folder=folder_name, db=db_name)
logger.warning("Failed to get entity for peer_id: ...")
logger.warning("Entity is not a Channel/Chat: ...")
```

### Checking Import Status
View backend logs to see detailed import results:
```bash
docker logs crm-app | grep "telegram_auto_tracked"
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "User profile not found" | Not authenticated to Telegram | Complete Telegram OAuth flow first |
| "operator does not exist: uuid = integer" | Type mismatch on folder_id | Convert folder_id to UUID |
| Only 2 of 4 channels imported | Some peers failed silently | Check logs for peer_id failures |

## Future Improvements

### Planned Enhancements
- [ ] Batch import with progress indicator
- [ ] Selective channel filtering before import (search, filter by member count)
- [ ] Automatic folder creation from Telegram folder names
- [ ] Dry-run mode to preview what will be imported
- [ ] Async import notifications (webhook/websocket)

### Performance Optimization
- [ ] Cache Telegram folder list to avoid repeated fetches
- [ ] Parallel peer_id resolution (batch get_entity calls)
- [ ] Background import task instead of blocking endpoint

---

**Last Updated**: 2026-05-09
**Maintained By**: Engineering Team
**Related Files**: `src/api/routers/telegram.py`, `src/connectors/telegram_connector.py`
