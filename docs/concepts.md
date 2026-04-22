# Core Concepts: Networking Brain

This document explains the key concepts and algorithms used in the Networking Brain project.

## 1. Tracking: Folders vs. Channels

### Tracked Folders
A **Folder** is a logical collection of channels or groups (e.g., "BG Intel", "Crypto"). In the Telegram UI, these correspond to chat folders. In our system, they act as a high-level classification.

### Tracked Channels
A **Tracked Channel** is a specific Telegram entity (channel or group) that the system monitors.
- Each channel is linked to a **Folder**.
- The system automatically mutes these channels in the user's Telegram to prevent notification overload.
- `last_sync_at` tracks when the system last fetched messages from this specific channel.

## 2. Lead Scoring Algorithm

The system identifies "Leads" and assigns a quality score. The score is calculated in `src/pipeline/unified_processor.py` based on:

### Raw Score
- Each detection starts with a base quality (1-10) provided by the LLM.
- **Keyword Bonus**: Messages containing high-value keywords (e.g., "dev", "invest", "ai") receive a bonus (Configurable: `scoring_weight_keyword_bonus`, default: 5.0).

### Recency Multipliers
- **Recent Week**: Multiplier applied to messages from the last 7 days (Configurable: `scoring_multiplier_recent_week`, default: 3.0x).
- **Recent Month**: Multiplier applied to messages from the last 30 days (Configurable: `scoring_multiplier_recent_month`, default: 2.0x).

### Context
- **Channel Ratio**: The percentage of a contact's ads that were posted in "our" primary monitored channel (Configurable: `scoring_our_channel_id`).

## 3. Persistent Sessions
The system uses Telethon sessions stored in the `sessions/` directory. Each database (e.g., `crm` vs `crm_crypto`) can have its own dedicated session file to allow simultaneous monitoring of different accounts or separate tracking environments.

## 4. Extraction Pipeline
1. **Ingestion**: Telegram messages are fetched and stored in the `messages` table.
2. **Detection**: LLMs analyze message content to identify contacts or leads.
3. **Deduplication**: The system searches for existing contacts by Telegram ID, Username, Email, or Name before creating new ones.
4. **Embedding**: Both contacts and messages are vectorized using `pgvector` to enable semantic search.
