# Руководство по управлению документацией

## О документации проекта

Документация Networking Brain организована в структурированном формате для максимальной читаемости и поддерживаемости.

### Структура docs/

```
docs/
├── README.md                          # Главный index
├── DOCUMENTATION_GUIDE.md             # Этот файл
├── 01-introduction/                   # Getting started docs
├── 02-architecture/                   # System design & structure
├── 03-product/                        # Product vision & guidelines  
├── 04-development/                    # Development workflows
│   ├── style-guides/                  # Coding standards
│   └── testing.md                     # Testing requirements
├── 05-features/                       # Feature documentation
├── 06-project-management/             # Tracks & planning
├── 07-patterns/                       # Design patterns & skills
└── 08-advanced/                       # Advanced topics
```

## Когда добавлять документацию

### ✅ ДОЛЖНЫ быть документированы

1. **Архитектурные решения** — пусть это переживет автора
2. **Новые features** — как работает, почему так разработано
3. **API endpoints** — параметры, примеры, error cases
4. **Database schema** — таблицы, relations, indices
5. **Configuration** — окружение переменные, defaults
6. **Processes** — как деплоить, как тестировать, как releasить
7. **Troubleshooting** — common issues и solutions

### ❌ НЕ должны быть документированы

- Очень очевидный код (self-explanatory)
- Временные fixes (создайте issue для proper fix)
- Работа в прогрессе (завершите, потом документируйте)
- Внутренние детали реализации (если не crucial)

## Как добавлять документацию

### 1. Создание нового документа

```bash
# В соответствующей папке
docs/05-features/my-new-feature.md
```

### 2. Структура документа

```markdown
# Feature Name

## Overview
One paragraph describing what this is.

## Key Concepts
- Concept 1: explanation
- Concept 2: explanation

## How It Works
Step-by-step explanation with examples.

## Configuration
Parameters and options.

## Examples
Real usage examples.

## Troubleshooting
Common issues and fixes.

## Related Docs
- [Link](../path)
- [Link](../path)
```

### 3. Обновление главного index

Добавьте ссылку в `docs/README.md`:

```markdown
### [5. Features](./05-features/)
- [Existing Feature 1](./05-features/feature1.md)
- [Existing Feature 2](./05-features/feature2.md)
- [**NEW: My New Feature**](./05-features/my-new-feature.md)  ← Добавьте тут
```

## Style Guide для документации

### Язык
- **Primary**: English (for international audience)
- **Secondary**: Russian (для локальной команды)
- **Mix**: OK если оба присутствуют в документе

### Форматирование

#### Headings
```markdown
# H1 — Page title (только один на странице)
## H2 — Major sections
### H3 — Subsections
#### H4 — Details
```

#### Lists
```markdown
✅ Use bullet points for non-sequential items
1. Use numbered for sequential steps
   - Nested items with 3 spaces
   - Or proper indentation
```

#### Code blocks
```markdown
# For code snippets
​```python
# With language identifier
def hello():
    pass
​```

# For terminal commands
​```bash
pip install requirements
python run.py
​```
```

#### Emphasis
```markdown
**bold** — important terms
*italic* — emphasis
`code` — inline code
[link](url) — internal links
```

### Length Guidelines

| Type | Max Length | Notes |
|------|-----------|-------|
| Title | 50 chars | Descriptive |
| Section | 200 lines | Consider splitting if > 300 |
| Paragraph | 150 words | Keep digestible |
| Code snippet | 30 lines | Link to file if longer |

## Updating Documentation

### When to update
- 🔴 Immediately when API changes
- 🟡 Within sprint when feature changes
- 🟡 Monthly review for outdated content
- 🟢 Can batch small improvements

### Update checklist
- [ ] Content is accurate
- [ ] Links still work
- [ ] Code examples run correctly
- [ ] No typos or grammatical errors
- [ ] Related docs are updated
- [ ] Version numbers are current

### Example update

```bash
# 1. Edit the file
vim docs/02-architecture/tech-stack.md

# 2. Update version/date at bottom
**Last updated**: 2026-05-08

# 3. Commit
git commit -m "docs(arch): Update tech-stack with new LLM provider"
```

## Keeping docs organized

### Linking within docs

```markdown
# Good internal links
- [See Overview](./overview.md)
- [API Documentation](../02-architecture/overview.md)

# Not good
- [See Overview](overview.html)
- File at: /Users/name/telegram-profiler/docs/overview.md
```

### Using cross-references

```markdown
**See also**: 
- [Related Topic](../section/page.md)
- [Configuration Guide](../04-development/config.md)
```

### Deprecation warnings

```markdown
⚠️ **DEPRECATED**: This section is outdated.
Use [New Approach](new-page.md) instead.
```

## Version control for docs

### Commit messages
```
docs(section): Brief description
docs: No section if affecting multiple areas

# Examples
docs(api): Add authentication endpoint
docs(arch): Update database schema diagram
docs: Reorganize documentation structure
```

### Reviews for docs
- At least 1 person reviews before merge
- Check: accuracy, clarity, consistency
- No grammar/spelling errors

## Tools & Automation

### Building documentation
```bash
# Optional: MkDocs for static site
mkdocs serve  # Serve locally at localhost:8000
mkdocs build  # Generate static HTML
```

### Checking links (optional)
```bash
# Check for broken links
pip install markdown-link-check
markdown-link-check docs/**/*.md
```

## Creating new sections

If you need a new major section:

1. Create folder: `docs/0X-section-name/`
2. Create `README.md` as section index
3. Add section to `docs/README.md`
4. Ensure consistent with other sections

### Section template

```markdown
# [Section Name]

Brief description of what this section covers.

## Topics Covered

- [Topic 1](topic1.md)
- [Topic 2](topic2.md)
- [Topic 3](topic3.md)

## Quick Links

- [Getting started](../01-introduction/)
- [Main docs](../README.md)
```

## Common mistakes to avoid

❌ **DON'T**:
- Leave outdated info in docs (delete or mark deprecated)
- Put sensitive data (API keys, passwords)
- Link to external sites that might disappear
- Write future tense ("will be implemented")
- Duplicate content across multiple docs

✅ **DO**:
- Update docs when code changes
- Keep examples up-to-date
- Use consistent formatting
- Link within docs for context
- Use past tense for completed features

## Documentation checklist

Before considering a doc "complete":

- [ ] Title clearly describes content
- [ ] Written for intended audience
- [ ] Code examples are correct and run
- [ ] All links are working
- [ ] Related topics are cross-linked
- [ ] No outdated information
- [ ] Consistent with style guide
- [ ] Reviewed by team member

## Asking for documentation help

If you need to improve docs:

```bash
# Create an issue
# Title: "docs: Improve [section] documentation"
# Description: 
#   - What's missing
#   - What's unclear
#   - Who should document it
#   - Priority (🔴 critical / 🟡 important / 🟢 nice-to-have)
```

## Quick reference

| Need | Where | Who |
|------|-------|-----|
| Getting started | 01-introduction | New users |
| How it's built | 02-architecture | Developers |
| What to build | 03-product | PMs, Design |
| How to build it | 04-development | Developers |
| Using features | 05-features | Users, Devs |
| Managing project | 06-project-management | PMs, Leads |
| Design patterns | 07-patterns | Architects |
| Advanced topics | 08-advanced | Advanced devs |

---

**Хорошая документация — залог успеха проекта.**

**Questions?** Check the related docs or ask in your team's channel.

**Последнее обновление**: 2026-05-08
