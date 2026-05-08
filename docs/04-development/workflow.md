# Рабочий процесс разработки

## Руководящие принципы

1. **План — источник истины** — все работы должны отслеживаться в `plan.md` (в conductor/)
2. **Технологический стек — сознательный выбор** — изменения в tech stack должны быть документированы в `tech-stack.md` *перед* реализацией
3. **Test-Driven Development** — напишите unit тесты перед реализацией функциональности
4. **Высокое покрытие тестами** — стремитесь к >80% code coverage для всех модулей
5. **UX First** — каждое решение должно приоритизировать user experience
6. **Non-Interactive & CI-Aware** — используйте non-interactive команды; `CI=true` для watch-mode tools

## Workflow для задач

### 1️⃣ Выбор задачи
- Откройте `conductor/tracks.md` или соответствующий track plan
- Выберите следующую доступную задачу в последовательном порядке
- Убедитесь, что это [task-based planning, а не issue-driven]

### 2️⃣ Отметьте "In Progress"
Перед началом работы, отредактируйте план и измените статус задачи:
```markdown
- [ ] Task Name (не начата)
- [~] Task Name (in progress)
- [x] Task Name (завершена)
```

### 3️⃣ Напишите failinng тесты (Red Phase)
**Это обязательно перед написанием кода!**

```python
# tests/unit/test_contact_extraction.py
import pytest
from src.ai.extractors import extract_contacts

def test_extract_email_from_message():
    """Должны извлечь email из сообщения"""
    message = "Contact me at john@example.com for details"
    
    contacts = extract_contacts(message)
    
    assert len(contacts) == 1
    assert contacts[0]['email'] == 'john@example.com'

def test_extract_multiple_contacts():
    """Должны извлечь несколько контактов"""
    message = """
    Contact our CEO John (john@crypto.com) or 
    VP of Sales Maria (maria.smith@crypto.com)
    """
    
    contacts = extract_contacts(message)
    
    assert len(contacts) == 2
    assert 'john@crypto.com' in [c['email'] for c in contacts]
```

**Запустите и убедитесь, что они failают:**
```bash
pytest tests/unit/test_contact_extraction.py -v
# Результат: FAILED (как и ожидается)
```

### 4️⃣ Реализуйте функциональность (Green Phase)
Напишите минимальный код для прохождения тестов:

```python
# src/ai/extractors.py
import re

def extract_contacts(message: str) -> list[dict]:
    """Извлекает контакты из сообщения"""
    contacts = []
    
    # Простой regex для email
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
    for email in emails:
        contacts.append({'email': email})
    
    return contacts
```

**Запустите тесты:**
```bash
pytest tests/unit/test_contact_extraction.py -v
# Результат: PASSED ✓
```

### 5️⃣ Рефакторинг (опционально)
С безопасностью прошедших тестов, улучшите код:

```python
# Улучшение: более точный regex, обработка ошибок
import re
from typing import Optional

EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

def extract_contacts(message: str) -> list[dict]:
    """Извлекает контакты из сообщения с улучшенной валидацией"""
    if not isinstance(message, str) or not message.strip():
        return []
    
    contacts = []
    emails = re.findall(EMAIL_PATTERN, message)
    
    for email in set(emails):  # Remove duplicates
        if is_valid_email(email):
            contacts.append({'email': email, 'type': 'email'})
    
    return contacts

def is_valid_email(email: str) -> bool:
    """Базовая валидация email"""
    return len(email) < 254 and email.count('@') == 1
```

**Снова запустите тесты** чтобы убедиться, что рефакторинг не сломал функциональность:
```bash
pytest tests/unit/test_contact_extraction.py -v
# Результат: PASSED ✓
```

### 6️⃣ Проверьте покрытие (Coverage)
Убедитесь, что новый код покрыт тестами:

```bash
pytest --cov=src/ai/extractors --cov-report=html

# Результат: Coverage 92% ✓
```

**Target**: > 80% покрытие для нового кода

### 7️⃣ Документируйте отклонения
Если реализация отличается от планов:

1. **STOP** разработку
2. **Update** `conductor/tech-stack.md` с новым дизайном
3. **Add** dated note объясняющую изменение:
   ```markdown
   **Note (2026-05-08)**: Использовали asyncio вместо ThreadPoolExecutor
   для улучшения производительности в I/O-bound tasks. Benchmarks показали
   2x speedup.
   ```
4. **Resume** реализацию

### 8️⃣ Commit изменений кода
Подготовьте и закоммитьте все changes к задаче:

```bash
git status
# Проверить, что изменены правильные файлы

git add src/ai/extractors.py tests/unit/test_contact_extraction.py

git commit -m "feat(ai): Implement contact extraction from messages

- Extract email addresses using regex
- Validate emails before storing
- Add 15 unit tests with 92% coverage"
```

