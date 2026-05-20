import { test as base, expect, type Page } from '@playwright/test';

export { expect };

/** Mock Telegram auth + user endpoints so the UI shows as authenticated. */
export async function mockTelegramAuth(page: Page, user = { first_name: 'Test', last_name: 'User', phone: '+70000000000' }) {
  await page.route('**/api/telegram/auth/status', route =>
    route.fulfill({ json: { authorized: true, profile: user } })
  );
  await page.route('**/api/telegram/user', route =>
    route.fulfill({ json: user })
  );
}

/** Mock Telegram auth as NOT authorized (for login-page tests). */
export async function mockTelegramUnauth(page: Page) {
  await page.route('**/api/telegram/auth/status', route =>
    route.fulfill({ json: { authorized: false } })
  );
}

/** Mock the dashboard data endpoints. */
export async function mockDashboard(page: Page) {
  await page.route('**/api/stats', route =>
    route.fulfill({ json: { total_contacts: 42, total_messages: 1500 } })
  );
  await page.route('**/api/tracking/channels', route =>
    route.fulfill({ json: { channels: [] } })
  );
  await page.route('**/api/tracking/folders', route =>
    route.fulfill({ json: { folders: [] } })
  );
  await page.route('**/api/tracking/contacts', route =>
    route.fulfill({ json: { contacts: [] } })
  );
}

/** Extended test with an `authedPage` fixture (mocks auth, passes real page). */
export const test = base.extend<{ authedPage: Page }>({
  authedPage: async ({ page }, use) => {
    await mockTelegramAuth(page);
    await use(page);
  },
});
