# Ключевые концепции

## 1. Отслеживание: Папки vs Каналы

### Отслеживаемые папки (Folders)

**Папка** — логическая коллекция каналов или групп (e.g., "BG Intel", "Crypto"). В Telegram UI это соответствует chat folders (папкам чатов). В нашей системе они действуют как high-level классификация для организации данных.

**Характеристики**:
- Пользователь может создать несколько папок
- Папка связана с одной БД
- Каждая папка содержит несколько отслеживаемых каналов
- Папка определяет область поиска и фильтрации

### Отслеживаемые каналы (Tracked Channels)

**Отслеживаемый канал** — конкретный Telegram entity (канал или группа), которую система мониторит.

**Характеристики**:
- Каждый канал привязан к определенной **Папке**
- Система автоматически **мьютит** эти каналы в Telegram пользователя (предотвращение перегрузки уведомлениями)
- `last_sync_at` отслеживает, когда система в последний раз загрузила сообщения из этого канала
- Каждый канал имеет уникальный `channel_id` в Telegram
- Опциональные параметры: `auto_join`, `mute`, `archive`

### Связь между папками и каналами

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

## 2. Алгоритм Lead Scoring

Система выявляет "Leads" и присваивает им **quality score**. Оценка рассчитывается в `src/ai/scorers/` на основе:

### Raw Score (Базовая оценка)

- Каждое обнаружение контакта начинает с базовой оценки качества (1-10), предоставленной LLM
- Оценка зависит от уверенности модели в том, что это действительно потенциальный lead

### Keyword Bonus (Бонус за ключевые слова)

Сообщения, содержащие высокоценные ключевые слова, получают bonus:

**Примеры high-value keywords**: "dev", "invest", "ai", "founder", "startup", "product", "blockchain", "crypto", "trading", "project"

**Конфигурируется**: `scoring_weight_keyword_bonus` (default: 5.0)

**Формула**: `base_score + (number_of_keywords * keyword_bonus)`

### Recency Multipliers (Множители свежести)

Свежесть контакта влияет на score:

**Recent Week Multiplier**: 3.0x для сообщений из последних 7 дней
- Активные люди в последнюю неделю более ценны
- **Конфигурируется**: `scoring_multiplier_recent_week`

**Recent Month Multiplier**: 2.0x для сообщений из последних 30 дней
- Менее агрессивное усиление для месячного периода
- **Конфигурируется**: `scoring_multiplier_recent_month`

### Context (Контекст)

**Channel Ratio**: Процент объявлений контакта, размещенные в "нашем" первичном отслеживаемом канале

**Формула**:
```
channel_ratio = (ads_in_our_channel / total_ads) * 100

if channel_ratio > 50:
    score *= 1.5  # Bonus если контакт активен в наших каналах
```

### Полная формула scoring

```
raw_score = LLM_confidence (1-10)

adjusted_score = raw_score
  + (keyword_count * keyword_bonus)  // Keyword bonus
  * (3.0 if recent_week else 1.0)    // Week multiplier
  * (2.0 if recent_month else 1.0)   // Month multiplier
  * (1.5 if channel_ratio > 50 else 1.0)  // Channel context

final_score = min(100, max(1, adjusted_score))
```

### Пример расчета

```
Message: "Hey, I'm a blockchain developer looking for AI projects"

1. LLM confidence: 7/10
2. Keywords found: "developer" (5), "blockchain" (5), "ai" (5) = 15 points
3. Posted 3 days ago: * 3.0 (recent_week)
4. Posted in #crypto_dev channel: * 1.5 (our_channel)

Score = 7 + 15 = 22
Score = 22 * 3.0 (recent) = 66
Score = 66 * 1.5 (channel) = 99 → Финальный score: 100 (max)
```

### Lead Classifications по score

```
90-100: ⭐⭐⭐⭐⭐ Premium Lead (немедленное внимание)
70-89:  ⭐⭐⭐⭐  High Priority (действуйте сегодня)
50-69:  ⭐⭐⭐   Medium Priority (на неделю)
30-49:  ⭐⭐    Low Priority (в список)
1-29:   ⭐     Research (для будущего)
```

## 3. Persistent Sessions

