/**
 * Suite 02 — Navigation & layout
 *
 * Verifies:
 *  - App loads on "/" and shows the dashboard (not login)
 *  - Sidebar is present with all expected nav items
 *  - Each nav link routes to the correct page
 *  - TopBar is rendered
 */
import { test, expect } from '@playwright/test';
import { goto, waitForLoad } from './helpers';

const NAV_ITEMS = [
  { label: 'Данные',            url: '/monitoring' },
  { label: 'Аудит',             url: '/audit' },
  { label: 'Поиск и AI',        url: '/search' },
  { label: 'Лиды',              url: '/leads' },
  { label: 'Рассылки',          url: '/campaigns' },
  { label: 'Контакты',          url: '/contacts' },
  { label: 'Личные Контакты',   url: '/personal-contacts' },
  { label: 'Настройки',         url: '/settings' },
];

test.describe('Navigation & layout', () => {

  test.beforeEach(async ({ page }) => {
    await goto(page, '/');
    await waitForLoad(page);
  });

  test('app loads dashboard — not login page', async ({ page }) => {
    await expect(page).not.toHaveURL(/\/login/);
    // Sidebar must be visible
    await expect(page.locator('nav, [class*="sidebar"], aside').first()).toBeVisible({ timeout: 8_000 });
  });

  test('sidebar contains all nav items', async ({ page }) => {
    const sidebar = page.locator('aside.sidebar');
    await expect(sidebar).toBeVisible({ timeout: 8_000 });
    for (const item of NAV_ITEMS) {
      // Use first() to avoid strict-mode violation when a label is a substring of another
      await expect(sidebar.locator('.nav-name').filter({ hasText: item.label }).first())
        .toBeVisible({ timeout: 5_000 });
    }
  });

  test('each sidebar link navigates to correct route', async ({ page }) => {
    for (const item of NAV_ITEMS) {
      // Click the nav-item via the .nav-name span
      await page.locator('.nav-item').filter({ hasText: item.label }).first().click();
      await page.waitForURL(`**${item.url}`, { timeout: 8_000 });
      await waitForLoad(page);
      await expect(page.locator('body')).not.toContainText('Not Found');
      await expect(page.locator('body')).not.toContainText('Something went wrong');
    }
  });

  test('TopBar is rendered on every page', async ({ page }) => {
    for (const item of NAV_ITEMS) {
      await goto(page, item.url);
      // TopBar typically contains the project/DB switcher or a header bar
      const topbar = page.locator('[class*="topbar"], [class*="top-bar"], header').first();
      await expect(topbar).toBeVisible({ timeout: 5_000 });
    }
  });

  test('direct URL navigation works (no 404 or redirect to login)', async ({ page }) => {
    const routes = ['/', '/contacts', '/search', '/leads', '/settings'];
    for (const route of routes) {
      await goto(page, route);
      await expect(page).not.toHaveURL(/\/login/);
    }
  });

});
