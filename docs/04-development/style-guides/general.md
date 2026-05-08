# General Code Style Principles

Эти принципы применяются ко всем языкам и фреймворкам, используемым в Networking Brain.

## Читаемость (Readability)

Код должен быть легко читаемым и понимаемым людьми.

### Правила
- 🚫 Избегайте чрезмерно clever или obscure конструкций
- ✅ Используйте descriptive имена
- ✅ Максимум 3-4 уровня вложенности
- ✅ Разбивайте сложные функции на smaller functions
- ✅ Комментируйте non-obvious решения

### Плохо ❌
```python
# Слишком clever
result = [y for x in [1,2,3] if (y:=x*2) > 2]
```

### Хорошо ✅
```python
# Ясный intent
doubled = [x * 2 for x in numbers]
significant = [x for x in doubled if x > 2]
```

## Консистентность (Consistency)

Следуйте существующим паттернам в codebase.

### Правила
- 📋 Изучите существующий код перед написанием своего
- 🎯 Используйте одинаковые паттерны для похожих задач
- 🔤 Консистентное форматирование (spaces, quotes, line length)
- 📁 Консистентная структура файлов и директорий

### Пример
```python
# Если в проекте используется dataclass, используйте везде
from dataclasses import dataclass

@dataclass
class Contact:
    name: str
    email: str
    score: float
```

## Простота (Simplicity)

Предпочитайте простые решения сложным.

### KISS Принцип (Keep It Simple, Stupid)

```python
# Плохо - overengineering
class ContactFactory:
    def __init__(self, strategy_registry):
        self.registry = strategy_registry
    
    def create(self, type_name):
        strategy = self.registry.get(type_name)
        return strategy.create()

# Хорошо - просто и понятно
def create_contact(name: str, email: str) -> Contact:
    return Contact(name=name, email=email)
```

### Правила
- Напишите минимальный код, чтобы решить задачу
- Добавляйте abstraction'ы, только когда они действительно нужны
- 3 похожих строки кода — OK, 4+ строк → рассмотрите refactoring
- Не оптимизируйте "в соответствии с будущими требованиями"

## Поддерживаемость (Maintainability)

Пишите код, который легко изменять и расширять.

### Правила
- ✅ Функции должны делать одно
- ✅ Минимизируйте dependencies и coupling
- ✅ Используйте dependency injection
- ✅ Избегайте side effects
- ✅ Используйте testing для refactoring safety

### Пример

```python
# Плохо - high coupling, hard to test
class ContactService:
    def __init__(self):
        self.db = PostgreSQL()  # Creates its own DB
        self.llm = GeminiAPI()  # Creates its own LLM
    
    def extract_contact(self, message):
        result = self.llm.analyze(message)
        self.db.save(result)
        return result

# Хорошо - dependency injection, easy to test
class ContactService:
    def __init__(self, db: Database, llm: LLMClient):
        self.db = db
        self.llm = llm
    
    def extract_contact(self, message: str) -> Contact:
        contact = self.llm.analyze(message)
        self.db.save(contact)
        return contact

# In tests, you can pass mock dependencies
service = ContactService(MockDB(), MockLLM())
```

## Документация (Documentation)

Документируйте **ЧТО и ПОЧЕМУ**, не только **ЧТО**.

### Правила

- 📝 Каждый public модуль, класс, функция должны иметь docstring
- 🤔 Объясняйте **почему** решение выбрано (если не очевидно)
- 🔗 Ссылайтесь на related docs/issues где нужно
- 🚫 Не повторяйте код в комментариях
- ✅ Обновляйте docs когда обновляете код

### Плохо ❌
```python
def process_message(msg):
    # Process the message
    return msg.upper()
```

### Хорошо ✅
```python
def process_message(msg: str) -> str:
    """
    Normalize message text for consistent processing.
    
    Converts to uppercase to ensure uniform handling
    across different input cases.
    
    Args:
        msg: Raw message string from Telegram
    
    Returns:
        Normalized message ready for LLM analysis
    """
    return msg.upper()
```

## DRY (Don't Repeat Yourself)

Избегайте дублирования кода.

### Правила
- 1-2 occurrence: OK, может быть совпадение
- 3 occurrences: Пора создать helper function/util
- 4+ occurrences: Срочно рефакторьте

### Пример
```python
# Плохо - дублирование
def get_active_contacts():
    return db.query(Contact).filter(Contact.active == True).all()

def get_premium_contacts():
    return db.query(Contact).filter(Contact.premium == True).all()

def get_recent_contacts():
    return db.query(Contact).filter(Contact.updated_at > date.today()).all()

# Хорошо - переиспользование
def get_contacts(filter_func=None):
    query = db.query(Contact)
    if filter_func:
        query = query.filter(filter_func())
    return query.all()

# Usage
active = get_contacts(lambda: Contact.active == True)
premium = get_contacts(lambda: Contact.premium == True)
```

## Error Handling

Правильная обработка ошибок.

### Правила
- ✅ Ловите specific исключения
- 🚫 Не ловите все (bare `except:`)
- 📝 Логируйте errors для debugging
- 🔄 Graceful degradation где возможно
- ❌ Не скрывайте ошибки

### Пример
```python
# Плохо
try:
    result = risky_operation()
except:
    return None

# Хорошо
try:
    result = risky_operation()
except DatabaseError as e:
    logger.error(f"Database error: {e}", exc_info=True)
    raise  # Re-raise for caller to handle
except ValidationError as e:
    logger.warning(f"Invalid data: {e}")
    return None  # Graceful fallback for validation
```

## Performance

Пишите efficient код, но не за счет readability.

### Правила
- ✅ Profилируйте перед оптимизацией
- 📊 Измеряйте impact optimization'ов
- 🚫 Не оптимизируйте micro-optimizations без причины
- 🔍 Ищите bottlenecks через profiling tools
- 💾 Используйте caching для дорогостоящих операций

### Пример
```python
# Плохо - premature optimization, less readable
contacts = {(c['name'], c['email']): c for c in all_contacts}

# Хорошо - clear intent, good performance for reasonable dataset
contact_lookup = create_contact_index(all_contacts)
def create_contact_index(contacts):
    return {(c['name'], c['email']): c for c in contacts}
```

## Security

Безопасность первична.

### Правила
- 🔒 Никогда не hardcode secrets
- 🔐 Валидируйте user input
- 🛡️ Используйте parameterized queries (no SQL injection)
- 🔑 Не логируйте sensitive информацию
- ✅ Регулярно обновляйте dependencies

---

**Примечание**: Когда в сомнениях — выбирайте **readability**. Код читается 100 раз, пишется 1 раз.

**Последнее обновление**: 2026-05-08
