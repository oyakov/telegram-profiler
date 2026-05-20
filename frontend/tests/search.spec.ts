import { test, expect } from './fixtures';

test.describe('Поиск', () => {
  test.beforeEach(async ({ authedPage: page }) => {
    await page.goto('/search');
    await expect(page.getByText('Интеллектуальный поиск')).toBeVisible();
  });

  test('страница поиска загружается корректно', async ({ authedPage: page }) => {
    await expect(page.getByRole('button', { name: /Семантический/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /По словам/i })).toBeVisible();
    await expect(page.locator('.search-container input')).toBeVisible();
  });

  test('вкладка AI активна по умолчанию', async ({ authedPage: page }) => {
    await expect(page.locator('.tab-btn.active')).toContainText('Семантический');
  });

  test('placeholder меняется при переключении вкладки', async ({ authedPage: page }) => {
    const input = page.locator('.search-container input');
    const aiPlaceholder = await input.getAttribute('placeholder');
    expect(aiPlaceholder).toMatch(/недвижимост/i);

    await page.getByRole('button', { name: /По словам/i }).click();
    const kwPlaceholder = await input.getAttribute('placeholder');
    expect(kwPlaceholder).toMatch(/ключевое слово/i);
  });

  test('активная вкладка переключается при клике', async ({ authedPage: page }) => {
    await page.getByRole('button', { name: /По словам/i }).click();
    await expect(page.locator('.tab-btn.active')).toContainText('По словам');

    await page.getByRole('button', { name: /Семантический/i }).click();
    await expect(page.locator('.tab-btn.active')).toContainText('Семантический');
  });

  test('показывает AI-индикатор во время запроса', async ({ authedPage: page }) => {
    // Use a controllable Promise so we can release the route AFTER asserting the
    // loading indicator — avoids "page.waitForTimeout: Test ended." when the
    // assertion passes but the route handler is still sleeping.
    let releaseRoute!: () => void;
    await page.route('**/api/search', async route => {
      await new Promise<void>(resolve => { releaseRoute = resolve; });
      route.fulfill({ json: { contacts: [], messages: [] } });
    });

    await page.locator('.search-container input').fill('кто занимается криптой');
    await page.locator('.search-submit').click();

    await expect(page.getByText('AI анализирует смыслы и связи...')).toBeVisible();

    // Now unblock the route so the request completes cleanly before test teardown
    releaseRoute();
    await page.waitForResponse(r => r.url().includes('/api/search'));
  });

  test('отображает найденные контакты с similarity-баром', async ({ authedPage: page }) => {
    await page.route('**/api/search', route =>
      route.fulfill({
        json: {
          contacts: [{
            id: 'u1',
            first_name: 'Иван',
            last_name: 'Петров',
            telegram_username: 'ivanp',
            similarity: 0.87,
          }],
          messages: [],
        },
      })
    );

    await page.locator('.search-container input').fill('разработчики');
    await page.locator('.search-submit').click();

    await expect(page.getByText('Иван Петров')).toBeVisible();
    await expect(page.getByText('@ivanp')).toBeVisible();
    await expect(page.getByText('87%')).toBeVisible();
    await expect(page.locator('.similarity-bar')).toBeVisible();
  });

  test('отображает найденные сообщения', async ({ authedPage: page }) => {
    await page.route('**/api/search', route =>
      route.fulfill({
        json: {
          contacts: [],
          messages: [{
            id: 'm1',
            contact_name: 'Анна Смирнова',
            group_name: 'Tech News',
            timestamp: new Date().toISOString(),
            content: 'Интересная новость про стартапы',
            similarity: 0.75,
          }],
        },
      })
    );

    await page.locator('.search-container input').fill('стартапы');
    await page.locator('.search-submit').click();

    await expect(page.getByText('Анна Смирнова')).toBeVisible();
    await expect(page.getByText('Tech News')).toBeVisible();
    await expect(page.getByText('Интересная новость про стартапы')).toBeVisible();
  });

  test('показывает ошибку при неудачном поиске', async ({ authedPage: page }) => {
    await page.route('**/api/search', route =>
      route.fulfill({ status: 500, json: { detail: 'Сервис векторного поиска недоступен' } })
    );

    await page.locator('.search-container input').fill('тест');
    await page.locator('.search-submit').click();

    await expect(page.locator('.search-error')).toBeVisible();
    await expect(page.getByText('Сервис векторного поиска недоступен')).toBeVisible();
  });

  test('показывает «Ничего не найдено» при пустых результатах', async ({ authedPage: page }) => {
    await page.route('**/api/search', route =>
      route.fulfill({ json: { contacts: [], messages: [] } })
    );

    await page.locator('.search-container input').fill('абракадабра');
    await page.locator('.search-submit').click();

    await expect(page.getByText(/Ничего не найдено/)).toBeVisible();
  });

  test('по ключевым словам вызывает /api/messages/search', async ({ authedPage: page }) => {
    let apiCalled = '';
    // Use a regex so Playwright matches the URL regardless of query-string format.
    await page.route(/\/api\/messages\/search/, route => {
      apiCalled = 'keyword';
      route.fulfill({ json: { messages: [] } });
    });

    await page.getByRole('button', { name: /По словам/i }).click();
    await page.locator('.search-container input').fill('bitcoin');

    // Register waitForResponse BEFORE clicking so we don't race against an
    // immediately-fulfilled mock that resolves before the listener is set up.
    const searchDone = page.waitForResponse(r => r.url().includes('/api/messages/search'));
    await page.locator('.search-submit').click();
    await searchDone;

    expect(apiCalled).toBe('keyword');
  });

  test('пустой запрос не отправляет API-запрос', async ({ authedPage: page }) => {
    let apiCalled = false;
    await page.route('**/api/search', () => { apiCalled = true; });

    await page.locator('.search-submit').click();
    await page.waitForTimeout(300);
    expect(apiCalled).toBe(false);
  });
});
