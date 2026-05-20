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
  // 1. Backend health check — /api/telegram/auth/status is the most reliable
  //    endpoint (no FastAPI Request-injection dependency).  /api/stats returns
  //    422 because it requires an injected FastAPI Request object.
  const health = await page.request.get('/api/telegram/auth/status');
  expect(health.ok(), `Backend health check failed: ${health.status()}`).toBeTruthy();

  // 2. Telegram session must already be authorized (reuse the response above)
  const authResp = health;
  const auth = await authResp.json();
  expect(auth.authorized, 'Telegram session must be authorized before running e2e tests').toBe(true);

  // 3. Load the app — should land on dashboard (not /login)
  await page.goto('/');
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 10_000 });
  await expect(page).not.toHaveURL(/\/login/);

  // 4. Persist storage state
  await page.context().storageState({ path: AUTH_FILE });
});
