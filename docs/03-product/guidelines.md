# Руководство по продукту

## Философия дизайна

Networking Brain следует этим принципам при разработке features:

### 1. User Experience First
- Каждое решение должно приоритизировать UX пользователя
- Сложность скрывается "под капотом", UI остается простым
- Для повторяющихся задач автоматизация > ручной ввод

### 2. Data-Driven
- Все решения основаны на метриках и данных
- Изменения в product должны проверяться A/B тестами
- Все assumption'ы должны быть подтверждены пользователями

### 3. Gradual Complexity
- Start simple, add features based on demand
- MVP with 3-4 core features лучше, чем сложный продукт
- Advanced features доступны для power users

### 4. Telegram-Native
- Интеграция с Telegram должна быть seamless
- Не заставляем пользователей менять workflow
- API Telegram используется "как есть"

## Приоритизация функций

### Матрица Impact vs Effort

```
┌─────────────────────────────────────────┐
│ High Impact, Low Effort (DO FIRST)      │
│ • Semantic search                       │
│ • Export contacts                       │
│ • Basic filtering & sorting             │
├─────────────────────────────────────────┤
│ High Impact, High Effort (PLAN)         │
│ • Multi-database support                │
│ • AI-generated summaries                │
│ • Advanced analytics                    │
├─────────────────────────────────────────┤
│ Low Impact, Low Effort (DO IF TIME)     │
│ • Dark mode                             │
│ • Custom color schemes                  │
│ • Keyboard shortcuts                    │
├─────────────────────────────────────────┤
│ Low Impact, High Effort (SKIP)          │
│ • Fancy animations                      │
│ • Multiple themes                       │
│ • Calendar integration (for now)        │
└─────────────────────────────────────────┘
```

## Design Patterns

### 1. Progressive Disclosure
Скрывать сложные параметры по умолчанию, показывать "Advanced" секцию для power users.

```
[Contact Card - Simple View]
├─ Name, email, phone
├─ Score badge
├─ [Show more details] button
└─ Quick actions (message, note)

[Contact Card - Expanded]
├─ All fields above +
├─ Activity history
├─ Network analysis
├─ Conversation history
└─ AI insights
```

### 2. Immediate Feedback
- Actions должны мгновенно показать результат
- Loading states вместо зависания UI
- Toast notifications для успешных действий
- Clear error messages

### 3. Contextual Actions
- Правая кнопка мыши → context меню с relevant actions
- Bulk actions для нескольких контактов
- Keyboard shortcuts для power users

## Navigation Hierarchy

```
Dashboard (Обзор)
├─ Recent leads
├─ Activity summary
└─ Quick stats

Contacts (Контакты)
├─ Search/Filter
├─ View options (List/Grid/Kanban)
├─ Bulk actions
└─ Contact detail modal

Search (Семантический поиск)
├─ Query input
├─ Filters sidebar
├─ Results grid
└─ View contact

Settings
├─ Account
├─ Folders & Channels
├─ AI Models
├─ Data Management
└─ Integrations (future)

Audit (Аудит)
├─ Activity log
├─ Change history
└─ Export options
```

## Interaction Patterns

### Search Flow

```
1. User enters natural language query
   "blockchain developers in crypto"
   
2. System:
   - Generates embedding
   - Queries pgvector
   - Returns ranked results
   
3. Results show:
   - Contact name, score
   - Match highlight (why it matched)
   - Quick actions
   
4. User can:
   - Click to view full contact
   - Add note / tag
   - Schedule follow-up
```

### Lead Qualification Flow

```
1. New lead appears in dashboard
2. System shows:
   - Raw score + breakdown
   - Why it's relevant
   - Suggested action
   
3. User can:
   - Accept (mark as "lead")
   - Reject (mark as "spam")
   - Postpone (review later)
   
4. Feedback improves scoring for future leads
```

## Color Coding

### Lead Score Badge

```
90-100: 🔴 Red         (Urgent)
70-89:  🟠 Orange      (High Priority)
50-69:  🟡 Yellow      (Medium)
30-49:  🟢 Green       (Low)
1-29:   ⚪ Gray        (Review)
```

