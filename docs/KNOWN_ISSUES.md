# Known Issues

## 1. Personal Contacts vs Contacts Show Same Count

**Status**: 🔴 Open  
**Severity**: Medium  
**Component**: Frontend / Database  
**Reported**: 2026-05-09

### Description
Both "Контакты" (Contacts) and "Личные Контакты" (Personal Contacts) pages display the same total count (1436), suggesting they're querying the same data without proper filtering.

### Root Cause
- The `Contact` model in `src/db/models.py` lacks an `is_personal` or `saved` field
- `PersonalContacts.tsx` queries `/api/contacts?source=telegram` but this only filters by source, not by personal status
- No database mechanism exists to distinguish between extracted contacts and user-saved personal contacts

### Expected Behavior
- **Контакты** (Index-Контактов): All extracted contacts (1436)
- **Личные Контакты**: Only user-saved personal contacts (should be much smaller number)

### Actual Behavior
Both pages show 1436 contacts

### Files Affected
- `frontend/src/pages/Contacts.tsx` — queries all contacts
- `frontend/src/pages/PersonalContacts.tsx` — queries with source filter only
- `src/db/models.py` — Contact model missing is_personal field
- `src/api/routers/contacts.py` — API endpoint lacks personal filtering logic

### Solution (Steps to Fix)

#### 1. Update Database Model
Add `is_personal` field to Contact model:
```python
# src/db/models.py
class Contact(Base):
    ...
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    saved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

#### 2. Create Migration
```bash
alembic revision --autogenerate -m "Add is_personal field to contacts"
```

#### 3. Update API Endpoints
```python
# src/api/routers/contacts.py
@router.get("/contacts")
async def get_contacts(
    page: int = 1,
    page_size: int = 50,
    is_personal: Optional[bool] = None,
    ...
):
    query = select(Contact)
    if is_personal is not None:
        query = query.where(Contact.is_personal == is_personal)
```

#### 4. Update Frontend
```tsx
// PersonalContacts.tsx - change query
const { data } = useSWR(
  `/api/contacts?page=${page}&page_size=50&is_personal=true`,
  fetcher
);
```

#### 5. Add UI to Save/Unsave Contacts
- Add "Save to Personal" button in Contacts page
- Add "Remove from Personal" button in Personal Contacts page
- Make these buttons call PATCH endpoint

### Workaround
Currently, no workaround exists. Users cannot distinguish their saved personal contacts from automatically extracted ones.

### Testing
After fix, verify:
1. Regular Contacts page still shows ~1436
2. Personal Contacts page shows 0 (until user saves some)
3. Can save contacts to personal list
4. Count updates when saving/removing

---

## 2. Folder Import - Partial Success with No Indication

**Status**: 🟡 Open  
**Severity**: Low  
**Component**: Telegram Integration  
**Reported**: 2026-05-09

### Description
When importing channels from a Telegram folder, some peer_ids may fail silently without clear user feedback about which channels failed and why.

### Example
- User imports IT folder with 4 channels
- Only 2 are imported successfully
- No detailed message about which 2 failed and why

### Root Cause
- Retry logic swallows individual peer_id failures
- Frontend only shows aggregate count (added, moved, total)
- Backend logs contain details but users don't see them

### Solution
- Enhance API response to include failed peer_ids with reason codes
- Display failed imports in frontend modal
- Allow user to retry failed imports

---

## 3. Database Lock Issues During Concurrent Imports

**Status**: 🟢 Mitigated (has workaround)  
**Severity**: Medium  
**Component**: Telegram Connector  
**Reported**: 2026-05-09

### Description
Multiple simultaneous folder import requests can trigger "database is locked" errors when Telethon's SQLite session database gets accessed concurrently.

### Current Solution
- Exponential backoff retry logic (0.5s → 1s → 2s) in `import_folder_channels()`
- Automatically retries up to 3 times
- Works for most cases but can still timeout under extreme load

### Ideal Solution
- Move session database to shared location or use file locking
- Serialize Telethon client access with a lock
- Use async-safe session management

---

**Last Updated**: 2026-05-09  
**Maintained By**: Engineering Team
