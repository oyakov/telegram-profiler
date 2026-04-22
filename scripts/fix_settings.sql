DELETE FROM settings;
INSERT INTO settings (key, value, value_type, description, category) VALUES
('telegram_sync_enabled', 'false', 'bool', 'Enable Telegram connector', 'connectors'),
('telegram_chat_whitelist', '[]', 'json', 'List of Telegram chat IDs to sync', 'connectors'),
('telegram_channel_whitelist', '["workshopiy", "ruskie_v_belgrade"]', 'json', 'List of Telegram channel usernames to monitor for ads', 'connectors'),
('telegram_initial_limit', '100', 'int', 'Messages to fetch on initial sync per chat', 'connectors'),
('excel_auto_import', 'false', 'bool', 'Auto-import new Excel files from uploads/', 'connectors'),
('crm_sync_enabled', 'false', 'bool', 'Enable CRM REST API connector', 'connectors'),
('crm_api_url', '', 'string', 'CRM API base URL', 'connectors'),
('crm_api_key', '', 'string', 'CRM API key', 'connectors'),
('social_sync_enabled', 'false', 'bool', 'Enable social media scraping', 'connectors'),
('dedup_cosine_threshold', '0.85', 'float', 'Cosine similarity threshold for deduplication', 'processing'),
('embedding_batch_size', '50', 'int', 'Batch size for embedding generation', 'processing'),
('llm_extraction_enabled', 'true', 'bool', 'Enable LLM-based fact extraction', 'processing'),
('sync_interval_minutes', '30', 'int', 'Interval between automatic syncs', 'scheduling');
