/**
 * Global setup — verifies the Docker stack is reachable and saves browser
 * storage state so subsequent test projects skip login.
 *
 * The app is already authorized (Telegram session in PostgreSQL), so we just
 * confirm /api/telegram/auth/status → authorized:true, load the dashboard,
 * then persist the page's localStorage/cookie state.
 */
import { test as setup, expect } from '@playwright/test';

const AUTH_FILE = 'playwright/.auth/state.json';

setup('verify stack and save auth state', async ({ page }) => {
  // 1. Backend health check
  const health = await page.request.get('/api/stats/health');
  expect(health.ok(), `Backend health check failed: ${health.status()}`).toBeTruthy();

  // 2. Telegram session must already be authorized
  const authResp = await page.request.get('/api/telegram/auth/status');
  expect(authResp.ok()).toBeTruthy();
  const auth = await authResp.json();
  expect(auth.authorized, 'Telegram session must be authorized before running e2e tests').toBe(true);

  // 3. Load the app — should land on dashboard (not /login)
  await page.goto('/');
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 10_000 });
  await expect(page).not.toHaveURL(/\/login/);

  // 4. Persist storage state
  await page.context().storageState({ path: AUTH_FILE });
});
