import { test } from "@playwright/test";
import { appUrl } from "./basePath";

test.describe("Visual Inspection", () => {
  test("capture full page screenshot - desktop", async ({ page }) => {
    await page.goto(appUrl());
    await page.screenshot({
      path: "test-results/screenshots/full-page-desktop.png",
      fullPage: true,
    });
  });

  test("capture full page screenshot - mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(appUrl());
    await page.screenshot({
      path: "test-results/screenshots/full-page-mobile.png",
      fullPage: true,
    });
  });

  test("capture individual sections", async ({ page }) => {
    await page.goto(appUrl());

    // Hero
    await page.locator(".hero").screenshot({
      path: "test-results/screenshots/hero.png",
    });

    // Overview
    await page.locator("#overview").screenshot({
      path: "test-results/screenshots/overview.png",
    });

    // Capabilities
    await page.locator("#capabilities").screenshot({
      path: "test-results/screenshots/capabilities.png",
    });

    // Policy Scenarios
    await page.locator("#scenarios").screenshot({
      path: "test-results/screenshots/scenarios.png",
    });

    // Stakeholders
    await page.locator("#stakeholders").screenshot({
      path: "test-results/screenshots/stakeholders.png",
    });
  });
});
