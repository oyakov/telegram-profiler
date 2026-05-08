# Требования к тестированию

## Философия тестирования

**Test-Driven Development** — напишите тесты ДО кода, это обязательно для всех features.

### Преимущества TDD
1. **Ясные требования** — тесты документируют, что должно работать
2. **Меньше bugs** — проблемы выявляются рано
3. **Refactoring confidence** — можно менять код без страха
4. **Living documentation** — тесты показывают как использовать API

## Уровни тестирования

### 1. Unit Tests (45-50% покрытия)
Тестируют отдельные функции/методы в изоляции.

```python
# tests/unit/test_contact_extraction.py
import pytest
from src.ai.extractors import extract_contacts

def test_extract_email():
    """Should extract email from message."""
    message = "Contact john@example.com"
    contacts = extract_contacts(message)
    
    assert len(contacts) == 1
    assert contacts[0]['email'] == 'john@example.com'

def test_no_contacts_in_empty_message():
    """Should return empty list for empty message."""
    assert extract_contacts("") == []
    assert extract_contacts(None) == []

def test_extract_multiple_emails():
    """Should extract multiple email addresses."""
    message = "john@example.com or mary@test.com"
    contacts = extract_contacts(message)
    
    assert len(contacts) == 2
```

### 2. Integration Tests (30-35% покрытия)
Тестируют взаимодействие нескольких компонентов.

```python
# tests/integration/test_contact_pipeline.py
import pytest
from src.pipeline import ContactPipeline
from src.db import Contact

@pytest.fixture
async def pipeline(db_session):
    return ContactPipeline(db=db_session)

@pytest.mark.asyncio
async def test_extract_and_save_contact(pipeline):
    """Should extract contact and save to database."""
    message = "Contact john@example.com"
    
    contact = await pipeline.process(message)
    
    assert contact.email == "john@example.com"
    
    # Verify saved to DB
    saved = await db_session.get(Contact, contact.id)
    assert saved is not None
```

### 3. End-to-End Tests (15-20% покрытия)
Тестируют полный workflow пользователя.

```python
# tests/e2e/test_user_flow.py
@pytest.mark.asyncio
async def test_user_searches_and_finds_contact(client):
    """User should be able to search and find contact."""
    # 1. Upload message
    response = await client.post("/api/messages", json={
        "content": "Contact john@example.com",
        "channel_id": 123
    })
    assert response.status_code == 200
    
    # 2. Search for contact
    response = await client.get("/api/search?q=john")
    assert response.status_code == 200
    
    results = response.json()
    assert len(results) == 1
    assert results[0]['email'] == 'john@example.com'
```

## Coverage Requirements

| Component | Minimum | Target |
|-----------|---------|--------|
| Core logic | 80% | 90% |
| API endpoints | 75% | 85% |
| Database models | 70% | 80% |
| Utils | 60% | 75% |
| Overall | 75% | 85% |

### Проверка покрытия

```bash
# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Show uncovered lines
pytest --cov=src --cov-report=term-missing
```

## Test Structure

### Naming Convention
```
tests/
├── unit/               # Unit tests
│   ├── test_extractors.py
│   ├── test_scorers.py
│   └── ...
├── integration/        # Integration tests
│   ├── test_pipeline.py
│   ├── test_api.py
│   └── ...
├── e2e/               # End-to-end tests
│   └── test_user_flows.py
└── conftest.py        # Shared fixtures
```

### Test Function Naming
```python
# ✅ Good
def test_extract_email_from_message():
def test_returns_empty_list_for_empty_message():
def test_deduplicates_multiple_emails():

# ❌ Bad
def test_extract():
def test_func():
def test_1():
```

## Using Fixtures

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    """Provide test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with AsyncSession(engine) as session:
        yield session
        await session.close()

@pytest.fixture
async def mock_llm():
    """Provide mock LLM for testing."""
    from unittest.mock import Mock
    mock = Mock()
    mock.analyze.return_value = {"email": "john@example.com"}
    return mock

# In test files
def test_with_fixture(db_session, mock_llm):
    """Test using fixtures."""
    ...
```

## Mocking Best Practices

```python
from unittest.mock import Mock, patch, AsyncMock

# ✅ Хорошо — мок конкретный сервис
@patch('src.ai.LLMClient.analyze')
def test_extract_uses_llm(mock_analyze):
    mock_analyze.return_value = {"email": "test@example.com"}
    
    result = extract_contacts("message")
    
    assert result[0]['email'] == "test@example.com"
    mock_analyze.assert_called_once()

# ✅ Хорошо — используйте AsyncMock для async функций
@patch('src.db.Session.query')
async def test_async_query(mock_query):
    mock_query.return_value = AsyncMock(return_value=[...])
    
    contacts = await get_contacts()
    
    assert len(contacts) > 0

# ❌ Плохо — не мокируйте весь модуль
@patch('src')  # Too broad!
def test_something(mock_src):
    ...
```

## Test Data & Factories

```python
# tests/factories.py
from factory import Factory
from src.db.models import Contact

class ContactFactory(Factory):
    """Factory for creating test Contact objects."""
    
    class Meta:
        model = Contact
    
    name = "John Developer"
    email = "john@example.com"
    score = 85.0

# In tests
def test_contact_scoring(db_session):
    contact = ContactFactory.create(score=90)
    assert contact.score == 90
```

## Async Testing

```python
# Using pytest-asyncio
import pytest

@pytest.mark.asyncio
async def test_async_extraction():
    """Test async function."""
    result = await extract_contacts_async("message")
    assert result is not None

# Using fixture
@pytest.fixture
def event_loop():
    """Create event loop for tests."""
    import asyncio
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()
```

## Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("message,expected_count", [
    ("john@example.com", 1),
    ("john@example.com and mary@test.com", 2),
    ("no emails here", 0),
    ("", 0),
])
def test_extract_emails(message, expected_count):
    """Test with different inputs."""
    result = extract_contacts(message)
    assert len(result) == expected_count
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - run: pip install -r requirements.txt
      - run: pip install -r tests/requirements.txt
      
      - run: pytest tests/ --cov=src
      - run: coverage report --fail-under=75
```

## Test Maintenance

### Updating Tests
- ❌ Не обновляйте тесты для "исправления" failures
- ✅ Обновляйте тесты если requirements изменились
- ✅ Добавляйте новые тесты для новых features
- ✅ Удаляйте тесты для удаленной функциональности

### Flaky Tests
Тесты, которые sometimes pass/fail:

```python
# ❌ Плохо — недетерминированно
def test_sometimes_fails():
    import random
    assert random.random() > 0.5

# ✅ Хорошо — используйте фиксированные данные
def test_deterministic():
    assert calculate_score(contact) == 85.0
```

## Documentation in Tests

```python
def test_extract_contacts():
    """
    Test the complete contact extraction flow.
    
    This test verifies that:
    1. Email addresses are correctly identified
    2. Duplicates are removed
    3. Confidence scores are assigned
    
    Arrangement: A message with multiple emails
    Action: Call extract_contacts()
    Assert: Correct contacts returned with proper metadata
    """
    # Arrange
    message = "Contact john@example.com or mary@test.com"
    
    # Act
    contacts = extract_contacts(message)
    
    # Assert
    assert len(contacts) == 2
    assert contacts[0]['email'] in ['john@example.com', 'mary@test.com']
```

---

**Тестирование — это инвестиция в качество и скорость разработки.**

**Последнее обновление**: 2026-05-08
