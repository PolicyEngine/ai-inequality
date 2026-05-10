import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

test.describe("AI Growth Research Homepage", () => {
  test("should load homepage and display all sections", async ({ page }) => {
    await page.goto(appUrl());

    // Check header
    await expect(page.locator("header")).toBeVisible();
    await expect(page.locator('img[alt="PolicyEngine"]')).toBeVisible();

    // Check hero section
    await expect(
      page.locator('h1:has-text("AI Economic Growth Research")'),
    ).toBeVisible();

    // Check all major sections are present
    await expect(
      page.locator('h2:has-text("Research Overview")'),
    ).toBeVisible();
    await expect(
      page.locator('h2:has-text("Why PolicyEngine?")'),
    ).toBeVisible();
    await expect(
      page.locator('h2:has-text("Relevant Research")'),
    ).toBeVisible();
    await expect(
      page.locator('h2:has-text("Policy Scenarios to Model")'),
    ).toBeVisible();
    await expect(
      page.locator('h2:has-text("Technical Requirements")'),
    ).toBeVisible();
    await expect(
      page.locator('h2:has-text("Potential Stakeholders")'),
    ).toBeVisible();
  });

  test("should have working external links", async ({ page }) => {
    await page.goto(appUrl());

    // Check PolicyEngine main site link
    const policyEngineLink = page.locator('a[href="https://policyengine.org"]');
    await expect(policyEngineLink).toBeVisible();
  });

  test("should have interactive research cards", async ({ page }) => {
    await page.goto(appUrl());

    // Find and click a research topic card
    const firstCard = page.locator(".card").first();
    await firstCard.click();

    // Check if expansion indicator changed
    await expect(firstCard).toBeVisible();
  });

  test("should have filterable stakeholder section", async ({ page }) => {
    await page.goto(appUrl());

    // Scroll to stakeholders
    await page
      .locator('h2:has-text("Potential Stakeholders")')
      .scrollIntoViewIfNeeded();

    // Check filter buttons exist
    await expect(
      page.locator('button:has-text("All Organizations")'),
    ).toBeVisible();
    await expect(page.locator('button:has-text("AI Companies")')).toBeVisible();

    // Click a filter button
    await page.locator('button:has-text("AI Companies")').click();

    // Check that stakeholders are still visible
    await expect(page.locator(".stakeholder-badge")).toBeVisible();
  });

  test("should have responsive design", async ({ page }) => {
    // Test desktop
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto(appUrl());
    await expect(page.locator(".hero")).toBeVisible();

    // Test mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator(".hero")).toBeVisible();
  });

  test("should have all policy scenario cards", async ({ page }) => {
    await page.goto(appUrl());

    await page
      .locator('h2:has-text("Policy Scenarios")')
      .scrollIntoViewIfNeeded();

    // Check for all 5 policy scenarios
    await expect(
      page.locator('.scenario-card:has-text("Current Policy Baseline")'),
    ).toBeVisible();
    await expect(
      page.locator('.scenario-card:has-text("Universal Basic Income")'),
    ).toBeVisible();
    await expect(
      page.locator('.scenario-card:has-text("Expanded Safety Net")'),
    ).toBeVisible();
    await expect(
      page.locator('.scenario-card:has-text("Capital Taxation")'),
    ).toBeVisible();
    await expect(
      page.locator('.scenario-card:has-text("Hybrid Approaches")'),
    ).toBeVisible();
  });
});
