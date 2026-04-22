# Specification: Lead Identification (Ad Buyers)

## Overview
The system must identify "Ad Buyers" from Telegram channel messages. Ad Buyers are individuals (often represented by a Telegram username) who are mentioned in channels as having purchased an advertisement or sponsored a post.

## Requirements

### 1. Channel Monitoring
- Extend `TelegramConnector` to handle syncing from **channels**, not just user dialogs.
- Support a whitelist of channel usernames/IDs to monitor for ad activity.
- Efficiently fetch only recent messages to avoid overwhelming the system.

### 2. Ad-Buyer Extraction
- Enhance the AI extraction module with a specific prompt for identifying "Ad Buyers".
- Identify:
  - The buyer's name or username.
  - The context of the ad (what was advertised, if possible).
  - The channel where the ad appeared.
  - The date and time of the ad.
- Map these to the existing `Contact` and `Message` models.

### 3. Lead Scoring & Ranking
- A contact's "Lead Score" or "Rank" will be calculated based on:
  - **Frequency:** How many ads they've bought across all monitored channels.
  - **Recency:** Bonus for very recent ad purchases.
  - **Context:** LLM-assessed "quality" of the ad or the buyer's profile (e.g., is it a known high-value brand or a person?).

### 4. Database Schema Updates
- Add `is_ad_buyer` (Boolean) to the `Contact` model.
- Add `ad_buyer_score` (Float) to the `Contact` model.
- Add `ad_context` (JSONB/Text) to track ad-specific metadata for each contact.
- Store ad-specific findings in `facts_json`.

### 5. Dashboard View
- Create a dedicated "Ad Buyer Insights" tab in the Streamlit dashboard.
- Display a ranked table of ad buyers.
- Allow clicking a buyer to see their ad history (messages that mentioned them as a buyer).

## Technical Details

### AI Prompting
A new system prompt will be created to specifically look for "Ad Buyer" patterns in channel messages:
- "This post is sponsored by @username"
- "Promo for @username"
- "Ads by @username"
- "Follow @username for more..." (when context implies sponsorship)

### Ranking Algorithm (Initial Version)
`score = count(ads_last_30_days) * 2.0 + count(ads_older) * 1.0`
(We'll refine this later with LLM-based qualitative assessment).

## Success Criteria
1.  System can successfully sync messages from at least 3 pre-defined Telegram channels.
2.  LLM correctly identifies at least 80% of ad buyers in a sample of 100 recent messages.
3.  The Streamlit dashboard correctly displays a list of identified buyers, ranked by their frequency of ad purchases.
