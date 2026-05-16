# Требования к тестированию

## Философия тестирования

Тесты — это живая документация проекта. Каждый тест описывает одно конкретное поведение.

### Принципы
1. **Изоляция** — каждый тест откатывает изменения в БД через `await session.rollback()`
2. **Детерминированность** — никаких случайных данных; фиксированные входные данные → предсказуемый результат
3. **Реальные зависимости** — unit-тесты мокируют только внешние вызовы (OpenAI, Telegram); в integration-тестах используется реальная PostgreSQL
4. **Актуальность** — при удалении или переименовании модуля тест удаляется/переписывается

---

## Уровни тестирования

### 1. Unit Tests (`tests/`)
Тестируют отдельные функции в изоляции. Внешние I/O мокируются.

```python
# tests/test_ai_logic.py
from src.ai.analysis import cosine_similarity

def test_cosine_similarity_identical_vectors():
    v = [1.0, 0.5, -0.3]
    assert cosine_similarity(v, v) == pytest.approx(1.0)

def test_cosine_similarity_orthogonal():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
```

```python
# tests/test_ai_logic.py — мок OpenAI
from src.ai.analysis import generate_embedding

@pytest.mark.asyncio
async def test_generate_embedding_calls_api():
    fake_vec = [0.1] * 768
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=fake_vec)]

    mock_client = AsyncMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    with patch("src.ai.analysis.AsyncOpenAI", return_value=mock_client):
        result = await generate_embedding("hello")

    assert result == fake_vec
```

### 2. Integration Tests (`tests/integration/`)
Используют реальный PostgreSQL. Данные откатываются после каждого теста.

```python
# tests/integration/test_extraction_pipeline.py
from src.pipeline.unified_processor import MessageProcessor
from src.db.models import Message, Contact, ExtractionLog
from src.ai.schemas import LeadExtraction

@pytest.mark.asyncio
async def test_message_processing_pipeline(db_session):
    contact = Contact(first_name="Ghost", telegram_username="ghost_user")
    db_session.add(contact)
    await db_session.flush()

    msg = Message(
        content="Looking for a flat in Belgrade. Contact oleg@example.com",
        source="telegram",
        group_name="Belgrade RE",
        raw_json={"is_channel": True},
        contact_id=contact.id,
    )
    db_session.add(msg)
    await db_session.commit()

    processor = MessageProcessor(db_session)

    mock_lead = LeadExtraction(
        username="ghost_user",
        content_summary="Wants a flat",
        category="RealEstate",
        lead_type="Consumer",          # обязательное поле
        evidence_quote="Looking for a flat",
        confidence=0.85,
    )

    with patch.object(processor.ai_service, "extract", AsyncMock(side_effect=[
        ([], "usage"),
        ([mock_lead], "usage"),
    ])):
        stats = await processor.process_batch([msg])

    assert stats["processed"] == 1
    assert stats["leads_found"] == 1
```

### 3. API Tests (`tests/`)
Используют `api_client` fixture (httpx.AsyncClient поверх ASGI).

```python
# tests/test_api_leads.py
@pytest.mark.asyncio
async def test_list_leads_pagination(api_client, db_session):
    # создаём тестовые данные
    for i in range(15):
        db_session.add(Contact(
            first_name=f"Lead {i}",
            is_lead=True,
            lead_score=100.0 + i,
            source="__api_test__",
        ))
    await db_session.commit()

    response = await api_client.get("/api/leads/top?page=1&page_size=10&min_score=100")
    assert response.status_code == 200
    data = response.json()
    assert len(data["contacts"]) == 10
    assert data["total"] == 15
```

---

## Fixtures (conftest.py)

| Fixture | Scope | Описание |
|---------|-------|---------|
| `setup_test_db` | `session` | Создаёт БД `crm_test`, применяет схему один раз на весь прогон |
| `db_session` | `function` | Async-сессия; откатывает изменения после каждого теста |
| `api_client` | `function` | `httpx.AsyncClient` поверх FastAPI ASGI без TCP-сокета |

```python
# conftest.py (ключевые части)
@pytest_asyncio.fixture
async def api_client(setup_test_db):
    from httpx import AsyncClient, ASGITransport
    from src.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
```

---

## Запуск тестов

```bash
# Все тесты
pytest tests/ -x -q

# С покрытием
pytest tests/ --cov=src --cov-report=term-missing

# Только unit-тесты (быстро, без реального Postgres)
pytest tests/ --ignore=tests/integration -x -q

# Только integration
pytest tests/integration/ -x -q

# Конкретный файл
pytest tests/test_ai_logic.py -v
```

### Переменные окружения для тестов
Тесты читают `.env` через `src.core.config.get_settings()`.
Минимальный набор для локального прогона:

```bash
POSTGRES_HOST=localhost
POSTGRES_USER=crm
POSTGRES_PASSWORD=...
POSTGRES_DB=crm
REDIS_URL=redis://localhost:6379/0
GOOGLE_API_KEY=...   # или используйте EMBED_PROVIDER=lmstudio
```

---

## Мокирование

```python
# ✅ Мок конкретного метода — предпочтительно
with patch.object(service, "send_message", AsyncMock(return_value=True)):
    result = await service.run_campaign(campaign_id)

# ✅ Мок модульного символа — когда патчить нужно в месте использования
with patch("src.ai.analysis.AsyncOpenAI", return_value=mock_client):
    vec = await generate_embedding("text")

# ❌ Не мокируйте src.db.database.get_session в unit-тестах — используйте db_session fixture
```

---

## Схема ai.schemas (обязательные поля)

```python
class LeadExtraction(BaseExtraction):
    username: str           # обязательно
    content_summary: str    # обязательно
    category: str           # обязательно
    lead_type: str          # обязательно
    evidence_quote: str     # обязательно
    lead_quality: int = 5   # опционально (default = 5)
    confidence: float = 0.0 # опционально
    display_name: Optional[str] = None
```

---

## CI/CD

```yaml
# .github/workflows/tests.yml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: ankane/pgvector:latest
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: crm_test
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -r requirements.txt pytest pytest-asyncio httpx sqlalchemy_utils
      - run: pytest tests/ -x -q --cov=src --cov-report=term
```

---

**Последнее обновление**: 2026-05-16
