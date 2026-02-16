import { test, expect } from "@playwright/test";

test.describe("Image Loading", () => {
  test("should load all project card images", async ({ page }) => {
    await page.goto("/");

    // Wait for example projects section
    await page.locator("#examples").waitFor();

    // Get all project images
    const projectImages = page.locator(".project-image");
    const count = await projectImages.count();

    expect(count).toBe(6); // Should have 6 project cards

    // Check each image loads successfully
    for (let i = 0; i < count; i++) {
      const img = projectImages.nth(i);

      // Wait for image to be visible
      await expect(img).toBeVisible();

      // Check image loaded (naturalWidth > 0)
      const isLoaded = await img.evaluate((el) => {
        return el.complete && el.naturalWidth > 0;
      });

      expect(isLoaded).toBe(true);
    }
  });

  test("should have no broken images on page", async ({ page }) => {
    await page.goto("/");

    // Wait for page to fully load
    await page.waitForLoadState("networkidle");

    // Get all images on page
    const allImages = page.locator("img");
    const count = await allImages.count();

    let brokenImages = [];

    for (let i = 0; i < count; i++) {
      const img = allImages.nth(i);
      const src = await img.getAttribute("src");

      const isLoaded = await img.evaluate((el) => {
        return el.complete && el.naturalWidth > 0;
      });

      if (!isLoaded) {
        brokenImages.push(src);
      }
    }

    expect(brokenImages).toEqual([]);
  });

  test("should have correct PUBLIC_URL paths", async ({ page }) => {
    await page.goto("/");

    // Check project images use correct base path
    const firstProjectImg = page.locator(".project-image").first();
    const src = await firstProjectImg.getAttribute("src");

    // Should include /images/ path
    expect(src).toContain("/images/");
  });
});
