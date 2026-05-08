# Python Style Guide

Следуйте этому guide при написании Python кода для Networking Brain.

## 1. Python Language Rules

### Linting
- Запускайте `ruff` или `flake8` на коде:
  ```bash
  ruff check src/
  ```
- Используйте `black` для форматирования:
  ```bash
  black src/
  ```

### Imports
```python
# ✅ Хорошо
import os
import sys
from typing import Optional, List

import numpy as np  # Third-party, separate group
import requests

from src.db import Session  # Local imports, separate group
from src.ai import LLMClient
```

```python
# ❌ Плохо
from os import *  # Never use wildcard imports
import os, sys  # Don't combine imports on one line
import src.db.models  # Too verbose
```

### Exceptions
```python
# ✅ Хорошо
try:
    data = parse_json(msg)
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON: {e}")
    raise ValueError("Message must be valid JSON") from e

# ❌ Плохо
try:
    data = parse_json(msg)
except:  # Bare except — catch all!
    pass  # Silently ignore errors
```

### Global State
```python
# ✅ Хорошо — module-level constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
SUPPORTED_FORMATS = {"json", "csv", "xlsx"}

# ❌ Плохо — mutable global state
config = {}  # Avoid mutable globals
active_sessions = []  # Creates hidden dependencies
```

### Comprehensions
```python
# ✅ Хорошо для простых случаев
emails = [c['email'] for c in contacts if c['email']]

# ❌ Плохо — слишком сложно
results = [
    {**c, 'score': calculate_score(c)}
    for c in contacts
    if is_active(c) and (score := calculate_score(c)) > threshold
]

# Напишите так:
results = []
for contact in contacts:
    if is_active(contact):
        score = calculate_score(contact)
        if score > threshold:
            results.append({**contact, 'score': score})
```

### Default Argument Values
```python
# ✅ Хорошо
def create_contact(name: str, tags: Optional[List[str]] = None):
    if tags is None:
        tags = []
    return Contact(name=name, tags=tags)

# ❌ Плохо — mutable default
def create_contact(name: str, tags: List[str] = []):
    tags.append(name)  # This modifies the default!
    return Contact(name=name, tags=tags)
```

### True/False Evaluations
```python
# ✅ Хорошо
if not contacts:  # Implicit false for empty list
    return None

if value is None:  # Explicit check for None
    return default

# ❌ Плохо
if len(contacts) == 0:  # Too verbose
    return None

if value == None:  # Use 'is' for None
    return default
```

### Type Annotations
**ОБЯЗАТЕЛЬНЫ** для всех public APIs:

```python
# ✅ Хорошо
def extract_contacts(message: str) -> List[Contact]:
    """Extract contacts from a message."""
    ...

def process_batch(
    contacts: List[Contact],
    batch_size: int = 100,
    timeout: Optional[float] = None
) -> Dict[str, Any]:
    """Process contacts in batches."""
    ...

# ❌ Плохо
def extract_contacts(message):
    """Extract contacts."""
    ...
```

## 2. Python Style Rules

### Line Length
**Maximum**: 88 characters (Black standard)

```python
# ✅ Хорошо
response = make_request(
    url=api_url,
    timeout=30,
    headers={"Authorization": f"Bearer {token}"}
)

# ❌ Плохо
response = make_request(url=api_url, timeout=30, headers={"Authorization": f"Bearer {token}"})
```

### Indentation
- **4 spaces** per level
- **NEVER** use tabs

```python
# ✅ Правильно
if condition:
    do_something()
    if nested:
        do_more()

# ❌ Неправильно (tabs)
if condition:
	do_something()  # Tab character
```

### Blank Lines
```python
# ✅ Правильно
import os


class Contact:
    """Contact model."""

    def __init__(self, name: str):
        self.name = name

    def get_email(self) -> Optional[str]:
        """Get email address."""
        return getattr(self, 'email', None)


def process_contact(contact: Contact) -> None:
    """Process a contact."""
    ...
```

### Whitespace
```python
# ✅ Правильно
x = 5
y = x + 2
name = "John"

# ❌ Неправильно
x=5
y=x+2
name ="John"
```

### Docstrings
```python
# ✅ Правильно
def extract_contacts(message: str) -> List[Contact]:
    """
    Extract contacts from a Telegram message.
    
    Uses LLM analysis to identify email addresses, names,
    and phone numbers in the message content.
    
    Args:
        message: Raw message text from Telegram
    
    Returns:
        List of Contact objects found in the message
    
    Raises:
        ValueError: If message is empty or None
        APIError: If LLM API call fails
    
    Example:
        >>> contacts = extract_contacts("Contact john@example.com")
        >>> len(contacts)
        1
    """
    if not message:
        raise ValueError("Message cannot be empty")
    ...

# ❌ Неправильно
def extract_contacts(message):
    # Extract contacts
    return contacts

# ❌ Неправильно (слишком много подробностей)
def extract_contacts(message: str) -> List[Contact]:
    """
    This function extracts contacts from a message.
    It takes a string as input and returns a list.
    The string is the message. The list contains contacts.
    """
```

