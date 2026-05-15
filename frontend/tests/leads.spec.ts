import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

test.describe('Leads Management E2E', () => {

  test.beforeEach(async ({ page }) => {
    page.on('console', msg => console.log(`BROWSER: ${msg.text()}`));

    // Mock auth status
    await page.route(/\/api\/telegram\/auth\/status/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ authorized: true })
      });
    });

    // Mock leads search API — returns the shape useLeads expects
    await page.route(/\/api\/leads\/search/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          contacts: [
            {
              id: '1',
              first_name: 'Lead',
              last_name: 'One',
              telegram_username: 'lead1',
              lead_score: 85.5,
              our_channel_ratio: 40,
              lead_context: { niche: 'Real Estate' },
              notes: 'Very interested in Belgrade flats'
            }
          ],
          total: 1
        })
      });
    });

    // Mock saved searches
    await page.route(/\/api\/leads\/searches/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 's1', name: 'Belgrade Real Estate', filters: { niche: 'Real Estate' } }
        ])
      });
    });

    // Mock stats API
    await page.route('**/api/stats', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total_contacts: 100, total_leads: 10 })
      });
    });

    await page.goto(`${BASE_URL}/leads`, { waitUntil: 'networkidle' });
  });

  test('should display heading and search button', async ({ page }) => {
    const heading = page.locator('h1');
    await expect(heading).toBeVisible({ timeout: 10000 });
    await expect(heading).toContainText('Поиск Лидов');

    const searchBtn = page.locator('button:has-text("Искать лидов")');
    await expect(searchBtn).toBeVisible();
    await expect(searchBtn).toBeEnabled();
  });

  test('should show lead cards after triggering search', async ({ page }) => {
    const searchBtn = page.locator('button:has-text("Искать лидов")');
    await expect(searchBtn).toBeVisible({ timeout: 10000 });
    await searchBtn.click();

    // Wait for lead cards to appear
    await expect(page.locator('.lead-card')).toHaveCount(1, { timeout: 5000 });
    await expect(page.locator('.lead-card').first()).toContainText('Lead One');
    await expect(page.locator('.lead-score-box .value').first()).toContainText('85.5');
  });

  test('should filter leads via keyword input', async ({ page }) => {
    const keywordInput = page.locator('input[placeholder="Добавить ключевое слово..."]');
    await expect(keywordInput).toBeVisible({ timeout: 10000 });
    await keywordInput.fill('Real Estate');

    // Verify search button is enabled
    const searchBtn = page.locator('button:has-text("Искать лидов")');
    await expect(searchBtn).toBeEnabled();

    // Clicking search triggers API (mocked to return 1 lead)
    await searchBtn.click();
    await expect(page.locator('.lead-card')).toHaveCount(1, { timeout: 5000 });
  });

  test('should open save search modal with correct title', async ({ page }) => {
    await page.click('button:has-text("Сохранить поиск")');
    await expect(page.locator('.modal-overlay')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.modal-dialog h3')).toContainText('Сохранить поиск');

    const nameInput = page.locator('input[placeholder="Мой поиск лидов..."]');
    await expect(nameInput).toBeVisible();
    await nameInput.fill('My New Search');

    await page.click('button:has-text("Сохранить")');
    // Modal should close after save (mock the save endpoint)
  });

});
