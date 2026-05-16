/**
 * Shared test helpers — API client, wait utils, common assertions.
 */
import { Page, expect } from '@playwright/test';

/** Typed API GET helper that asserts 200 and returns parsed JSON. */
export async function apiGet<T = unknown>(page: Page, path: string): Promise<T> {
  const resp = await page.request.get(path);
  expect(resp.ok(), `GET ${path} → ${resp.status()}`).toBeTruthy();
  return resp.json() as Promise<T>;
}

/** Typed API POST helper. */
export async function apiPost<T = unknown>(page: Page, path: string, body: object): Promise<T> {
  const resp = await page.request.post(path, { data: body });
  expect(resp.ok(), `POST ${path} → ${resp.status()}`).toBeTruthy();
  return resp.json() as Promise<T>;
}

/** Navigate to a route and wait until the page stops loading. */
export async function goto(page: Page, route: string) {
  await page.goto(route, { waitUntil: 'networkidle', timeout: 15_000 });
}

/** Assert a visible element contains text (case-insensitive substring). */
export async function assertText(page: Page, selector: string, text: string) {
  await expect(page.locator(selector).first()).toContainText(text, {
    ignoreCase: true,
    timeout: 8_000,
  });
}

/** Wait for any loading spinners / skeleton screens to disappear. */
export async function waitForLoad(page: Page) {
  await page.waitForLoadState('networkidle', { timeout: 15_000 });
  // Dismiss any lingering spinners
  await page.waitForFunction(
    () => document.querySelectorAll('.spin, [data-loading="true"]').length === 0,
    { timeout: 10_000 }
  ).catch(() => {/* spinners optional */});
}

/** Format a large number with commas the same way the UI does. */
export function fmtNumber(n: number): string {
  return n.toLocaleString('en-US');
}
