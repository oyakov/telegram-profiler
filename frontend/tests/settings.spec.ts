import { test, expect } from './fixtures';

/** Realistic mock that covers every assertion in this suite. */
const MOCK_SETTINGS = {
  settings: [
    {
      key: 'llm_provider',
      value: 'openai',
      env_value: 'openai',
      value_type: 'string',
      description: 'LLM provider',
      category: 'llm',
      source: 'env',
      updated_at: null,
    },
    {
      key: 'whisper_model',
      value: 'base',
      env_value: 'base',
      value_type: 'string',
      description: 'Whisper model size',
      category: 'whisper',
      source: 'env',
      updated_at: null,
    },
    {
      key: 'embed_provider',
      value: 'openai',
      env_value: 'openai',
      value_type: 'string',
      description: 'Embeddings provider',
      category: 'embeddings',
      source: 'env',
      updated_at: null,
    },
    {
      key: 'embed_dimensions',
      value: 1536,
      env_value: 1536,
      value_type: 'int',
      description: 'Embedding vector dimensions',
      category: 'embeddings',
      source: 'env',
      updated_at: null,
    },
    {
      key: 'telegram_sync_enabled',
      value: true,
      env_value: null,
      value_type: 'bool',
      description: 'Enable Telegram sync',
      category: 'telegram',
      source: 'db',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ],
};

test.describe('Настройки', () => {
  test.beforeEach(async ({ authedPage: page }) => {
    // Mock the settings endpoint so the component can render regardless of backend state
    await page.route('**/api/settings/effective', route =>
      route.fulfill({ json: MOCK_SETTINGS })
    );
    await page.goto('/settings');
    await expect(page.locator('.settings-page')).toBeVisible({ timeout: 12_000 });
  });

  test('загружает страницу настроек с заголовком', async ({ authedPage: page }) => {
    await expect(page.getByRole('heading', { name: 'Настройки' })).toBeVisible();
    await expect(page.getByText(/Конфигурация системы/)).toBeVisible();
  });

  test('показывает вкладки категорий', async ({ authedPage: page }) => {
    await expect(page.getByRole('button', { name: 'Все' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'AI / LLM' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Embeddings' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Whisper STT' })).toBeVisible();
  });

  test('вкладка «Все» активна по умолчанию', async ({ authedPage: page }) => {
    await expect(page.getByRole('button', { name: 'Все' })).toHaveClass(/active/);
  });

  test('фильтр по «AI / LLM» скрывает Whisper-настройки', async ({ authedPage: page }) => {
    await page.getByRole('button', { name: 'AI / LLM' }).click();

    await expect(page.getByText('llm_provider')).toBeVisible();
    await expect(page.getByText('whisper_model')).not.toBeVisible();
  });

  test('фильтр по «Embeddings» показывает embed-настройки', async ({ authedPage: page }) => {
    await page.getByRole('button', { name: 'Embeddings' }).click();

    await expect(page.getByText('embed_provider')).toBeVisible();
    await expect(page.getByText('embed_dimensions')).toBeVisible();
    await expect(page.getByText('llm_provider')).not.toBeVisible();
  });

  test('кнопка «Все» возвращает все категории', async ({ authedPage: page }) => {
    await page.getByRole('button', { name: 'AI / LLM' }).click();
    await expect(page.getByText('whisper_model')).not.toBeVisible();

    await page.getByRole('button', { name: 'Все' }).click();
    await expect(page.getByText('whisper_model')).toBeVisible();
    await expect(page.getByText('llm_provider')).toBeVisible();
  });

  test('повторный клик по активной категории сбрасывает на «Все»', async ({ authedPage: page }) => {
    await page.getByRole('button', { name: 'AI / LLM' }).click();
    await expect(page.getByText('whisper_model')).not.toBeVisible();

    await page.getByRole('button', { name: 'AI / LLM' }).click();
    await expect(page.getByText('whisper_model')).toBeVisible();
  });

  test('поле ввода помечается dirty при изменении', async ({ authedPage: page }) => {
    const firstInput = page.locator('.setting-input').first();
    const original = await firstInput.inputValue();

    await firstInput.clear();
    await firstInput.type(original + '_x');

    const row = firstInput.locator('xpath=ancestor::div[contains(@class,"setting-row")]');
    await expect(row).toHaveClass(/dirty/);
  });

  test('кнопка сохранения появляется только когда поле dirty', async ({ authedPage: page }) => {
    const firstInput = page.locator('.setting-input').first();

    // Initially hidden
    const saveBtn = firstInput.locator('xpath=ancestor::div[contains(@class,"setting-row")]')
      .locator('.icon-btn.save');
    await expect(saveBtn).toHaveClass(/hidden/);

    // After edit — visible
    await firstInput.press('End');
    await firstInput.type('_test');
    await expect(saveBtn).not.toHaveClass(/hidden/);
  });

  test('Enter сохраняет изменённое поле и показывает ✓', async ({ authedPage: page }) => {
    // PUT → mock success; GET (revalidation) → fall through to beforeEach mock
    await page.route('**/api/settings/**', async route => {
      if (route.request().method() === 'PUT') {
        await route.fulfill({ json: { success: true } });
      } else {
        // Pass GET requests to the next handler (the beforeEach mock)
        await route.fallback();
      }
    });

    const firstInput = page.locator('.setting-input').first();
    await firstInput.click();
    await firstInput.press('End');
    await firstInput.type('_save');
    await firstInput.press('Enter');

    const row = firstInput.locator('xpath=ancestor::div[contains(@class,"setting-row")]');
    await expect(row.locator('.icon-btn.save.ok')).toBeVisible({ timeout: 4_000 });
  });

  test('DB-переопределённые настройки показывают бейдж DB и кнопку сброса', async ({ authedPage: page }) => {
    // telegram_sync_enabled has source: 'db' in the mock
    const dbBadge = page.locator('.source-badge.db').first();
    await expect(dbBadge).toBeVisible();
    await expect(dbBadge).toHaveText('DB');

    const resetBtn = page.locator('.icon-btn.reset').first();
    await expect(resetBtn).toBeVisible();
    await expect(resetBtn).toHaveAttribute('title', /Сбросить/i);
  });

  test('ENV-настройки показывают бейдж ENV и не имеют кнопки сброса', async ({ authedPage: page }) => {
    const envRow = page.locator('.setting-row').filter({ has: page.locator('.source-badge.env') }).first();
    await expect(envRow.locator('.source-badge.env')).toHaveText('ENV');
    await expect(envRow.locator('.icon-btn.reset')).not.toBeVisible();
  });

  test('boolean-настройка рендерится как toggle', async ({ authedPage: page }) => {
    // telegram_sync_enabled is bool → rendered as toggle-switch
    await expect(page.locator('.toggle-switch').first()).toBeVisible();
    await expect(page.locator('.toggle-track').first()).toBeVisible();
  });

  test('показывает счётчик DB-переопределений в заголовке', async ({ authedPage: page }) => {
    // telegram_sync_enabled source:db → badge shows "1 переопределено"
    await expect(page.locator('.db-overrides-badge')).toBeVisible();
  });
});
