# Core Concepts / Ключевые концепции

This document outlines the core architectural and business concepts powering the Networking Brain project.

---

## 1. Tracking: Folders vs. Channels / Отслеживание: Папки vs Каналы

### Tracked Folders / Отслеживаемые папки

**Folder** — логическая коллекция каналов или групп (e.g., "BG Intel", "Crypto"). В Telegram UI это соответствует chat folders (папкам чатов). В нашей системе они действуют как high-level классификация для организации данных.

*Characteristics / Характеристики:*
- Пользователь может создать несколько папок.
- Папка связана с одной БД.
- Каждая папка содержит несколько отслеживаемых каналов.
- Папка определяет область поиска и фильтрации.

### Tracked Channels / Отслеживаемые каналы

**Tracked Channel** — конкретный Telegram entity (канал или группа), которую система мониторит.

*Characteristics / Характеристики:*
- Каждый канал привязан к определенной **Папке**.
- Система автоматически **мьютит** (mutes) эти каналы в Telegram пользователя (предотвращение перегрузки уведомлениями).
- `last_sync_at` отслеживает, когда система в последний раз загрузила сообщения из этого канала.
- Каждый канал имеет уникальный `channel_id` в Telegram.
- Опциональные параметры: `auto_join`, `mute`, `archive`.

### Relationship / Связь папок и каналов
```
User (1) 
  └─ Database: crm (1)
      └─ Folder: Crypto (1)
          ├─ Channel: bitcoin (N)
          ├─ Channel: ethereum
          └─ Channel: defi
      └─ Folder: Belgrade News (1)
          ├─ Channel: bg_intel
          └─ Channel: serbia_business
```

---

## 2. Lead Scoring Algorithm / Алгоритм Lead Scoring

Система выявляет "Leads" и присваивает им **quality score**. Оценка рассчитывается в `src/ai/scorers/` на основе следующих факторов:

### Raw Score (Базовая оценка)
- Каждое обнаружение контакта начинает с базовой оценки качества (1-10), предоставленной LLM.
- Оценка зависит от уверенности модели в том, что это действительно потенциальный lead.

### Keyword Bonus (Бонус за ключевые слова)
Сообщения, содержащие высокоценные ключевые слова (e.g., `"dev"`, `"invest"`, `"ai"`, `"founder"`, `"startup"`), получают bonus.
- **Конфигурируется**: `scoring_weight_keyword_bonus` (default: `5.0`).
- **Формула**: `base_score + (number_of_keywords * keyword_bonus)`

### Recency Multipliers (Множители свежести)
Свежесть контакта влияет на score:
- **Recent Week Multiplier**: `3.0x` для сообщений из последних 7 дней. (Конфигурируется: `scoring_multiplier_recent_week`).
- **Recent Month Multiplier**: `2.0x` для сообщений из последних 30 дней. (Конфигурируется: `scoring_multiplier_recent_month`).

### Context (Контекст)
- **Channel Ratio**: Процент объявлений контакта, размещенные в "нашем" первичном отслеживаемом канале (Конфигурируется: `scoring_our_channel_id`).
- **Формула**:
  ```
  channel_ratio = (ads_in_our_channel / total_ads) * 100
  if channel_ratio > 50:
      score *= 1.5  # Bonus если контакт активен в наших каналах
  ```

### Full Scoring Formula / Полная формула scoring
```
raw_score = LLM_confidence (1-10)

adjusted_score = raw_score
  + (keyword_count * keyword_bonus)  // Keyword bonus
  * (3.0 if recent_week else 1.0)    // Week multiplier
  * (2.0 if recent_month else 1.0)   // Month multiplier
  * (1.5 if channel_ratio > 50 else 1.0)  // Channel context

final_score = min(100, max(1, adjusted_score))
```

### Lead Classifications
- **90-100**: ⭐⭐⭐⭐⭐ Premium Lead (немедленное внимание)
- **70-89**:  ⭐⭐⭐⭐  High Priority (действуйте сегодня)
- **50-69**:  ⭐⭐⭐   Medium Priority (на неделю)
- **30-49**:  ⭐⭐    Low Priority (в список)
- **1-29**:   ⭐     Research (для будущего)

---

## 3. Persistent Sessions / Постоянные Сессии

Система использует **PostgreSQL-backed Telethon sessions** (класс `PostgresTelegramSession`), исключая использование классических SQLite `.session` файлов. Сессия сохраняется в виде сериализованной и опционально зашифрованной (через Fernet) строки `StringSession` в таблице `telegram_sessions` соответствующей базы данных.