### Strings
```python
# ✅ Используйте f-strings
name = "John"
email = "john@example.com"
message = f"Contact {name} at {email}"

# ✅ Konsistent с quotes (выберите один стиль)
title = "Contact Information"
description = 'How to reach them'

# ❌ Плохо
message = "Contact " + name + " at " + email
message = f'Contact {name} at {email}'  # Inconsistent quotes
```

### Comments
```python
# ✅ Хорошо — объясняйте ПОЧЕМУ
# We cache results for 1 hour because leads expire quickly
CACHE_TTL = 3600

# ❌ Плохо — не повторяйте код
x = 5  # Set x to 5
result = x + 2  # Add 2 to x
```

### TODO Comments
```python
# TODO(john): Implement email validation
# FIXME(maria): Handle connection timeout properly
```

### Import Formatting
```python
# ✅ Правильно — три группы с пустыми строками
import os
import sys
from typing import Optional

import numpy as np
import requests

from src.db import Session
from src.ai import LLMClient
```

## 3. Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Modules | `snake_case` | `contact_service.py` |
| Functions | `snake_case` | `def extract_contacts()` |
| Variables | `snake_case` | `contact_name`, `last_sync` |
| Classes | `PascalCase` | `class ContactService` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES = 3` |
| Private | `_leading_underscore` | `def _internal_method()` |
| Magic | `__double_leading__` | `__init__`, `__str__` |

### Примеры

```python
# ✅ Правильно
class ContactExtractor:
    DEFAULT_CONFIDENCE = 0.8
    
    def __init__(self):
        self._cache = {}
    
    def extract_from_message(self, message: str) -> List[Contact]:
        """Public method."""
        return self._analyze(message)
    
    def _analyze(self, text: str) -> List[Contact]:
        """Private method."""
        ...

# ❌ Неправильно
class contactExtractor:  # Should be PascalCase
    DEFAULT_confidence = 0.8  # Should be UPPER_SNAKE_CASE
    
    def ExtractFromMessage(self):  # Should be snake_case
        ...
```

## 4. Best Practices

### Async/Await
```python
# ✅ Правильно
async def get_contacts() -> List[Contact]:
    async with Session() as session:
        return await session.query(Contact).all()

# ❌ Неправильно — смешивание sync/async
async def get_contacts():
    contacts = db.query(Contact).all()  # sync call in async
    return contacts
```

### Context Managers
```python
# ✅ Правильно
with open('data.json') as f:
    data = json.load(f)  # File automatically closed

# ❌ Неправильно
f = open('data.json')
data = json.load(f)
f.close()  # Может не закрыться если ошибка
```

### Pydantic Models
```python
# ✅ Правильно
from pydantic import BaseModel, EmailStr

class ContactSchema(BaseModel):
    name: str
    email: EmailStr
    score: float
    
    class Config:
        str_strip_whitespace = True

# ❌ Неправильно
class ContactSchema:
    def __init__(self, name, email, score):
        self.name = name
        self.email = email
        self.score = score
```

## 5. Testing

```python
# ✅ Правильно
import pytest
from unittest.mock import Mock, patch

def test_extract_contacts_with_email():
    """Test extracting email from message."""
    message = "Contact me at john@example.com"
    contacts = extract_contacts(message)
    
    assert len(contacts) == 1
    assert contacts[0].email == "john@example.com"

@pytest.mark.asyncio
async def test_async_get_contacts():
    """Test async contact retrieval."""
    with patch('src.db.Session') as mock_session:
        mock_session.query.return_value.all.return_value = [...]
        contacts = await get_contacts()
        assert len(contacts) > 0

# ❌ Неправильно
def test_contacts():
    """Test."""
    x = extract_contacts("Contact john@example.com")
    print(x)  # Don't use print, use assertions
    assert x  # Too vague
```

## Tool Configuration

### pyproject.toml
```toml
[tool.black]
line-length = 88
target-version = ["py312"]

[tool.ruff]
line-length = 88
target-version = "py312"
select = ["E", "F", "W"]

[tool.mypy]
python_version = "3.12"
strict = true
```

### .flake8
```ini
[flake8]
max-line-length = 88
ignore = E203, E266, E501, W503
```

---

**BE CONSISTENT.** Когда редактируете чужой код, следуйте его стилю.

**Последнее обновление**: 2026-05-08  
**Источник**: [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
