import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

test.describe('Campaign Management E2E', () => {

  test.beforeEach(async ({ page }) => {
    // Mock auth status
    await page.route(/\/api\/telegram\/auth\/status/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ authorized: true })
      });
    });

    // Mock campaigns list — matches the Campaign interface in Campaigns.tsx
    await page.route(/\/api\/campaigns(\?.*)?/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          campaigns: [
            {
              id: 'c1',
              name: 'Real Estate Reachout',
              status: 'sending',
              total_contacts: 50,
              sent_count: 23,
              failed_count: 0,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            },
            {
              id: 'c2',
              name: 'IT Job Offers',
              status: 'completed',
              total_contacts: 20,
              sent_count: 20,
              failed_count: 0,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            }
          ]
        })
      });
    });

    // Mock contacts for campaign creation
    await page.route(/\/api\/contacts(\?.*)?/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ contacts: [], total: 0 })
      });
    });

    // Mock stats API
    await page.route(/\/api\/stats/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total_contacts: 100, total_leads: 10, running_campaigns: 1 })
      });
    });

    await page.goto(`${BASE_URL}/campaigns`, { waitUntil: 'networkidle' });
  });

  test('should display campaigns list with correct heading', async ({ page }) => {
    const heading = page.locator('h1');
    await expect(heading).toBeVisible({ timeout: 10000 });
    await expect(heading).toContainText('Кампании');

    // Campaign cards should be visible
    await expect(page.locator('.campaign-card')).toHaveCount(2, { timeout: 5000 });
    await expect(page.locator('.campaign-card').first()).toContainText('Real Estate Reachout');
  });

  test('should show correct status labels on campaign cards', async ({ page }) => {
    await expect(page.locator('.campaign-card')).toHaveCount(2, { timeout: 5000 });

    // First card has status 'sending' → label "Отправляется"
    await expect(page.locator('.campaign-card').first().locator('.status')).toContainText('Отправляется');

    // Second card has status 'completed' → label "Завершена"
    await expect(page.locator('.campaign-card').nth(1).locator('.status')).toContainText('Завершена');
  });

  test('should show campaign form for creating a campaign', async ({ page }) => {
    // The form is inline (not in a modal)
    const nameInput = page.locator('input[placeholder="Например: Приглашение на вебинар"]');
    await expect(nameInput).toBeVisible({ timeout: 10000 });

    await nameInput.fill('Test Campaign');

    const messageTextarea = page.locator('textarea[placeholder*="Привет"]');
    await expect(messageTextarea).toBeVisible();
    await messageTextarea.fill('Hello {first_name}!');

    // Create button should exist but be disabled (no contacts selected)
    const createBtn = page.locator('button:has-text("Создать кампанию")');
    await expect(createBtn).toBeVisible();
    await expect(createBtn).toBeDisabled();
  });

});
