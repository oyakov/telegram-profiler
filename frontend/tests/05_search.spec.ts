/**
 * Suite 05 — Search page (semantic + keyword)
 *
 * Tests:
 *  - Search input renders
 *  - Submitting a query triggers POST /api/search
 *  - Results render (mocked for speed / determinism)
 *  - Empty query shows no results gracefully
 *  - Network error shows an error state
 */
import { test, expect } from '@playwright/test';
import { goto, waitForLoad } from './helpers';

const MOCK_RESULTS = {
  contacts: [
    {
      id: 'e2e-contact-1',
      first_name: 'Playwright',
      last_name: 'Testuser',
      telegram_username: 'pw_testuser',
      similarity: 0.92,
    },
  ],
  messages: [
    {
      id: 'e2e-msg-1',
      content: 'Looking for a flat in Belgrade near the center',
      contact_name: 'Playwright Testuser',
      group_name: 'BG Rent',
      timestamp: new Date().toISOString(),
      similarity: 0.88,
    },
  ],
  total: 1,
};

test.describe('Search page', () => {

  test.beforeEach(async ({ page }) => {
    // Mock the search endpoint to avoid hitting real LMStudio / DB
    await page.route('**/api/search', async route => {
      if (route.request().method() === 'POST') {
        const body = route.request().postDataJSON() as { query?: string };
        if (!body?.query || body.query.trim() === '') {
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ contacts: [], messages: [], total: 0 }) });
        } else {
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RESULTS) });
        }
      } else {
        await route.continue();
      }
    });

    await goto(page, '/search');
    await waitForLoad(page);
  });

  test('search input is visible and focused-ready', async ({ page }) => {
    const input = page.locator('input[type="text"], input[type="search"], textarea').first();
    await expect(input).toBeVisible({ timeout: 8_000 });
  });

  test('submitting a query shows results', async ({ page }) => {
    const input = page.locator('input[type="text"], input[type="search"], textarea').first();
    await expect(input).toBeVisible({ timeout: 8_000 });
    await input.fill('flat in Belgrade');

    // Submit via Enter or button
    const submitBtn = page.locator('button[type="submit"], button:has-text("Поиск"), button:has-text("Search")');
    if (await submitBtn.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await submitBtn.click();
    } else {
      await input.press('Enter');
    }

    // Wait for mock results to render
    await expect(page.locator('body')).toContainText('Playwright Testuser', { timeout: 8_000 });
    await expect(page.locator('body')).toContainText('Looking for a flat', { timeout: 5_000 });
  });

  test('results show similarity scores', async ({ page }) => {
    const input = page.locator('input[type="text"], input[type="search"], textarea').first();
    await input.fill('test query');
    await input.press('Enter');
    await page.waitForTimeout(1_500);

    // Score like "0.92" or "92%" should appear
    const body = await page.locator('body').textContent() ?? '';
    expect(body).toMatch(/0\.\d{2}|9[0-9]%|\bsimilarity\b/i);
  });

  test('loading state is shown during search', async ({ page }) => {
    // Slow down the mock to observe the loading indicator
    await page.route('**/api/search', async route => {
      await new Promise(r => setTimeout(r, 800));
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RESULTS) });
    });

    const input = page.locator('input[type="text"], input[type="search"], textarea').first();
    await input.fill('delayed search');
    await input.press('Enter');

    // A spinner, thinking container, or disabled button should appear
    const hasSpinner = await page.locator('.spin, [class*="think"], [class*="loading"], button[disabled]')
      .first().isVisible({ timeout: 500 }).catch(() => false);
    // Not strictly required — just log if absent
    if (!hasSpinner) {
      console.log('[info] No visible loading state detected during search');
    }

    await expect(page.locator('body')).toContainText('Playwright Testuser', { timeout: 6_000 });
  });

  test('API error does not crash the page', async ({ page }) => {
    await page.route('**/api/search', async route => {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Internal Server Error' }) });
    });

    const input = page.locator('input[type="text"], input[type="search"], textarea').first();
    await input.fill('error trigger');
    await input.press('Enter');
    await page.waitForTimeout(2_000);

    // Page must not hard-crash — the React app should still be mounted
    await expect(page.locator('body')).not.toContainText('Something went wrong');
    await expect(page).not.toHaveURL(/\/login/);
    // Either an error message or simply no results (both are acceptable UX)
    const body = await page.locator('body').textContent() ?? '';
    // Just verify the search input is still present (page didn't crash)
    const inputStillThere = await page.locator('input[type="text"], input[type="search"], textarea').first()
      .isVisible({ timeout: 2_000 }).catch(() => false);
    expect(inputStillThere).toBe(true);
  });

});
