import { test, expect } from './fixtures';

test.describe('Навигация', () => {
  test.beforeEach(async ({ authedPage: page }) => {
    // Minimal stubs so pages render without hanging
    await page.route('**/api/stats', route =>
      route.fulfill({ json: { total_contacts: 0, total_messages: 0 } })
    );
    await page.route('**/api/tracking/**', route =>
      route.fulfill({ json: { channels: [], folders: [], contacts: [] } })
    );
    await page.route('**/api/connectors/**', route =>
      route.fulfill({ json: { status: 'idle' } })
    );
    await page.goto('/');
    await expect(page.locator('.sidebar')).toBeVisible({ timeout: 10_000 });
  });

  test('sidebar показывает все 8 пунктов навигации', async ({ authedPage: page }) => {
    const expected = [
      'Данные', 'Аудит', 'Поиск и AI', 'Лиды',
      'Рассылки', 'Контакты', 'Личные контакты', 'Настройки',
    ];
    for (const name of expected) {
      // exact: true prevents 'Контакты' from also matching 'Личные контакты'
      await expect(page.locator('.sidebar').getByRole('link', { name, exact: true })).toBeVisible();
    }
  });

  test('«Контакты» и «Личные контакты» имеют разные иконки', async ({ authedPage: page }) => {
    // After our fix: Contacts uses Users icon, Personal Contacts uses BookUser icon
    const contactsLink = page.locator('.nav-item', { hasText: 'Контакты' }).first();
    const personalLink  = page.locator('.nav-item', { hasText: 'Личные контакты' });

    const contactsSvg = await contactsLink.locator('svg').getAttribute('class');
    const personalSvg  = await personalLink.locator('svg').getAttribute('class');

    // Both SVGs exist but are different icons (different path data)
    const contactsPath = await contactsLink.locator('svg path').first().getAttribute('d');
    const personalPath  = await personalLink.locator('svg path').first().getAttribute('d');
    expect(contactsPath).not.toEqual(personalPath);
  });

  test('клик по пункту sidebar меняет URL', async ({ authedPage: page }) => {
    await page.route('**/api/settings/**', route =>
      route.fulfill({ json: { settings: [] } })
    );
    await page.locator('.sidebar').getByRole('link', { name: 'Настройки' }).click();
    await expect(page).toHaveURL('/settings');
  });

  test('клик по «Поиск и AI» открывает страницу поиска', async ({ authedPage: page }) => {
    await page.locator('.sidebar').getByRole('link', { name: 'Поиск и AI' }).click();
    await expect(page).toHaveURL('/search');
    await expect(page.getByText('Интеллектуальный поиск')).toBeVisible();
  });

  test('активный пункт sidebar имеет класс active', async ({ authedPage: page }) => {
    await page.route('**/api/settings/**', route =>
      route.fulfill({ json: { settings: [] } })
    );
    await page.goto('/settings');
    const settingsLink = page.locator('.sidebar').getByRole('link', { name: 'Настройки' });
    await expect(settingsLink).toHaveClass(/active/);

    // Other links are not active
    const searchLink = page.locator('.sidebar').getByRole('link', { name: 'Поиск и AI' });
    await expect(searchLink).not.toHaveClass(/active/);
  });

  test('TopBar содержит ссылки Профиль и Папки', async ({ authedPage: page }) => {
    await expect(page.locator('.top-bar').getByRole('link', { name: 'Профиль' })).toBeVisible();
    await expect(page.locator('.top-bar').getByRole('link', { name: 'Папки' })).toBeVisible();
  });

  test('TopBar показывает индикатор Telegram connected', async ({ authedPage: page }) => {
    await expect(page.getByTitle('Telegram подключён')).toBeVisible();
  });

  test('TopBar показывает «Система онлайн» когда API доступен', async ({ authedPage: page }) => {
    await expect(page.getByText('Система онлайн')).toBeVisible();
  });

  test('Profiler логотип присутствует в sidebar', async ({ authedPage: page }) => {
    await expect(page.locator('.sidebar-header').getByText('Profiler')).toBeVisible();
  });
});

/**
 * Separate describe so it gets its own fresh page and route setup —
 * "Система недоступна" requires TopBar's INITIAL SWR call to fail, which
 * means we must control the route from the very first page load.
 */
test.describe('TopBar — offline indicator', () => {
  test('TopBar показывает «Система недоступна» при ошибке API', async ({ page }) => {
    // Stub dashboard data so the page renders
    await page.route('**/api/stats', route =>
      route.fulfill({ json: { total_contacts: 0, total_messages: 0 } })
    );
    await page.route('**/api/tracking/**', route =>
      route.fulfill({ json: { channels: [], folders: [], contacts: [] } })
    );
    await page.route('**/api/connectors/**', route =>
      route.fulfill({ json: { status: 'idle' } })
    );
    await page.route('**/api/telegram/user', route =>
      route.fulfill({ json: { first_name: 'Test', last_name: 'User', phone: '+70000000000' } })
    );

    // Counter route: React StrictMode fires AuthContext's useEffect TWICE
    // (mount → cleanup → remount), so calls 1 AND 2 must return authorized:true
    // to ensure isAuthenticated=true and the authenticated layout renders.
    // Calls 3+ (TopBar's SWR on mount) → abort → statusError → "Система недоступна".
    let authCalls = 0;
    await page.route('**/api/telegram/auth/status', route => {
      authCalls++;
      if (authCalls <= 2) {
        route.fulfill({ json: { authorized: true, profile: { first_name: 'Test', last_name: 'User', phone: '+70000000000' } } });
      } else {
        route.abort('failed');
      }
    });

    await page.goto('/');
    await expect(page.locator('.sidebar')).toBeVisible({ timeout: 10_000 });

    // TopBar mounts after the authenticated layout renders and immediately fires
    // its own SWR call for auth/status — which is call 2 → abort → error → offline.
    await expect(page.getByText(/Система недоступна/)).toBeVisible({ timeout: 8_000 });
  });
});
