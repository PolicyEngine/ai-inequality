import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

// On a 375px phone screen, every health-coverage chart's tooltip stays inside
// the screen, whether a pointer hovers the chart or the keyboard steps
// through it.
const WIDTH = 375;

test.use({ viewport: { width: WIDTH, height: 812 } });

async function charts(page) {
  await page.goto(appUrl("/policy-analysis"));
  const surfaces = page.locator("section.health-coverage svg.recharts-surface");
  await expect(surfaces).toHaveCount(3);
  return surfaces;
}

async function expectTooltipOnScreen(page, surface) {
  const wrapper = surface.locator(
    "xpath=ancestor::div[contains(@class,'recharts-wrapper')]",
  );
  const tooltip = wrapper.locator(".recharts-tooltip-wrapper");
  await expect(tooltip).toBeVisible();
  // Recharts slides the box into place; wait for it to settle.
  await page.waitForTimeout(500);
  const box = await tooltip.boundingBox();
  expect(box).not.toBeNull();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(WIDTH);
}

test("tooltips stay on screen on hover", async ({ page }) => {
  const surfaces = await charts(page);
  for (let i = 0; i < 3; i += 1) {
    const surface = surfaces.nth(i);
    // The page scrolls smoothly, so hover() places the pointer once the
    // chart stops moving; only the chart's size is read here.
    const { width, height } = await surface.boundingBox();
    // Near the 10%, 50% and 100% shifts, across the plot.
    for (const share of [0.3, 0.6, 0.95]) {
      await surface.hover({ position: { x: width * share, y: height / 2 } });
      await expectTooltipOnScreen(page, surface);
    }
  }
});

test("tooltips stay on screen on keyboard focus", async ({ page }) => {
  const surfaces = await charts(page);
  for (let i = 0; i < 3; i += 1) {
    const surface = surfaces.nth(i);
    await surface.focus();
    for (let step = 0; step < 10; step += 1) {
      await surface.press("ArrowRight");
      await expectTooltipOnScreen(page, surface);
    }
  }
});
