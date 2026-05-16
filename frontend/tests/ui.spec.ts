/**
 * ui.spec.ts — Smoke tests (kept for backward compatibility).
 *
 * These are quick sanity checks that the most critical paths work.
 * Full coverage lives in the numbered suites (01_* – 09_*).
 */
import { test, expect } from '@playwright/test';

test.describe('Smoke tests', () => {

  test('dashboard loads and is not login page', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator('body')).not.toContainText('Something went wrong');
  });

  test('sidebar navigation renders', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const sidebar = page.locator('nav, aside, [class*="sidebar"]').first();
    await expect(sidebar).toBeVisible({ timeout: 8_000 });
    // Key nav items
    await expect(sidebar).toContainText('Данные');
    await expect(sidebar).toContainText('Контакты');
  });

  test('contacts page shows real data', async ({ page }) => {
    await page.goto('/contacts', { waitUntil: 'networkidle' });
    await expect(page).not.toHaveURL(/\/login/);
    // Real DB has 53 000+ contacts — any number > 0 proves the API is connected
    const items = page.locator('[class*="contact-card"], [class*="contact-row"], tbody tr');
    await expect(items.first()).toBeVisible({ timeout: 15_000 });
  });

  test('API health endpoint returns ok', async ({ request }) => {
    const r = await request.get('/api/stats/health');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.status).toBe('healthy');
  });

  test('settings page renders without crashing', async ({ page }) => {
    await page.goto('/settings', { waitUntil: 'networkidle' });
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator('body')).not.toContainText('Something went wrong');
  });

});
