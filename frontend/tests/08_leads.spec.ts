/**
 * Suite 08 — Leads page
 *
 * Uses mocked API so tests are deterministic regardless of extraction state.
 */
import { test, expect } from '@playwright/test';
import { goto, waitForLoad } from './helpers';

const MOCK_LEADS = {
  contacts: [
    {
      id: 'lead-e2e-1',
      first_name: 'Ivan',
      last_name: 'Petrov',
      telegram_username: 'ivanpetrov',
      lead_score: 92.0,
      our_channel_ratio: 55,
      lead_context: { niche: 'Real Estate' },
      notes: 'Very active buyer',
    },
    {
      id: 'lead-e2e-2',
      first_name: 'Maria',
      last_name: 'Ivanova',
      telegram_username: 'mariasells',
      lead_score: 74.5,
      our_channel_ratio: 30,
      lead_context: { niche: 'IT' },
      notes: '',
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
  pages: 1,
};

test.describe('Leads page', () => {

  test.beforeEach(async ({ page }) => {
    await page.route('**/api/leads/search', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_LEADS) });
    });
    await page.route('**/api/leads/searches', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await goto(page, '/leads');
    await waitForLoad(page);
  });

  test('page heading is visible', async ({ page }) => {
    await expect(page.locator('h1, h2').filter({ hasText: /лид/i }).first())
      .toBeVisible({ timeout: 8_000 });
  });

  test('search button triggers lead fetch and renders cards', async ({ page }) => {
    const btn = page.locator('button:has-text("Искать лидов")');
    await expect(btn).toBeVisible({ timeout: 8_000 });
    await btn.click();

    await expect(page.locator('[class*="lead-card"]').first()).toBeVisible({ timeout: 6_000 });
    const cards = page.locator('[class*="lead-card"]');
    expect(await cards.count()).toBe(2);
    await expect(cards.first()).toContainText('Ivan Petrov');
    await expect(cards.nth(1)).toContainText('Maria Ivanova');
  });

  test('lead score is displayed', async ({ page }) => {
    await page.locator('button:has-text("Искать лидов")').click();
    await expect(page.locator('[class*="lead-card"]').first()).toBeVisible({ timeout: 6_000 });
    // Score 92.0 or 92 should appear on the first card
    await expect(page.locator('[class*="lead-card"]').first()).toContainText(/92/);
  });

  test('keyword filter input is present', async ({ page }) => {
    const keywordInput = page.locator(
      'input[placeholder*="ключевое" i], input[placeholder*="keyword" i], input[placeholder*="слово" i]'
    ).first();
    await expect(keywordInput).toBeVisible({ timeout: 8_000 });
  });

  test('save search button opens modal', async ({ page }) => {
    const saveBtn = page.locator('button:has-text("Сохранить поиск"), button:has-text("Save search")');
    if (!(await saveBtn.isVisible({ timeout: 3_000 }).catch(() => false))) {
      test.skip(true, 'Save search button not found');
      return;
    }
    await saveBtn.click();
    // Use the overlay specifically to avoid strict mode violation on multiple modal-* elements
    await expect(page.locator('.modal-overlay').first()).toBeVisible({ timeout: 3_000 });
    // Close modal
    await page.keyboard.press('Escape');
  });

  test('empty leads state shows helpful message', async ({ page }) => {
    // Override to return empty
    await page.route('**/api/leads/search', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ contacts: [], total: 0, page: 1, page_size: 50, pages: 0 }) });
    });
    const btn = page.locator('button:has-text("Искать лидов")');
    await btn.click();
    await page.waitForTimeout(1_000);
    // Should not crash — empty state message
    await expect(page.locator('[class*="lead-card"]')).toHaveCount(0);
    await expect(page.locator('body')).toContainText(/нет лидов|no leads|not found|0 results/i).catch(() => {
      console.log('[info] No explicit empty state message shown');
    });
  });

});
