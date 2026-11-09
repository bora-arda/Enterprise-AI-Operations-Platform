/**
 * Verify the session-ID fix and Markdown table rendering in the Dockerized UI.
 *
 * Usage (stack running on :3000):
 *   node verify_demo_fix.mjs ../docs/assets
 */

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const outDir = resolve(process.argv[2] || "../docs/assets");
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });

async function login(email, password = "demo123") {
  await page.goto("http://localhost:3000", {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page
    .locator("h2", { hasText: "Pending Approvals" })
    .waitFor({ state: "visible", timeout: 30000 });
  return page.evaluate(() => localStorage.getItem("procurement_session"));
}

async function logout() {
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.locator('input[type="email"]').waitFor({ timeout: 30000 });
}

async function ask(question, expectedText) {
  const input = page.locator('input[type="text"]');
  await input.fill(question);
  await page.getByRole("button", { name: "Send" }).click();
  await page
    .getByText(expectedText, { exact: false })
    .first()
    .waitFor({ timeout: 60000 });
  await page.waitForTimeout(500);
  return page.evaluate(() => document.querySelectorAll("table").length);
}

try {
  const managerSession = await login("manager@example.com");
  await logout();

  const specialistSession = await login("specialist@example.com");
  await logout();

  const managerSession2 = await login("manager@example.com");

  const tablesForPending = await ask(
    "which payment requests are pending?",
    "Pending payment requests"
  );

  const tablesForApprovals = await ask(
    "list me all pending payments and approvals",
    "Pending approvals"
  );

  const tablesForFollowUp = await ask(
    "list me with each of them detailed as a table",
    "Pending approvals"
  );

  await page.screenshot({
    path: resolve(outDir, "chat-pending-requests.png"),
    fullPage: true,
  });

  console.log(
    JSON.stringify(
      {
        managerSession,
        specialistSession,
        managerSession2,
        sessionIsolated:
          Boolean(managerSession) &&
          Boolean(specialistSession) &&
          managerSession !== specialistSession,
        tablesForPending,
        tablesForApprovals,
        tablesForFollowUp,
      },
      null,
      2
    )
  );
} finally {
  await browser.close();
}
