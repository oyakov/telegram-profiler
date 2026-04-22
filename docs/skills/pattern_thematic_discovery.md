# Skill: Thematic Discovery & Automatic Expansion

## Problem
Manually identifying and joining relevant Telegram channels for multiple niches (Real Estate, News, Jobs, Cars) is slow and prone to missing valuable sources.

## Solution

### 1. Keyword-to-Niche Mapping
Define a configuration that maps specific keywords to target databases and Telegram folders.
- **Example:** "Белград аренда" -> `crm_bg_rent` -> "BG - Rent".

### 2. Automated Search & Filter
Use the Telegram Global Search API to find candidates, then filter by:
- **Participant Count:** Min 100-500 members to avoid spam/empty groups.
- **Deduplication:** Check the `TrackedChannel` table of the *specific* target database to skip existing ones.

### 3. Automated Join & Mute
Perform a "Silent Join" to avoid notification spam:
- `JoinChannelRequest`
- Immediately trigger `UpdateNotifySettingsRequest` to mute the channel.
- Use `UpdateFolderRequest` to place the new channel into the appropriate thematic folder.

## Implementation Details
See [multi_db_discover_and_expand.py](file:///c:/Projects/telegram-profiler/scripts/multi_db_discover_and_expand.py) for the implementation of the theme-based expansion engine.
