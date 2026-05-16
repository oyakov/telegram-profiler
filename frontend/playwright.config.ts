import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for headless e2e tests against the local Docker stack.
 *
 * The Vite dev server (port 5173) proxies /api → http://localhost:8000 (crm-app).
 * Tests run headless against a real backend — no mocks for API calls unless
 * explicitly needed for destructive/side-effectful operations.
 *
 * Run:   npx playwright test
 * Debug: npx playwright test --headed --slowMo=500
 * UI:    npx playwright test --ui
 */

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,          // share a single auth session between tests
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: 1,                    // sequential: tests share live DB state
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    baseURL: BASE_URL,
    headless: true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
    // All requests go through the Vite proxy → Docker app
    extraHTTPHeaders: { 'Accept': 'application/json' },
  },

  projects: [
    {
      name: 'setup',
      testMatch: '**/global.setup.ts',
    },
    {
      name: 'e2e',
      use: {
        ...devices['Desktop Chrome'],
        // Reuse auth state saved by setup project
        storageState: 'playwright/.auth/state.json',
      },
      dependencies: ['setup'],
      testIgnore: '**/global.setup.ts',
    },
  ],

  // Reuse existing Vite dev server — start it if not running
  webServer: {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
