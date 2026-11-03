/**
 * Capture demo screenshots from the running frontend (authenticated).
 *
 * Usage (from the frontend directory, with the dev server on :3000):
 *   node capture_screenshots.mjs ../docs/assets
 */

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const outDir = resolve(process.argv[2] || "../docs/assets");
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

try {
  await page.goto("http://localhost:3000", {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });

  // Login as a manager (can see pending approvals)
  await page.getByRole("heading", { name: "Procurement AI Platform" }).waitFor({
    timeout: 30000,
  });
  await page.locator('input[type="email"]').fill("manager@example.com");
  await page.locator('input[type="password"]').fill("demo123");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page
    .locator("h2", { hasText: "Pending Approvals" })
    .waitFor({ state: "visible", timeout: 30000 });

  const input = page.locator('input[type="text"]');
  await input.fill("Why is invoice INV-000010 overdue?");
  await page.getByRole("button", { name: "Send" }).click();

  // Wait for the assistant response, not the user message or loading state
  await page
    .getByText("It is linked to purchase order", { exact: false })
    .first()
    .waitFor({ timeout: 60000 });
  await page.waitForTimeout(500);

  await page.screenshot({
    path: resolve(outDir, "chat-investigation.png"),
    fullPage: true,
  });

  const panel = page.locator("section.approvals");
  if ((await panel.count()) > 0) {
    await panel.screenshot({
      path: resolve(outDir, "approvals-panel.png"),
    });
  }

  console.log(`Screenshots written to ${outDir}`);
} finally {
  await browser.close();
}
