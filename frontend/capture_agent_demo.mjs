/**
 * Capture the current agent-first demo screens from the local frontend.
 *
 * Usage (frontend dev server on :3000):
 *   node capture_agent_demo.mjs ../docs/assets
 */

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const outDir = resolve(process.argv[2] || "../docs/assets");
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();

async function login(page) {
  await page.goto("http://localhost:3000", {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  await page.locator('input[type="email"]').fill("manager@example.com");
  await page.locator('input[type="password"]').fill("demo123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page
    .locator("h2", { hasText: "Pending Approvals" })
    .waitFor({ state: "visible", timeout: 30000 });
}

async function ask(page, question) {
  const before = await page.locator(".message.assistant").count();
  await page.locator('input[type="text"]').fill(question);
  await page.getByRole("button", { name: "Send" }).click();
  await page
    .locator(".message.assistant.loading")
    .waitFor({ state: "hidden", timeout: 120000 })
    .catch(() => {});
  await page
    .locator(".message.assistant")
    .nth(before)
    .waitFor({ state: "visible", timeout: 120000 });
  await page.waitForTimeout(800);
}

async function screenshot(page, name) {
  // The chat panel normally scrolls internally. Expand it for a full-page
  // documentation screenshot so the answer is not clipped.
  await page.addStyleTag({
    content:
      ".chat-container{height:auto !important;} .messages{overflow:visible !important;}",
  });
  await page.screenshot({
    path: resolve(outDir, name),
    fullPage: true,
  });
  console.log(`wrote ${name}`);
}

try {
  const investigation = await browser.newPage({
    viewport: { width: 1280, height: 900 },
  });
  await login(investigation);
  await ask(investigation, "Why is invoice INV-000010 overdue?");
  await screenshot(investigation, "chat-investigation.png");
  await investigation.close();

  const exceptions = await browser.newPage({
    viewport: { width: 1280, height: 900 },
  });
  await login(exceptions);
  await ask(exceptions, "anomalies and exceptions");
  await screenshot(exceptions, "chat-agent-anomalies.png");
  await ask(
    exceptions,
    "show me the top 5 invoices that exceed PO, with vendor and contract details",
  );
  await screenshot(exceptions, "chat-agent-exception-detail.png");
  await exceptions.close();

  const focus = await browser.newPage({
    viewport: { width: 1280, height: 900 },
  });
  await login(focus);
  await ask(focus, "what should I focus on this week?");
  await screenshot(focus, "chat-agent-focus.png");
  await focus.close();

  console.log(`agent-first screenshots written to ${outDir}`);
} finally {
  await browser.close();
}
