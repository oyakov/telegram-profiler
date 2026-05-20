import { test, expect } from './fixtures';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ authedPage: page }) => {
    await page.route('**/api/stats', route =>
      route.fulfill({ json: { total_contacts: 42, total_messages: 1500 } })
    );
    await page.route('**/api/tracking/channels', route =>
      route.fulfill({
        json: {
          channels: Array.from({ length: 5 }, (_, i) => ({
            id: `ch${i}`, title: `Channel ${i}`, messages_count: 100 * i,
          })),
        },
      })
    );
    await page.route('**/api/tracking/folders', route =>
      route.fulfill({
        json: {
          folders: [
            { id: 'f1', name: 'Инвесторы', folder_type: 'folder', message_count: 500 },
            { id: 'f2', name: 'Технологии', folder_type: 'folder', message_count: 200 },
          ],
        },
      })
    );
    await page.route('**/api/tracking/contacts', route =>
      route.fulfill({
        json: {
          contacts: [
            { id: 'c1', first_name: 'Алексей', status: 'active', message_count: 15 },
            { id: 'c2', first_name: 'Мария',   status: 'active', message_count: 7  },
            { id: 'c3', first_name: 'Дмитрий', status: 'active', message_count: 3  },
          ],
        },
      })
    );

    await page.goto('/');
    await expect(page.locator('.dashboard-page')).toBeVisible({ timeout: 10_000 });
  });

  test('показывает имя пользователя из Telegram', async ({ authedPage: page }) => {
    await expect(page.getByText('Test User')).toBeVisible();
  });

  test('показывает счётчик контактов из /api/stats', async ({ authedPage: page }) => {
    const contactStat = page.locator('.profile-stat').filter({ hasText: 'Контактов' });
    await expect(contactStat.locator('.stat-value')).toHaveText('42');
  });

  test('показывает количество каналов', async ({ authedPage: page }) => {
    const channelStat = page.locator('.profile-stat').filter({ hasText: 'Каналов' });
    await expect(channelStat.locator('.stat-value')).toHaveText('5');
  });

  test('таблица папок отображает данные', async ({ authedPage: page }) => {
    await expect(page.getByText('Инвесторы')).toBeVisible();
    await expect(page.getByText('Технологии')).toBeVisible();
  });

  test('таблица контактов отображает данные', async ({ authedPage: page }) => {
    await expect(page.getByText('Алексей')).toBeVisible();
    await expect(page.getByText('Мария')).toBeVisible();
    await expect(page.getByText('Дмитрий')).toBeVisible();
  });

  test('поиск фильтрует контакты по имени', async ({ authedPage: page }) => {
    const searchBox = page.locator('.search-box input');
    await searchBox.fill('алекс');

    await expect(page.getByText('Алексей')).toBeVisible();
    await expect(page.getByText('Мария')).not.toBeVisible();
    await expect(page.getByText('Дмитрий')).not.toBeVisible();
  });

  test('поиск без совпадений не ломает таблицу', async ({ authedPage: page }) => {
    await page.locator('.search-box input').fill('zzznobody');
    await expect(page.getByText('Алексей')).not.toBeVisible();
    // Table heading still visible — use h3 scope to avoid matching the sidebar nav link
    await expect(page.locator('h3').filter({ hasText: 'Личные контакты' })).toBeVisible();
  });

  test('кнопка синхронизации отправляет API-запросы', async ({ authedPage: page }) => {
    const called: string[] = [];
    await page.route('**/api/sync/manual', route => {
      called.push('sync');
      route.fulfill({ json: { status: 'ok' } });
    });
    await page.route('**/api/telegram/contacts/sync', route => {
      called.push('contacts');
      route.fulfill({ json: { task_id: 'task-abc' } });
    });
    await page.route('**/api/telegram/contacts/sync/status/**', route =>
      route.fulfill({ json: { status: 'SUCCESS' } })
    );

    // Set up waitForResponse listeners BEFORE clicking so we don't race against
    // fast mock responses that complete before the listener is registered.
    const syncDone     = page.waitForResponse(r => r.url().includes('/api/sync/manual'));
    const contactsDone = page.waitForResponse(r => r.url().includes('/api/telegram/contacts/sync'));

    await page.locator('.sync-btn').click();

    await syncDone;
    await contactsDone;

    expect(called).toContain('sync');
    expect(called).toContain('contacts');
  });

  test('иконка синхронизации крутится во время запроса', async ({ authedPage: page }) => {
    // Use a controllable Promise so we can unblock the route AFTER the assertion
    // passes — prevents "page.waitForTimeout: Test ended." from route teardown.
    let releaseSyncManual!: () => void;
    await page.route('**/api/sync/manual', async route => {
      await new Promise<void>(resolve => { releaseSyncManual = resolve; });
      route.fulfill({ json: { status: 'ok' } });
    });
    await page.route('**/api/telegram/contacts/sync', route =>
      route.fulfill({ json: { task_id: 't1' } })
    );
    await page.route('**/api/telegram/contacts/sync/status/**', route =>
      route.fulfill({ json: { status: 'SUCCESS' } })
    );

    await page.locator('.sync-btn').click();
    await expect(page.locator('.sync-btn .spinning')).toBeVisible();

    // Unblock the route so the request completes before test teardown
    releaseSyncManual();
    await page.waitForResponse(r => r.url().includes('/api/sync/manual'));
  });

  test('показывает ✓ Готово после успешной синхронизации', async ({ authedPage: page }) => {
    await page.route('**/api/sync/manual', route =>
      route.fulfill({ json: { status: 'ok' } })
    );
    await page.route('**/api/telegram/contacts/sync', route =>
      route.fulfill({ json: { task_id: 't1' } })
    );
    await page.route('**/api/telegram/contacts/sync/status/**', route =>
      route.fulfill({ json: { status: 'SUCCESS' } })
    );

    // Wait for the full sync chain to complete before asserting the success state.
    const statusDone = page.waitForResponse(
      r => r.url().includes('/api/telegram/contacts/sync/status')
    );
    await page.locator('.sync-btn').click();
    await statusDone;

    await expect(page.getByText('✓ Готово')).toBeVisible({ timeout: 5_000 });
  });
});
