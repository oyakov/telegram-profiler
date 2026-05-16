/**
 * Suite 09 — Audit page
 *
 * Verifies the audit log renders task history from the DB.
 */
import { test, expect } from '@playwright/test';
import { goto, waitForLoad } from './helpers';

test.describe('Audit page', () => {

  test.beforeEach(async ({ page }) => {
    await goto(page, '/audit');
    await waitForLoad(page);
  });

  test('audit page loads without errors', async ({ page }) => {
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator('body')).not.toContainText('Something went wrong');
  });

  test('page heading is visible', async ({ page }) => {
    await expect(page.locator('h1, h2').filter({ hasText: /аудит/i }).first())
      .toBeVisible({ timeout: 8_000 });
  });

  test('task monitoring section renders', async ({ page }) => {
    // TaskMonitoring component or celery tasks section
    const taskSection = page.locator('[class*="task-monitor"], [class*="TaskMonitor"], [class*="audit"]').first();
    await expect(taskSection).toBeVisible({ timeout: 10_000 });
  });

  test('celery tasks API data is reflected', async ({ page }) => {
    // The audit page shows Celery task history — at minimum the "running/queued/workers" summary
    await expect(page.locator('body')).toContainText(
      /running|queued|worker|задач|задан/i,
      { timeout: 10_000 }
    );
  });

});