Система использует **Telethon sessions** (сохраненные в `sessions/` директории). 

### Зачем нужны сессии?

- Сохранение состояния Telegram подключения
- Избежание повторной авторизации
- Возможность нескольких одновременных сессий
- Переиспользование подключений

### Multi-DB Session Management

Каждая база данных может иметь свой dedicated session файл:

```
sessions/
├── crm.session                 # Main DB session
├── crm_research.session        # Research DB session
├── crm_personal.session        # Personal DB session
└── crm_<folder_name>.session   # Per-folder sessions (опционально)
```

### Жизненный цикл сессии

```
1. Пользователь авторизуется
   → Отправляется OTP код на телефон
   → Сохраняется session файл

2. Система использует session для:
   → Подключение к Telegram без повторной авторизации
   → Синхронизация сообщений
   → Мониторинг каналов

3. При выходе:
   → Сессия остается для будущего использования
   → Может быть удалена при logout
```

### Управление сессиями в API

```python
# src/api/auth.py
@router.post("/auth/login")
async def login(phone: str, db_name: str = "crm"):
    """
    1. Проверка существует ли session
    2. Если нет → запрос OTP
    3. Сохранение session после подтверждения
    """
    session_file = f"sessions/{db_name}.session"
    if not os.path.exists(session_file):
        # Требуется OTP авторизация
        ...
    else:
        # Использование существующей session
        ...
```

## 4. Extraction Pipeline (Конвейер извлечения)

### Шаги процесса

**1. Ingestion (Приемка)**
- Telegram сообщения загружаются через API Telethon
- Сохраняются в таблице `messages`
- Каждое сообщение получает `message_id`, `channel_id`, `timestamp`, `content`

**2. Detection (Обнаружение)**
- LLM анализирует контент сообщения
- Выявляет: имена, email, номера телефонов, должности, компании
- Создает JSON с извлеченной информацией
- Присваивает confidence score (0-1)

**3. Deduplication (Дедупликация)**
- Система проверяет, существует ли уже контакт с:
  - Тем же Telegram ID
  - Тем же username
  - Тем же email
  - Похожим именем (fuzzy matching)
- Если найден → обновить существующий контакт
- Если нет → создать новый

**4. Embedding (Векторизация)**
- Сообщение преобразуется в embedding (vector)
- Сохраняется в pgvector для семантического поиска
- Позволяет find похожие сообщения по смыслу

**5. Scoring (Ранжирование)**
- Применяется Lead Scoring Algorithm
- Контакт получает final score
- Отмечается как "lead" если score > threshold (e.g., > 50)

### Диаграмма потока

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

User can now:
- Search semantically
- View leads ranked by score
- Take action (contact, notes, etc.)
```

## 5. Semantic Search

### Как это работает

```
User Query: "blockchain developer looking for investment"
    ↓
[Embedding] → Vector representation
    ↓
[pgvector] → Similarity search (HNSW index)
    ↓
[Ranking] → Sort by cosine similarity score
    ↓
Results: Top contacts matching the query
```

### Примеры поиска

| Query | Результаты |
|-------|-----------|
| "AI expert" | Contacts со словами AI, ML, data science, neural |
| "developer" | Contacts из #dev channels, со словами code, github, project |
| "investor" | Contacts со словами fund, investment, capital, portfolio |
| "стартап" | Contacts со словами startup, entrepreneurship, идея |

### Точность поиска

- **Semantic similarity** — поиск по смыслу, не только по ключевым словам
- **Multi-language support** — через мультиязычные embeddings
- **Ranking** — лучшие результаты по relevance score

## 6. Contact Graph

Система может строить граф связей между контактами:

```
Developer (John)
  ├─ Posted in: #crypto_dev
  ├─ Also active in: #ai_projects
  ├─ Mentioned by: @maria_advisor
  ├─ Interested in: Blockchain, AI
  └─ Network score: 85/100
```

### Использование
- Найти "influencers" в сообществе
- Рекомендовать контакты на основе связей
- Анализировать тренды в сообществе

---

**Все эти концепции работают вместе** для создания мощной системы идентификации и ранжирования leads.

**Последнее обновление**: 2026-05-08
