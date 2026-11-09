/**
 * Capture the provisioned Grafana dashboard.
 *
 * Usage (with Grafana on :3001):
 *   GRAFANA_ADMIN_PASSWORD=admin node capture_grafana.mjs ../docs/assets
 */

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const outDir = resolve(process.argv[2] || "../docs/assets");
mkdirSync(outDir, { recursive: true });

const password = process.env.GRAFANA_ADMIN_PASSWORD || "admin";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1680 } });

try {
  await page.goto("http://localhost:3001/login", {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });

  await page.locator('input[name="user"]').fill("admin");
  await page.locator('input[name="password"]').fill(password);
  await page.locator('button[type="submit"]').click();

  // Dismiss optional first-login prompts (change password / welcome)
  await page.waitForTimeout(3000);
  for (const name of [/skip/i, /no thanks/i, /later/i]) {
    const button = page.getByRole("button", { name });
    if ((await button.count()) > 0) {
      await button.first().click().catch(() => {});
    }
  }

  await page.goto("http://localhost:3001/d/procurement-overview", {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForTimeout(10000); // allow panels to query Prometheus

  await page.screenshot({
    path: resolve(outDir, "grafana-dashboard.png"),
    fullPage: true,
  });

  console.log(`Grafana screenshot written to ${outDir}`);
} finally {
  await browser.close();
}
