/**
 * Suite 03 — Monitoring / Data page
 */
import { test, expect } from '@playwright/test';
import { goto, waitForLoad, apiGet } from './helpers';

test.describe('Monitoring / Data page', () => {

  test.beforeEach(async ({ page }) => {
    // Dashboard is at /monitoring (sidebar "Данные" → /monitoring)
    await goto(page, '/monitoring');
    await waitForLoad(page);
  });

  test('page loads without errors', async ({ page }) => {
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator('body')).not.toContainText('Something went wrong');
    await expect(page.locator('body')).not.toContainText('Unexpected error');
  });

  test('Data Explorer tree renders folder rows', async ({ page }) => {
    // DataFlowTree renders divs with class "tree-row level-0 folder"
    const rows = page.locator('.tree-row');
    await expect(rows.first()).toBeVisible({ timeout: 12_000 });
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('folders start collapsed — no level-1 rows visible initially', async ({ page }) => {
    // Wait for tree to load
    await expect(page.locator('.tree-row').first()).toBeVisible({ timeout: 10_000 });
    // After our fix, all start collapsed — child rows should not exist yet
    const level1Rows = page.locator('.tree-row.channel, [class*="level-1"]');
    expect(await level1Rows.count()).toBe(0);
  });

  test('clicking a folder row expands it to show children', async ({ page }) => {
    await expect(page.locator('.tree-row').first()).toBeVisible({ timeout: 10_000 });
    // The tree API shows: Personal(0), Unread(0), IT(2), BG Intel(51)...
    // Click "IT" which is the 3rd row (index 2) and has children
    const rows = page.locator('.tree-row');
    const count = await rows.count();
    // Find a row with "IT" text (guaranteed to have children)
    const itRow = page.locator('.tree-row').filter({ hasText: 'IT' }).first();
    if (await itRow.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await itRow.click();
    } else {
      // Fallback: click the 3rd row
      await rows.nth(Math.min(2, count - 1)).click();
    }
    await page.waitForTimeout(500);
    await expect(page.locator('.tree-children')).toBeVisible({ timeout: 5_000 });
  });

  test('vector store widget shows correct totals', async ({ page }) => {
    const card = page.locator('.embeddings-manager');
    await expect(card).toBeVisible({ timeout: 10_000 });
    await expect(card.locator('.label').first()).toContainText('Всего векторов');

    // Validate number shown matches API
    const stats = await apiGet<{ total_embeddings: number }>(page, '/api/stats/embeddings');
    const expected = stats.total_embeddings.toLocaleString('en-US');
    await expect(card.locator('.value').first()).toContainText(expected);
  });

  test('Reindex button is visible and enabled', async ({ page }) => {
    const btn = page.locator('.btn-reindex');
    await expect(btn).toBeVisible({ timeout: 10_000 });
    await expect(btn).toBeEnabled();
    await expect(btn).toContainText('Переиндексировать');
  });

  test('Reindex button triggers API call', async ({ page }) => {
    let called = false;
    await page.route('**/api/stats/embeddings/reindex', async route => {
      called = true;
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'queued', db_name: 'crm' }) });
    });

    await page.locator('.btn-reindex').click();
    await page.waitForTimeout(1_000);
    expect(called).toBe(true);
  });

  test('SystemFlow bar shows Active Streams label', async ({ page }) => {
    // SystemFlow renders "Active Streams: Standby" and "Aggregate Load: Normal"
    await expect(page.locator('body')).toContainText('Active Streams', { timeout: 10_000 });
  });

  test('Data Explorer header columns are visible', async ({ page }) => {
    const treeCard = page.locator('.data-flow-tree');
    await expect(treeCard).toBeVisible({ timeout: 10_000 });
    await expect(treeCard).toContainText('Иерархия данных');
    await expect(treeCard).toContainText('Заполнение');
    await expect(treeCard).toContainText('Сообщений');
  });

});