### Multi-DB Session Management
Каждая папка/база данных хранит свои данные сессии изолированно внутри своей схемы в PostgreSQL:
```
PostgreSQL Database: <db_name>
└── Table: telegram_sessions
    └── Row: session_name ("telethon_session"), session_data (encrypted or plaintext StringSession), user_id, is_active
```
Это полностью устраняет проблемы с конкурентным доступом к файловой системе и блокировками файлов, обеспечивая горизонтальное масштабирование Celery-воркеров.

### Session Lifecycle / Жизненный цикл сессии
1. **Пользователь авторизуется** $\to$ Отправляется OTP код на телефон $\to$ Генерируется StringSession и сохраняется в таблицу `telegram_sessions`.
2. **Система использует session для** $\to$ Загрузки StringSession из БД $\to$ Подключения к Telegram без повторной авторизации $\to$ Синхронизации сообщений $\to$ Мониторинга каналов.
3. **При выходе** $\to$ Сессия удаляется из PostgreSQL (или деактивируется при явном logout).

---

## 4. Extraction Pipeline / Конвейер извлечения

### Pipeline Steps
1. **Ingestion (Приемка)**: Telegram сообщения загружаются через API Telethon и сохраняются в таблице `messages`.
2. **Detection (Обнаружение)**: LLM анализирует контент сообщения, извлекая контакты, лиды и метаданные с confidence score (0-1).
3. **Deduplication (Дедупликация)**: Проверка существования контакта по Telegram ID, Username, Email или похожему имени (fuzzy matching). Если найден — обновляется, иначе создается новый.
4. **Embedding (Векторизация)**: Генерация векторных представлений сообщений/контактов с сохранением в `pgvector` для семантического поиска.
5. **Scoring (Ранжирование)**: Вычисление финального Lead Score.

```
Telegram Messages
    ↓
[Ingestion] → messages table
    ↓
[Detection] → Contact + metadata (LLM)
    ↓
[Deduplication] → Check existing contacts
    ├─ Found → Update existing
    └─ Not found → Create new
    ↓
[Embedding] → Vector representation
    ↓
[Scoring] → Lead Score
    ↓
[Storage] → contacts + leads tables
```

---

## 5. Semantic Search / Семантический поиск

Семантический поиск позволяет находить контакты по смыслу запроса, а не только по точному совпадению ключевых слов.

*How It Works:*
```
User Query: "blockchain developer looking for investment"
    ↓
[Embedding] → Vector representation
    ↓
[pgvector] → Similarity search (HNSW index)
    ↓
[Ranking] → Sort by cosine similarity score (Threshold: 0.52 cosine distance)
    ↓
Results: Top contacts matching the query
```

---

## 6. Telegram Folder Import Feature / Импорт Папок Telegram

### What are Telegram Folders?
Папки Telegram (внутреннее название: `dialog filters`) — созданные пользователем коллекции для организации чатов.

### How Import Works
1. **List Folders**: Вызов `list_telegram_folders()` для получения структуры папок и peer ID.
2. **Import Channels**: При выборе папки запускается `import_folder_channels(peer_ids)`.
3. **Resolve Entities**: Для каждого peer_id вызывается Telethon `get_entity()` для извлечения Channel/Chat.
4. **Deduplicate**: Проверка существования отслеживаемого канала и обновление связей.
5. **Save to Database**: Запись новых `TrackedChannel` связанных с выбранной папкой.

### Retry Logic / Логика повторных попыток
В старых версиях импорта использовался **exponential backoff retry** для обхода блокировок файлов SQLite (`sqlite3.OperationalError: database is locked`). В текущей архитектуре эта проблема полностью решена благодаря переходу на PostgreSQL-backed сессии (`PostgresTelegramSession`). Система работает конкурентно и надежно без ошибок взаимной блокировки файлов.

### UUID Type Safety
API-эндпоинт принимает `folder_id` как строку UUID и конвертирует ее в Python-объект UUID перед выполнением SQL-запроса:
```python
from uuid import UUID
if isinstance(folder_id, str):
    folder_id = UUID(folder_id)
```
Это предотвращает ошибки `sqlalchemy.exc.ProgrammingError: operator does not exist: uuid = integer`.

For detailed implementation, see the [Telegram Folder Import Feature](../05-features/telegram-folder-import.md) guide.

---

**Last Updated / Последнее обновление**: 2026-05-20  
