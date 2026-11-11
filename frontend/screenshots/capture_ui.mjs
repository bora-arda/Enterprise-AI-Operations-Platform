/**
 * Capture the Iris redesign for review.
 *
 * Usage (with the dev server on :3000):
 *   node screenshots/capture_ui.mjs
 */

import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const outDir = here;
mkdirSync(outDir, { recursive: true });

const BASE = 'http://localhost:3000';
const browser = await chromium.launch();

async function setTheme(page, theme, selector = '.nav-shell--desktop .theme-toggle') {
  const current = await page.evaluate(() => document.documentElement.dataset.theme);
  if (current === theme) return;
  await page.locator(selector).first().click();
  await page.waitForFunction(
    (next) => document.documentElement.dataset.theme === next,
    theme
  );
  await page.waitForTimeout(180);
}

async function login(page) {
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.getByLabel('Email').fill('manager@example.com');
  await page.getByLabel('Password', { exact: true }).fill('demo123');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForSelector('h1.page-title', { timeout: 15000 });
  await page.locator('.toast__close').click({ timeout: 1200 }).catch(() => {});
  await page.waitForTimeout(500);
}

async function shot(page, name, fullPage = true) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(420);
  await page.screenshot({ path: resolve(outDir, name), fullPage });
  console.log(`wrote ${name}`);
}

try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
  });
  const page = await context.newPage();

  // ----- Login, light + dark -----
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await shot(page, 'login-light.png');

  await setTheme(page, 'dark', '.login-toolbar .theme-toggle');
  await shot(page, 'login-dark.png');

  await setTheme(page, 'light', '.login-toolbar .theme-toggle');
  await login(page);

  // ----- Landing, light -----
  await shot(page, 'home-light.png');

  // ----- Approvals, light -----
  await page.getByRole('link', { name: /Pending approvals/ }).click();
  await page.waitForSelector('h1.page-title');
  await page.waitForTimeout(700);
  await shot(page, 'approvals-light.png');

  await page.locator('.table-request__title').first().click();
  await page.waitForSelector('.approval-drawer');
  await shot(page, 'approval-detail-light.png', false);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // ----- Chat, light -----
  await page.getByRole('link', { name: 'Chat' }).click();
  await page.waitForSelector('.chat-window');
  await shot(page, 'chat-empty-light.png', false);

  await page
    .getByRole('button', { name: 'Which invoices are overdue?' })
    .click();
  await page.locator('.typing-bubble').waitFor({ state: 'hidden', timeout: 120000 }).catch(() => {});
  await page.locator('.bubble--assistant').last().waitFor({
    state: 'visible',
    timeout: 120000,
  });
  await page.waitForTimeout(600);
  await shot(page, 'chat-light.png', false);

  await page.getByRole('button', { name: /History/ }).click();
  await page.locator('.chat-history-panel').waitFor({ timeout: 10000 });
  await shot(page, 'chat-history-light.png', false);
  await page.getByRole('button', { name: 'Close chat history' }).click();

  // ----- Chat, dark, with a real API answer -----
  await setTheme(page, 'dark');
  await page.getByRole('button', { name: 'New chat' }).click();
  await page.waitForSelector('.chat-empty');
  await page
    .getByRole('button', { name: 'What changed in spending from 2024 to 2025?' })
    .click();
  await page.locator('.typing-bubble').waitFor({ state: 'hidden', timeout: 120000 }).catch(() => {});
  await page.locator('.bubble--assistant').last().waitFor({
    state: 'visible',
    timeout: 120000,
  });
  await page.waitForTimeout(600);
  await shot(page, 'chat-dark.png', false);

  // ----- Landing and approvals, dark -----
  await page.getByRole('link', { name: 'Home', exact: true }).click();
  await page.waitForSelector('h1.page-title');
  await shot(page, 'home-dark.png');

  await page.getByRole('link', { name: /Pending approvals/ }).click();
  await page.waitForSelector('h1.page-title');
  await page.waitForTimeout(500);
  await shot(page, 'approvals-dark.png');

  await context.close();

  // ----- Mobile pass -----
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  const phone = await mobile.newPage();
  await login(phone);
  await shot(phone, 'mobile-home.png');

  await phone.getByRole('button', { name: 'Open menu' }).click();
  await phone.waitForSelector('.nav-shell--drawer');
  await shot(phone, 'mobile-menu.png', false);
  await phone.getByRole('link', { name: /Pending approvals/ }).click();
  await phone.waitForSelector('h1.page-title');
  await phone.waitForTimeout(600);
  await shot(phone, 'mobile-approvals.png');

  await phone.getByRole('button', { name: 'Open menu' }).click();
  await phone.waitForSelector('.nav-shell--drawer');
  await phone.getByRole('link', { name: 'Chat' }).click();
  await phone.waitForSelector('.chat-window');
  await phone.getByRole('button', { name: 'Which invoices are overdue?' }).click();
  await phone.locator('.typing-bubble').waitFor({ state: 'hidden', timeout: 120000 }).catch(() => {});
  await phone.locator('.bubble--assistant').last().waitFor({
    state: 'visible',
    timeout: 120000,
  });
  await phone.waitForTimeout(600);
  await shot(phone, 'mobile-chat.png', false);

  await mobile.close();

  const loginMobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  const loginPhone = await loginMobile.newPage();
  await loginPhone.goto(BASE, { waitUntil: 'networkidle' });
  await loginPhone.evaluate(() => document.fonts.ready);
  await shot(loginPhone, 'mobile-login.png');
  await loginMobile.close();
} finally {
  await browser.close();
}
