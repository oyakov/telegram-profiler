import { test, expect } from '@playwright/test';
import { mockTelegramUnauth, mockTelegramAuth, mockDashboard } from './fixtures';

test.describe('Страница входа', () => {
  test('показывает форму входа когда не авторизован', async ({ page }) => {
    await mockTelegramUnauth(page);
    await page.goto('/');

    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByText('Профайлер')).toBeVisible();
    await expect(page.getByText('Войдите через Telegram')).toBeVisible();
    await expect(page.getByLabel('Номер телефона')).toBeVisible();
  });

  test('перенаправляет на /login при прямом доступе к защищённому маршруту', async ({ page }) => {
    await mockTelegramUnauth(page);
    await page.goto('/settings');
    await expect(page).toHaveURL(/\/login/);
  });

  test('форма неактивна во время загрузки — кнопка дизейблится', async ({ page }) => {
    await mockTelegramUnauth(page);
    let resolveRoute!: () => void;
    await page.route('**/api/telegram/auth/send_code', route => {
      return new Promise<void>(res => { resolveRoute = res; })
        .then(() => route.fulfill({ json: { status: 'success', phone_code_hash: 'h1' } }));
    });

    await page.goto('/login');
    await page.getByLabel('Номер телефона').fill('+70001234567');
    await page.getByRole('button', { name: 'Отправить код' }).click();

    // Button should be disabled while API call is in flight
    await expect(page.getByRole('button', { name: /отправка/i })).toBeDisabled();
    resolveRoute();
  });

  test('переходит к шагу ввода кода после успешной отправки телефона', async ({ page }) => {
    await mockTelegramUnauth(page);
    await page.route('**/api/telegram/auth/send_code', route =>
      route.fulfill({ json: { status: 'success', phone_code_hash: 'testhash' } })
    );

    await page.goto('/login');
    await page.getByLabel('Номер телефона').fill('+70001234567');
    await page.getByRole('button', { name: 'Отправить код' }).click();

    await expect(page.getByLabel('Код подтверждения')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Назад' })).toBeVisible();
  });

  test('показывает ошибку API при неверном номере', async ({ page }) => {
    await mockTelegramUnauth(page);
    await page.route('**/api/telegram/auth/send_code', route =>
      route.fulfill({ status: 400, json: { detail: 'Номер телефона некорректен' } })
    );

    await page.goto('/login');
    await page.getByLabel('Номер телефона').fill('+invalid');
    await page.getByRole('button', { name: 'Отправить код' }).click();

    await expect(page.getByText('Номер телефона некорректен')).toBeVisible();
    // Should still be on phone step
    await expect(page.getByLabel('Номер телефона')).toBeVisible();
  });

  test('кнопка Назад возвращает к вводу телефона', async ({ page }) => {
    await mockTelegramUnauth(page);
    await page.route('**/api/telegram/auth/send_code', route =>
      route.fulfill({ json: { status: 'success', phone_code_hash: 'h' } })
    );

    await page.goto('/login');
    await page.getByLabel('Номер телефона').fill('+70001234567');
    await page.getByRole('button', { name: 'Отправить код' }).click();
    await expect(page.getByLabel('Код подтверждения')).toBeVisible();

    await page.getByRole('button', { name: 'Назад' }).click();
    await expect(page.getByLabel('Номер телефона')).toBeVisible();
    await expect(page.getByLabel('Код подтверждения')).not.toBeVisible();
  });

  test('переходит на шаг 2FA если сервер требует пароль', async ({ page }) => {
    await mockTelegramUnauth(page);
    await page.route('**/api/telegram/auth/send_code', route =>
      route.fulfill({ json: { status: 'success', phone_code_hash: 'h' } })
    );
    await page.route('**/api/telegram/auth/verify', route =>
      route.fulfill({ json: { status: 'requires_2fa' } })
    );

    await page.goto('/login');
    await page.getByLabel('Номер телефона').fill('+70001234567');
    await page.getByRole('button', { name: 'Отправить код' }).click();
    await page.getByLabel('Код подтверждения').fill('12345');
    await page.getByRole('button', { name: 'Подтвердить' }).click();

    await expect(page.getByLabel('Пароль двухфакторной аутентификации')).toBeVisible();
  });

  test('успешный вход перенаправляет на Dashboard', async ({ page }) => {
    // mockTelegramUnauth keeps auth/status returning {authorized:false} for ALL calls
    // (including React StrictMode's double-invocation of AuthContext's useEffect).
    // After verify succeeds, Login.tsx calls setIsAuthenticated(true) directly —
    // no second auth/status call needed.
    await mockTelegramUnauth(page);
    await page.route('**/api/telegram/auth/send_code', route =>
      route.fulfill({ json: { status: 'success', phone_code_hash: 'h' } })
    );
    await page.route('**/api/telegram/auth/verify', route =>
      route.fulfill({ json: { status: 'success' } })
    );
    await page.route('**/api/telegram/user', route =>
      route.fulfill({ json: { first_name: 'Test', last_name: 'User', phone: '+70000000000' } })
    );
    await mockDashboard(page);

    await page.goto('/login');
    await page.getByLabel('Номер телефона').fill('+70001234567');
    await page.getByRole('button', { name: 'Отправить код' }).click();
    await page.getByLabel('Код подтверждения').fill('12345');
    await page.getByRole('button', { name: 'Подтвердить' }).click();

    await expect(page).toHaveURL('/', { timeout: 8_000 });
    await expect(page.locator('.sidebar')).toBeVisible();
  });

  test('URL сохраняется при редиректе на login и восстанавливается после входа', async ({ page }) => {
    // mockTelegramUnauth keeps auth/status → {authorized:false} for ALL calls,
    // including React StrictMode's second invocation of AuthContext's useEffect.
    await mockTelegramUnauth(page);
    await page.route('**/api/telegram/auth/send_code', route =>
      route.fulfill({ json: { status: 'success', phone_code_hash: 'h' } })
    );
    await page.route('**/api/telegram/auth/verify', route =>
      route.fulfill({ json: { status: 'success' } })
    );
    // Mock settings API so the page can render after redirect
    await page.route('**/api/settings/**', route =>
      route.fulfill({ json: { settings: [] } })
    );

    await page.goto('/settings');
    await expect(page).toHaveURL(/\/login/);

    await page.getByLabel('Номер телефона').fill('+70001234567');
    await page.getByRole('button', { name: 'Отправить код' }).click();
    await page.getByLabel('Код подтверждения').fill('12345');
    await page.getByRole('button', { name: 'Подтвердить' }).click();

    // Should land on /settings (restored from location.state.from), not /
    await expect(page).toHaveURL('/settings', { timeout: 8_000 });
  });
});
