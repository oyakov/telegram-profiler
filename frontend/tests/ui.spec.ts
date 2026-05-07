import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173'; // Vite default

test.describe('Telegram Profiler UI Rework', () => {
  
  test.beforeEach(async ({ page }) => {
    // Mock basic stats API
    await page.route('**/api/stats', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_contacts: 1500,
          total_messages: 45000,
          total_leads: 120,
          total_voice_notes: 450,
          contacts_by_source: { "crm": 1000, "crm_crypto": 500 }
        })
      });
    });

    // Mock tracking API
    await page.route('**/api/tracking/channels', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          channels: [
            { id: 1, title: 'Test Channel', username: 'test_ch', messages_count: 100, is_active: true, type: 'channel', last_sync: new Date().toISOString() }
          ]
        })
      });
    });

    await page.goto(BASE_URL);
  });

  test('should display dashboard metrics', async ({ page }) => {
    await expect(page.locator('.metric-value').first()).toContainText('1500');
    await expect(page.locator('.metric-value').nth(1)).toContainText('45000');
    await expect(page.locator('h1')).toContainText('Обзор Проекта');
  });

  test('should navigate to Tracking page and search', async ({ page }) => {
    await page.click('text=Трекинг');
    await expect(page).toHaveURL(/.*tracking/);
    await expect(page.locator('.channel-card')).toBeVisible();
    
    const searchInput = page.locator('.search-bar-container input');
    await searchInput.fill('Test');
    await expect(page.locator('.channel-card')).toHaveCount(1);
    
    await searchInput.fill('NonExistent');
    await expect(page.locator('.channel-card')).toHaveCount(0);
  });

  test('should perform semantic search with thinking state', async ({ page }) => {
    await page.click('text=Поиск и AI');
    
    // Mock search API with delay to see thinking state
    await page.route('**/api/search', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          contacts: [{ id: 1, first_name: 'John', last_name: 'Doe', telegram_username: 'johndoe', similarity: 0.95 }],
          messages: [{ content: 'Looking for a flat in Belgrade', contact_name: 'John Doe', group_name: 'Rental', timestamp: new Date().toISOString(), similarity: 0.92 }]
        })
      });
    });

    const searchInput = page.locator('.search-container input');
    await searchInput.fill('Who wants to rent?');
    await page.click('.search-submit');

    // Check thinking state
    await expect(page.locator('.thinking-container')).toBeVisible();
    
    // Check results
    await expect(page.locator('.contact-card')).toBeVisible();
    await expect(page.locator('.message-card')).toBeVisible();
    await expect(page.locator('.contact-card')).toContainText('John Doe');
  });

  test('should switch databases', async ({ page }) => {
    await page.click('.switcher-btn');
    await expect(page.locator('.project-menu')).toBeVisible();
    
    // Mock reload or check localStorage if possible
    await page.click('text=Crypto Universe');
    
    // After reload, check if it's the active one
    // Note: Playwright might need to handle the reload properly
    await expect(page.locator('.current-project-label')).toContainText('Crypto Universe');
  });

});
