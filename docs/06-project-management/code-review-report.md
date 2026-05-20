# 📊 Код-Ревью Проекта Telegram-Profiler

## 🔍 Обзор проекта

**Telegram Profiler** — это сложная система для профилирования контактов из Telegram с использованием AI/ML технологий. Система обрабатывает миллионы сообщений, использует векторные embeddings, hybrid search и имеет полную инфраструктуру (Docker, Celery, PostgreSQL + pgvector, Redis).

---

## 🎯 Основные Классифицированные Баги и Проблемы

### 🔴 Critical Bugs (Немедленное исправление)

#### 1. Отсутствие Middleware Exception Handler
- **Файл:** `src/api/main.py`
- **Проблема:** Нет глобального exception handler для consistent error responses.
- **Решение:**
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  from fastapi.exceptions import RequestValidationError

  app.add_exception_handler(Exception, handle_exceptions)
  app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True)
  ```

#### 2. Потенциальная SQL Injection в X-Database Header
- **Файл:** `src/db/database.py` (строки 103-104)
- **Проблема:** Несмотря на regex validation, есть возможность edge-case attacks.
- **Решение:** Добавить logging перед проверкой и использовать parameterized queries.
  ```python
  logger.info("validating_x_database", db_name=db_name)
  ```

#### 3. N+1 Query Problem в Search Router
- **Файл:** `src/api/routers/search.py`
- **Проблема:** В функции `_extract_evidence_batch` — отсутствие eager loading для связанных объектов. Это делает отдельные запросы для каждого контакта!
- **Решение:** Добавить `options(sa.orm.joinedload(Message.content))` для избежания lazy loading.

#### 4. Отсутствие Retry Logic в Telegram Connector
- **Файл:** `src/connectors/telegram_connector.py`
- **Проблема:** Нет retry mechanism для transient API failures (timeouts, network issues).
- **Решение:**
  ```python
  from tenacity import retry, stop_after_attempt, wait_exponential

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
  async def fetch_channel_metadata(self, channel_id: str) -> Optional[dict]:
      ...
  ```

---

### 🟡 Major Issues (Высокий приоритет)

#### 5. Плохая типизация в некоторых функциях
- **Файлы:** `src/pipeline/tasks.py`, `src/api/routers/telegram.py`
- **Пример плохой практики:**
  ```python
  async def extract_leads_from_messages(
      contact_id: UUID,
      content: str,
  ) -> ExtractionResult[LeadExtraction]:  # Неверный тип!
      ...
  ```
- **Решение:** Использовать правильные generic типы и `Optional`/`Union` там, где необходимо.

#### 6. Отсутствие Input Validation в Schema Files
- **Файлы:** `src/api/schemas/*.py`
- **Проблема:** Многие модели не имеют `Field(validators=...)` для email format, phone format, etc.
- **Решение:**
  ```python
  from pydantic import EmailStr, field_validator
  import re

  @field_validator('email')
  @classmethod
  def validate_email(cls, v):
      pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
      if not re.match(pattern, v):
          raise ValueError('Invalid email address')
      return v
  ```

#### 7. Hard-coded Magic Numbers и Constants
- **Места:** `search.py` (строка 114), `unified_processor.py`
- **Проблема:**
  ```python
  if distance < 0.52:  # Relaxed threshold: 0.3 was too strict
      ...
  ```
- **Решение:** Вынести в `config.py` как `THRESHOLD_SEMANTIC_RECALL = 0.52`.

#### 8. Отсутствие Database Connection Pooling Validation
- **Файл:** `src/db/database.py`
- **Проблема:** При многопоточном использовании Celery workers возможны race conditions.
- **Решение:** Добавить connection pool monitoring:
  ```python
  async def monitor_pool_health(db_name):
      engine = get_engine(db_name)
      with engine.pool.checked_instrumentation() as stats:
          logger.info("pool_stats", checkedout=stats.checkedout(), checkedin=stats.checkedin())
  ```

#### 9. Memory Leak в Bulk Operations
- **Файл:** `src/db/repository.py`
- **Проблема:** `bulk_save_messages` и `bulk_upsert_contacts` могут накапливать large lists в memory.
- **Решение:** Использовать бачи по 1000 records с asyncpg `executemany`.
  ```python
  async def bulk_save_messages_paginated(self, messages_data):
      BATCH_SIZE = 1000
      for i in range(0, len(messages_data), BATCH_SIZE):
          batch = messages_data[i:i+BATCH_SIZE]
          # process batch...
  ```

#### 10. Отсутствие Transaction Management в API Endpoints
- **Места:** `src/services/*.py`
- **Проблема:** Некоторые write операции не используют explicit transactions.
- **Решение:**
  ```python
  async with get_session() as session:
      try:
          # operations...
          await session.commit()
      except Exception:
          await session.rollback()
          raise
  ```

---

### 🟢 Minor Issues (Средний приоритет)

#### 11. Отсутствие Docstrings в Public API Methods
- **Места:** Множество файлов
- **Решение:**
  ```python
  async def get_contact(self, contact_id: str) -> dict:
      """Retrieve a single contact by UUID.

      Args:
          contact_id: UUID string or hex representation.

      Returns:
          Dict with Contact API response format.

      Raises:
          ValueError: If contact not found or invalid ID format.
      """
  ```

#### 12. Непоследовательное логирование (Inconsistent Logging)
- **Места:** Разные сервисы
- **Проблема:** Смешивание `logger.info()` с `print()` в некоторых местах.
- **Решение:** Использовать `structlog`:
  ```python
  logger = structlog.get_logger()
  logger.debug("processing_message", message_id=message_id)
  ```

#### 13. Отсутствие Unit Tests для Service Layer
- **Директория:** `tests/`
- **Проблема:** Есть только `test_round8_fixes.py`, нет тестов для `ContactService`, `PipelineService` и т.д.
- **Решение:** Добавить unit тесты под `tests/unit/`.

#### 14. Redundant Type Annotations
- **Места:** `src/api/routers/telegram.py`
- **Решение:** Упростить `isinstance(msg_count, int)` проверки, где тип уже гарантирован.

#### 15. Отсутствие API Rate Limiting
- **Файл:** `src/api/main.py`
- **Решение:** Добавить Redis-based rate limiter middleware.

---

## 🛠 Возможности для Рефакторинга

1. **Service Layer Pattern:** Разбить монолитные роутеры (например, `telegram.py`) на отдельные специализированные сервисы:
   - `channel_service.py`
   - `message_service.py`
   - `contact_service.py`
   - `extraction_service.py`
2. **Repository Pattern Улучшение:** Ввести интерфейсы репозиториев для облегчения тестирования (mocking).
3. **DTO/Response Models:** Создать отдельные Pydantic Response models вместо inline dict mapping.

---

## 📊 Архитектурные Улучшения

1. **Event Sourcing / CQRS Pattern:** Для write-heavy операций (sync, embeddings) добавить event bus через Redis Streams.
2. **Circuit Breaker для Telegram API:** Добавить circuit breaker в `src/connectors/telegram_connector.py` для защиты от каскадных сбоев.
3. **pgvector HNSW Index Tuning:** Оптимизировать параметры поиска HNSW (`hnsw.ef_search`) в зависимости от размера базы.

---

## 🎯 Сводная таблица приоритетов

| Приоритет | Количество | Примеры |
|---|---|---|
| 🔴 **Critical** | 4 | Exception handler, SQL injection, N+1, Retry logic |
| 🟡 **Major** | 10 | Type safety, Validation, Magic numbers, Transactions |
| 🟢 **Minor** | 7 | Docs, Logging, Tests, Code style |

---

## ✅ Быстрые победы (Top 5 Fixes)

1. Добавить Exception Middleware в `src/api/main.py`.
2. Перенести magic constants в `config.py`.
3. Улучшить input validation через Pydantic validators.
4. Добавить retry decorator в Telegram connector.
5. Начать писать unit-тесты для service layer.