**Правила commit message**:
- `feat:` для новой функциональности
- `fix:` для bug fixes
- `refactor:` для улучшений кода
- `test:` для тестов
- `docs:` для документации
- Первая строка < 50 символов
- Body объясняет *WHY*, не *WHAT*

### 9️⃣ Добавьте Git Notes (опционально для важных tasks)
Для больших features, добавьте detailed summary через git notes:

```bash
# Получите commit hash
git log -1 --format="%H"  # abc123def456...

# Добавьте note
git notes add -m "
TASK: Implement contact extraction
COMPLETED: 2026-05-08

Summary of changes:
- Added email extraction with regex
- Added email validation logic
- Created 15 unit tests
- Achieved 92% code coverage

Key files:
- src/ai/extractors.py (new)
- tests/unit/test_contact_extraction.py (new)

Why: Automated extraction saves manual entry time,
critical for scaling the system to process thousands
of messages per day.
" abc123def456...
```

### 🔟 Обновите план
1. **Откройте** план (conductor/tracks/*/plan.md)
2. **Найдите** строку с вашей задачей
3. **Обновите** статус с `[~]` на `[x]`
4. **Добавьте** первые 7 символов commit hash:
   ```markdown
   - [x] Implement contact extraction (abc123d)
   ```
5. **Сохраните** файл

### 1️⃣1️⃣ Закоммитьте обновление плана

```bash
git add conductor/tracks/*/plan.md
git commit -m "conductor(plan): Mark 'Implement contact extraction' as complete"
```

## Phase Completion Verification

Когда **вся фаза завершена**:

### 1. Запустите все тесты

```bash
# Объявите команду, которую запустите
echo "Running full test suite with: pytest tests/ --cov=src"

# Выполните
pytest tests/ --cov=src --cov-report=term-missing

# Результат должен быть: PASSED с >80% coverage
```

### 2. Проверьте code quality

```bash
# Lint
flake8 src/ tests/

# Format check
black --check src/ tests/

# Type checking
mypy src/ --strict
```

### 3. Проверьте против product goals
Открыйте `conductor/product.md` и убедитесь:
- [ ] Все success metrics выполнены для этой фазы
- [ ] UX/UI соответствует guidelines
- [ ] Performance targets достигнуты
- [ ] Accessibility требования удовлетворены

### 4. Создайте checkpoint

```markdown
# Phase Checkpoint: Lead Extraction (2026-05-08)

**Status**: ✅ Complete

**Tests**: 47 passed, 0 failed (98% coverage)

**Key commits**:
- abc123d feat(ai): Implement contact extraction
- def456e test(ai): Add comprehensive extraction tests
- ghi789f docs(ai): Document extraction algorithm

**Verification**:
- [x] All tests pass
- [x] Code coverage > 80%
- [x] Style guide compliance
- [x] Manual testing complete
- [x] Performance targets met

**Next phase**: Lead Scoring Algorithm
```

Сохраните в `conductor/CHECKPOINTS.md`

## Troubleshooting

### Тесты failают
1. Прочитайте error message внимательно
2. Проверьте, что dependencies установлены
3. Запустите с verbose: `pytest -v`
4. Проверьте environment variables в .env

### Код не работает locально, но работает в CI
1. Проверьте Python версию: `python --version`
2. Проверьте зависимости: `pip install -r requirements.txt`
3. Удалите __pycache__: `find . -type d -name __pycache__ -exec rm -rf {} +`
4. Очистите тестовую БД: `pytest --reset-db`

### Performance проблемы
1. Профилируйте код: `python -m cProfile -s cumtime script.py`
2. Проверьте database indexes
3. Добавьте caching где нужно
4. Обновите tech-stack.md с бенчмарками

## Git Workflow

### Feature branch
```bash
# Создайте branch от main
git checkout -b feat/contact-extraction

# Делайте commits
git commit -m "..."

# Когда готово, создайте PR
# GitHub Actions автоматически запустит тесты
```

### Merging
```bash
# После review и approval от 2 teammates
git checkout main
git pull origin main
git merge --squash feat/contact-extraction
git commit -m "Merge feature: Contact extraction"
```

## Code Review Checklist

Перед merge-ом убедитесь:

- [ ] Tests pass (CI ✓)
- [ ] Code coverage maintained (>80%)
- [ ] No merge conflicts
- [ ] Matches style guide
- [ ] No hardcoded values
- [ ] Proper error handling
- [ ] Database migrations tested
- [ ] Documentation updated

---

**Этот workflow максимизирует quality и трaceability разработки.**

**Последнее обновление**: 2026-05-08
