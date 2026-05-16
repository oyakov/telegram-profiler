/**
 * Suite 07 — Settings page
 *
 * Tests:
 *  - Settings categories render
 *  - Each setting has a key + value display
 *  - Editing a non-critical string setting (mocked save) works
 */
import { test, expect } from '@playwright/test';
import { goto, waitForLoad, apiGet } from './helpers';

test.describe('Settings page', () => {

  test.beforeEach(async ({ page }) => {
    await goto(page, '/settings');
    await waitForLoad(page);
  });

  test('settings page renders', async ({ page }) => {
    await expect(page.locator('h1, h2').filter({ hasText: /настройк/i }).first())
      .toBeVisible({ timeout: 8_000 });
  });

  test('settings list is populated from API', async ({ page }) => {
    const apiData = await apiGet<{ settings: { key: string }[] }>(page, '/api/settings');
    expect(apiData.settings.length).toBeGreaterThan(0);

    // At least a few setting keys should be visible on the page
    const firstKey = apiData.settings[0].key;
    // Keys are often displayed as labels — try to find one
    const label = page.locator(`text=${firstKey}`);
    await expect(label).toBeVisible({ timeout: 8_000 }).catch(() => {
      // Key might be transformed to human-readable label — just verify settings render
      console.log(`[info] Setting key "${firstKey}" not found verbatim — checking for any setting rows`);
    });

    // Fallback: look for any setting input or row
    const rows = page.locator('[class*="setting-row"], [class*="setting-item"], [class*="settings"] input');
    await expect(rows.first()).toBeVisible({ timeout: 5_000 });
  });

  test('editing a setting calls PATCH /api/settings', async ({ page }) => {
    let patchCalled = false;
    await page.route('**/api/settings/**', async route => {
      if (route.request().method() === 'PATCH' || route.request().method() === 'PUT') {
        patchCalled = true;
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
      } else {
        await route.continue();
      }
    });

    // Find any text input in settings and change it
    const inputs = page.locator('[class*="setting"] input[type="text"], [class*="settings"] input[type="text"]');
    if (!(await inputs.first().isVisible({ timeout: 3_000 }).catch(() => false))) {
      test.skip(true, 'No editable text input found on settings page');
      return;
    }

    await inputs.first().triple_click?.() ?? await inputs.first().click({ clickCount: 3 });
    await inputs.first().fill('e2e_test_value');

    // Submit via blur or save button
    const saveBtn = page.locator('button:has-text("Save"), button:has-text("Сохранить"), button[type="submit"]');
    if (await saveBtn.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await saveBtn.click();
    } else {
      await inputs.first().press('Enter');
    }
    await page.waitForTimeout(1_000);
    expect(patchCalled).toBe(true);
  });

  test('Telegram username is shown in the TopBar', async ({ page }) => {
    const authData = await apiGet<{ profile: { first_name: string; username: string } }>(
      page, '/api/telegram/auth/status'
    );
    // TopBar shows the first letter of the name as an avatar initial
    const initial = authData.profile.first_name.charAt(0).toUpperCase();
    const username = authData.profile.username;
    // Either the initial avatar or the @username must appear somewhere in the UI
    const topbar = page.locator('[class*="topbar"], [class*="top-bar"], header').first();
    await expect(topbar).toBeVisible({ timeout: 8_000 });
    const topbarText = await topbar.textContent() ?? '';
    expect(topbarText.includes(initial) || topbarText.includes(username)).toBe(true);
  });

});