### Status Indicators

```
🟢 Active        (Recently seen)
🟡 Moderate      (Seen this month)
⚪ Inactive      (No recent activity)
🔴 Do Not Contact (Explicitly rejected)
```

## Form Design

### Principles
- Minimal fields (required only)
- Clear labels и placeholders
- Inline validation
- Helpful errors

### Example: Add Channel Form

```
[Add Channel to Folder]

Folder: [Dropdown: Crypto] *
Channel: [Text input: @channel_name] *
         (Auto-complete from Telegram)

Auto-join: [Toggle: ON/OFF]
Mute: [Toggle: ON]
Archive: [Toggle: OFF]

[Cancel] [Create Channel]
```

## Data Display

### Contacts List View

```
┌─────────────────────────────────────────┐
│ Search [          ] | Filters | Sort: Score ▼
├─────────────────────────────────────────┤
│ John Developer        Score: 85 ⭐⭐⭐⭐ │
│ john@blockchain.com   Last seen: 2 days ago  │
│ Tags: AI, Investor                           │
├─────────────────────────────────────────┤
│ Maria Advisor         Score: 72 ⭐⭐⭐  │
│ maria@crypto.com      Last seen: 1 week ago  │
│ Tags: Founder, Mentor                       │
└─────────────────────────────────────────┘
```

### Contact Detail View

```
[Contact Card]

Header:
├─ Photo / Avatar
├─ Name
├─ Score + Badge
└─ [Edit] [More actions...]

Information:
├─ Email
├─ Phone
├─ Telegram Handle
├─ Location
├─ Interests / Tags
└─ Last Contact Date

Activity:
├─ Messages in our channels (list)
├─ Posts / Interactions
└─ AI Insights

Actions:
├─ [Message] [Add Note] [Set reminder]
├─ [Export] [Delete] [Report]
└─ [View in Telegram]
```

## Accessibility

### Compliance
- WCAG 2.1 AA compliance minimum
- Keyboard navigation for all features
- Screen reader friendly (ARIA labels)
- Color contrast > 4.5:1

### Requirements

```
1. Keyboard users can access everything
   - Tab through all interactive elements
   - Enter/Space to activate
   - Escape to close modals

2. Screen readers
   - All images have alt text
   - Form labels properly associated
   - Semantic HTML

3. Color-blind users
   - Don't rely on color alone
   - Use icons + color
   - High contrast mode

4. Motor control
   - Large touch targets (min 44x44px)
   - No requiring hover states
   - Keyboard alternatives for mouse
```

## Performance Targets

- **Page Load**: < 2 seconds
- **Search Results**: < 500ms
- **API Response**: < 200ms (p95)
- **Contact Load**: < 100ms per contact

## Localization

### Phase 1 (Current)
- English (en)
- Russian (ru) — partial

### Phase 2 (Planned)
- German (de)
- Spanish (es)
- Ukrainian (uk)

### Guidelines
- Use i18n library (e.g., react-i18next)
- Extract strings to `.json` files
- Test RTL languages separately
- Use locale-aware date/time formatting

## Internationalization Checklist

```
□ All user-facing text in i18n keys
□ Date/time formatting respects locale
□ Numbers formatted with proper separator
□ RTL/LTR layout support
□ Currency symbols translated
□ User's locale from profile settings
```

## Testing Strategy

### User Testing
- Quarterly user interviews (N=5-10)
- Monthly feedback surveys
- Usage analytics review
- NPS tracking

### A/B Testing
- New features require A/B test
- Minimum sample: 100 users per variant
- Run for at least 1 week
- 90% confidence level required

### QA Checklist
- All features have acceptance tests
- Edge cases covered
- Performance tested
- Accessibility verified
- Localization checked

---

**Эти руководства — живой документ, требуют обновления по мере развития продукта.**

**Последнее обновление**: 2026-05-08  
**Ответственность**: Product & Design team
