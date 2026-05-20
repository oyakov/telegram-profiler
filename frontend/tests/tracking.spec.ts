import { test, expect } from './fixtures';

const FOLDERS = [
  { id: 'f1', name: 'Инвесторы', description: 'Инвестиции', tags: ['finance', 'invest'], is_active: true, message_count: 0 },
  { id: 'f2', name: 'Технологии', description: '', tags: [], is_active: true, message_count: 0 },
];

const CHANNELS = [
  { id: 'ch1', folder_id: 'f1', title: 'CryptoNews',   username: 'cryptonews', messages_count: 500 },
  { id: 'ch2', folder_id: 'f1', title: 'StockMarket',  username: 'stocks',     messages_count: 200 },
  { id: 'ch3', folder_id: 'f2', title: 'TechChannel',  username: 'tech',       messages_count: 100 },
];

test.describe('Трекинг каналов', () => {
  test.beforeEach(async ({ authedPage: page }) => {
    await page.route('**/api/tracking/folders', route =>
      route.fulfill({ json: { folders: FOLDERS } })
    );
    await page.route('**/api/tracking/channels', route =>
      route.fulfill({ json: { channels: CHANNELS } })
    );
    await page.route('**/api/connectors/pipeline/sync/status', route =>
      route.fulfill({ json: { status: 'idle', last_run: null } })
    );

    await page.goto('/tracking');
    await expect(page.locator('.folder-card').first()).toBeVisible({ timeout: 10_000 });
    // useTracking collapses all folders in a useEffect after data loads;
    // wait for that to settle so every test starts with folders collapsed.
    await expect(page.getByText('CryptoNews', { exact: true })).not.toBeVisible({ timeout: 5_000 });
  });

  test('отображает все папки', async ({ authedPage: page }) => {
    await expect(page.getByText('Инвесторы')).toBeVisible();
    await expect(page.getByText('Технологии')).toBeVisible();
  });

  test('показывает счётчик каналов в каждой папке', async ({ authedPage: page }) => {
    // f1 has 2 channels, f2 has 1
    const counts = await page.locator('.folder-count').allTextContents();
    expect(counts).toContain('2');
    expect(counts).toContain('1');
  });

  test('папки изначально свёрнуты — каналы не видны', async ({ authedPage: page }) => {
    await expect(page.getByText('CryptoNews')).not.toBeVisible();
    await expect(page.getByText('StockMarket')).not.toBeVisible();
  });

  test('клик по папке разворачивает её и показывает каналы', async ({ authedPage: page }) => {
    await page.locator('.folder-card').first().locator('.folder-header').click();

    await expect(page.getByText('CryptoNews', { exact: true })).toBeVisible();
    await expect(page.getByText('StockMarket', { exact: true })).toBeVisible();
  });

  test('повторный клик сворачивает папку', async ({ authedPage: page }) => {
    const header = page.locator('.folder-card').first().locator('.folder-header');
    await header.click();
    await expect(page.getByText('CryptoNews', { exact: true })).toBeVisible();

    await header.click();
    await expect(page.getByText('CryptoNews', { exact: true })).not.toBeVisible();
  });

  test('отображает теги папки', async ({ authedPage: page }) => {
    await expect(page.getByText('#finance')).toBeVisible();
    await expect(page.getByText('#invest')).toBeVisible();
  });

  test('поиск фильтрует каналы по названию', async ({ authedPage: page }) => {
    // Expand all folders
    for (const card of await page.locator('.folder-card').all()) {
      await card.locator('.folder-header').click();
    }

    await page.locator('input[placeholder*="оиск"]').fill('crypto');

    await expect(page.getByText('CryptoNews', { exact: true })).toBeVisible();
    await expect(page.getByText('StockMarket', { exact: true })).not.toBeVisible();
    await expect(page.getByText('TechChannel', { exact: true })).not.toBeVisible();
  });

  test('поиск по username тоже работает', async ({ authedPage: page }) => {
    for (const card of await page.locator('.folder-card').all()) {
      await card.locator('.folder-header').click();
    }

    await page.locator('input[placeholder*="оиск"]').fill('tech');
    await expect(page.getByText('TechChannel')).toBeVisible();
  });

  test('удаление папки вызывает confirm-модал вместо window.confirm', async ({ authedPage: page }) => {
    await page.route('**/api/tracking/folders/**', route =>
      route.fulfill({ json: { success: true } })
    );

    await page.locator('.folder-btn--danger').first().click();

    // Our custom ConfirmModal should appear (not native dialog)
    await expect(page.locator('.confirm-overlay')).toBeVisible();
    await expect(page.getByText('Удаление папки')).toBeVisible();
    await expect(page.locator('.confirm-btn.cancel')).toBeVisible();
    await expect(page.locator('.confirm-btn.ok')).toBeVisible();
  });

  test('отмена в confirm-модале не удаляет папку', async ({ authedPage: page }) => {
    let deleteCallMade = false;
    await page.route('**/api/tracking/folders/**', route => {
      if (route.request().method() === 'DELETE') deleteCallMade = true;
      route.fulfill({ json: { success: true } });
    });

    await page.locator('.folder-btn--danger').first().click();
    await expect(page.locator('.confirm-overlay')).toBeVisible();
    await page.locator('.confirm-btn.cancel').click();

    await expect(page.locator('.confirm-overlay')).not.toBeVisible();
    expect(deleteCallMade).toBe(false);
    // Folder still visible
    await expect(page.getByText('Инвесторы')).toBeVisible();
  });

  test('подтверждение в confirm-модале удаляет папку', async ({ authedPage: page }) => {
    let deleteCallMade = false;
    await page.route('**/api/tracking/folders/f1', route => {
      if (route.request().method() === 'DELETE') {
        deleteCallMade = true;
        route.fulfill({ json: { success: true } });
      } else {
        route.continue();
      }
    });

    await page.locator('.folder-card').first().locator('.folder-btn--danger').click();
    await page.locator('.confirm-btn.ok').click();

    await expect(page.locator('.confirm-overlay')).not.toBeVisible();
    expect(deleteCallMade).toBe(true);
  });

  test('кнопка синхронизации показывает toast вместо alert', async ({ authedPage: page }) => {
    await page.route('**/api/connectors/telegram/sync', route =>
      route.fulfill({ json: { status: 'started' } })
    );

    // Click the sync button in TrackingHeader
    const syncBtn = page.locator('button', { hasText: /Синхронизировать|Sync/i }).first();
    await syncBtn.click();

    // Toast container should appear (not native alert)
    await expect(page.locator('.toast-container')).toBeVisible({ timeout: 4_000 });
    await expect(page.locator('.toast-info')).toBeVisible();
  });
});
