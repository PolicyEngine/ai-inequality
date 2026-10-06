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

    // Challenge
    await page.locator(".challenge-section").screenshot({
      path: "test-results/screenshots/challenge.png",
    });

    // Approach
    await page.locator(".approach-section").screenshot({
      path: "test-results/screenshots/approach.png",
    });

    // Example projects
    await page.locator("#examples").screenshot({
      path: "test-results/screenshots/examples.png",
    });

    // Ecosystem
    await page.locator("#ecosystem").screenshot({
      path: "test-results/screenshots/ecosystem.png",
    });
  });
});
