import { test, expect } from './fixtures';

test.describe('Toast-уведомления', () => {
  test.beforeEach(async ({ authedPage: page }) => {
    await page.route('**/api/tracking/folders', route =>
      route.fulfill({ json: { folders: [{ id: 'f1', name: 'Test', description: '', tags: [], is_active: true, message_count: 0 }] } })
    );
    await page.route('**/api/tracking/channels', route =>
      route.fulfill({ json: { channels: [] } })
    );
    await page.route('**/api/connectors/pipeline/sync/status', route =>
      route.fulfill({ json: { status: 'idle' } })
    );
  });

  test('toast-контейнер рендерится в DOM', async ({ authedPage: page }) => {
    await page.goto('/');
    // Container exists but is empty when no toasts
    await expect(page.locator('.toast-container')).toBeAttached();
  });

  test('успешная операция показывает зелёный toast', async ({ authedPage: page }) => {
    await page.route('**/api/connectors/telegram/sync', route =>
      route.fulfill({ json: { status: 'started' } })
    );

    await page.goto('/tracking');
    await expect(page.locator('.folder-card')).toBeVisible({ timeout: 8_000 });

    const syncBtn = page.locator('button', { hasText: /Синхронизировать/i }).first();
    await syncBtn.click();

    await expect(page.locator('.toast.toast-info')).toBeVisible({ timeout: 4_000 });
  });

  test('ошибочная операция показывает красный toast', async ({ authedPage: page }) => {
    await page.route('**/api/connectors/telegram/sync', route =>
      route.fulfill({ status: 500, json: { detail: 'Telegram не отвечает' } })
    );

    await page.goto('/tracking');
    await expect(page.locator('.folder-card')).toBeVisible({ timeout: 8_000 });

    const syncBtn = page.locator('button', { hasText: /Синхронизировать/i }).first();
    await syncBtn.click();

    await expect(page.locator('.toast.toast-error')).toBeVisible({ timeout: 4_000 });
    await expect(page.getByText('Telegram не отвечает')).toBeVisible();
  });

  test('toast закрывается по кнопке ×', async ({ authedPage: page }) => {
    await page.route('**/api/connectors/telegram/sync', route =>
      route.fulfill({ json: { status: 'started' } })
    );

    await page.goto('/tracking');
    await expect(page.locator('.folder-card')).toBeVisible({ timeout: 8_000 });

    await page.locator('button', { hasText: /Синхронизировать/i }).first().click();
    const toast = page.locator('.toast').first();
    await expect(toast).toBeVisible({ timeout: 4_000 });

    await toast.locator('.toast-close').click();
    await expect(toast).not.toBeVisible();
  });

  test('confirm-модал не является нативным window.confirm', async ({ authedPage: page }) => {
    await page.goto('/tracking');
    await expect(page.locator('.folder-card')).toBeVisible({ timeout: 8_000 });

    // Listen for native dialog — should NOT appear
    let nativeDialogFired = false;
    page.on('dialog', () => { nativeDialogFired = true; });

    await page.locator('.folder-btn--danger').first().click();

    // Custom modal should be there
    await expect(page.locator('.confirm-overlay')).toBeVisible();
    expect(nativeDialogFired).toBe(false);

    // Dismiss it
    await page.locator('.confirm-btn.cancel').click();
  });
});
