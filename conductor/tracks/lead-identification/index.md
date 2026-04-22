# Track 01: Lead Identification (Ad Buyers)

## Status
- **Progress:** 100%
- **Status:** `[x]`

## Objectives
The primary objective of this track is to implement the "Networking Brain's" first high-value use case: identifying and ranking individuals who buy advertisements in specific Telegram channels.

1.  **Configure Channel Monitoring:** Allow the Telegram connector to sync from specific, ad-heavy channels.
2.  **Ad-Buyer Extraction Logic:** Develop LLM-based extraction to identify buyers from channel messages (e.g., "Ad by @username" or "Thanks to @username for the placement").
3.  **Lead Scoring & Ranking:** Implement a preliminary scoring system based on frequency and context of mentions.
4.  **Dashboard Integration:** Create a simple view in the Streamlit dashboard to see the top-ranked ad buyers.

## Key Files
- `src/connectors/telegram_connector.py`
- `src/ai/extraction.py`
- `src/db/models.py`
- `dashboard/app.py`
- `src/pipeline/tasks.py`

## Links
- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
