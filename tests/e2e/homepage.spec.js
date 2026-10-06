import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

test.describe("AI Growth Research Homepage", () => {
  test("loads the homepage and displays current sections", async ({ page }) => {
    await page.goto(appUrl());

    await expect(page.locator("main")).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: /how will policy shape ai's impact on inequality/i,
      }),
    ).toBeVisible();

    for (const section of [
      "The challenge",
      "Our approach",
      "What PolicyEngine does",
      "What the research shows",
      "The ecosystem",
      "Get involved",
      "Dive deeper",
    ]) {
      await expect(page.getByRole("heading", { name: section })).toBeVisible();
    }
  });

  test("has working external links", async ({ page }) => {
    await page.goto(appUrl());

    await expect(
      page.locator('a[href="https://github.com/PolicyEngine"]'),
    ).toBeVisible();
    await expect(
      page
        .locator(
          'a[href="https://digitaleconomy.stanford.edu/publications/canaries-in-the-coal-mine/"]',
        )
        .first(),
    ).toBeVisible();
  });

  test("has project cards linking to PolicyEngine work", async ({ page }) => {
    await page.goto(appUrl());

    const firstCard = page.locator(".project-card").first();
    await expect(firstCard).toBeVisible();
    await expect(firstCard).toHaveAttribute(
      "href",
      /policyengine\.org\/us\/research/,
    );
  });

  test("shows the ecosystem section", async ({ page }) => {
    await page.goto(appUrl());

    await page
      .getByRole("heading", { name: "The ecosystem" })
      .scrollIntoViewIfNeeded();

    for (const category of [
      "Research & academia",
      "AI companies",
      "Policy & advocacy",
      "Models & tools",
      "Funders & forecasting",
    ]) {
      await expect(page.getByRole("heading", { name: category })).toBeVisible();
    }
    await expect(page.locator(".ecosystem-org-card")).toHaveCount(27);
  });

  test("has responsive hero layout", async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto(appUrl());
    await expect(page.locator(".hero")).toBeVisible();

    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator(".hero")).toBeVisible();
  });

  test("links to deeper pages from the homepage", async ({ page }) => {
    await page.goto(appUrl());

    await expect(
      page.getByRole("link", { name: /income-shift experiment/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /research context/i }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /references/i })).toBeVisible();
  });
});
