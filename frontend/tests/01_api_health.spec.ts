/**
 * Suite 01 — API health & contract tests
 *
 * Pure HTTP checks (no browser): verifies all critical endpoints return
 * expected shapes and status codes. Runs first so failures here explain
 * UI test failures downstream.
 */
import { test, expect } from '@playwright/test';

test.describe('API health & contracts', () => {

  test('GET /api/stats/health → ok', async ({ request }) => {
    const r = await request.get('/api/stats/health');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.status).toBe('healthy');
    expect(body.checks.database).toBe('ok');
  });

  test('GET /api/telegram/auth/status → authorized', async ({ request }) => {
    const r = await request.get('/api/telegram/auth/status');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.authorized).toBe(true);
    expect(body.profile).toMatchObject({
      telegram_id: expect.any(String),
      first_name: expect.any(String),
    });
  });

  test('GET /api/stats → totals are positive integers', async ({ request }) => {
    const r = await request.get('/api/stats');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(typeof body.total_contacts).toBe('number');
    expect(typeof body.total_messages).toBe('number');
    expect(body.total_contacts).toBeGreaterThan(0);
    expect(body.total_messages).toBeGreaterThan(0);
  });

  test('GET /api/stats/embeddings → correct shape', async ({ request }) => {
    const r = await request.get('/api/stats/embeddings');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body).toMatchObject({
      total_messages: expect.any(Number),
      messages_with_embeddings: expect.any(Number),
      messages_needing_embeddings: expect.any(Number),
      progress_percent: expect.any(Number),
    });
    expect(body.progress_percent).toBeGreaterThanOrEqual(0);
    expect(body.progress_percent).toBeLessThanOrEqual(100);
  });

  test('GET /api/contacts → returns contact list', async ({ request }) => {
    const r = await request.get('/api/contacts?limit=5');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body.contacts)).toBe(true);
    expect(body.contacts.length).toBeGreaterThan(0);
    // Verify contact shape
    const c = body.contacts[0];
    expect(c).toHaveProperty('id');
    expect(c).toHaveProperty('first_name');
    expect(c).toHaveProperty('telegram_id');
  });

  test('GET /api/tracking/folders → returns folders array', async ({ request }) => {
    const r = await request.get('/api/tracking/folders');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body.folders)).toBe(true);
    expect(body.folders.length).toBeGreaterThan(0);
    const f = body.folders[0];
    expect(f).toHaveProperty('id');
    expect(f).toHaveProperty('name');
  });

  test('GET /api/tracking/channels → returns channel list', async ({ request }) => {
    const r = await request.get('/api/tracking/channels?limit=5');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body.channels)).toBe(true);
    const ch = body.channels[0];
    expect(ch).toHaveProperty('id');
    expect(ch).toHaveProperty('title');
    expect(ch).toHaveProperty('telegram_id');
  });

  test('GET /api/stats/tree → hierarchical tree with folders', async ({ request }) => {
    const r = await request.get('/api/stats/tree');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body.tree)).toBe(true);
    expect(body.tree.length).toBeGreaterThan(0);
    const node = body.tree[0];
    expect(node).toHaveProperty('name');
    expect(node.type).toBe('folder');
    expect(Array.isArray(node.children)).toBe(true);
  });

  test('GET /api/settings → returns settings list', async ({ request }) => {
    const r = await request.get('/api/settings');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body.settings)).toBe(true);
    expect(body.settings.length).toBeGreaterThan(0);
    expect(body.settings[0]).toHaveProperty('key');
  });

  test('POST /api/stats/embeddings/reindex → queues task', async ({ request }) => {
    const r = await request.post('/api/stats/embeddings/reindex');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.status).toBe('queued');
    expect(body.db_name).toBeTruthy();
  });

  test('POST /api/leads/search → returns result shape', async ({ request }) => {
    const r = await request.post('/api/leads/search', {
      data: { limit: 5, min_lead_score: 0 },
    });
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body).toMatchObject({
      contacts: expect.any(Array),
      total: expect.any(Number),
    });
  });

  test('GET /api/messages/search → keyword search works', async ({ request }) => {
    const r = await request.get('/api/messages/search?q=a&limit=3');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body.messages ?? body.results ?? body)).toBe(true);
  });

  test('GET /api/sync/status → sync state returned', async ({ request }) => {
    const r = await request.get('/api/sync/status');
    expect(r.status()).toBe(200);
  });

});
