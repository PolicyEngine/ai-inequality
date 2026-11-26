import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

// On a 375px phone screen, every health-coverage chart's tooltip shows the
// shift the pointer or the arrow keys chose, and neither the tooltip box nor
// its text runs past the screen's edges.
const WIDTH = 375;

test.use({ viewport: { width: WIDTH, height: 812 } });

const shiftLabel = (shift) => (shift === 0 ? "Baseline" : `${shift}% shift`);

async function charts(page) {
  await page.goto(appUrl("/policy-analysis"));
  const surfaces = page.locator("section.health-coverage svg.recharts-surface");
  await expect(surfaces).toHaveCount(3);
  // Recharts draws the axes once the chart has measured its width; wait for
  // each chart's six x-axis ticks, 0% to 100%. Recharts 3 draws tick labels
  // in their own layer, outside the axis's group, so their text finds them.
  for (let i = 0; i < 3; i += 1) {
    await expect(
      surfaces
        .nth(i)
        .locator(".recharts-cartesian-axis-tick-value")
        .filter({ hasText: /^\d+%$/ }),
    ).toHaveCount(6);
  }
  return surfaces;
}

// The tooltip's edges, and how far its text runs past its box, once Recharts
// has stopped moving it. Recharts slides the tooltip over 400ms and moves it
// again once it has measured new text, so this reads only when no transition
// runs and three frames in a row give the same edges.
function settledEdges(tooltip) {
  return tooltip.evaluate(async (wrapper) => {
    const box = wrapper.querySelector(".recharts-default-tooltip");
    const frame = () =>
      new Promise((resolve) => requestAnimationFrame(resolve));
    const running = () => wrapper.getAnimations({ subtree: true });
    const read = () => {
      const outer = wrapper.getBoundingClientRect();
      const inner = box.getBoundingClientRect();
      return JSON.stringify({
        wrapper: [outer.left, outer.right],
        box: [inner.left, inner.right],
        overflow: box.scrollWidth - box.clientWidth,
      });
    };
    let last = "";
    let same = 0;
    for (let i = 0; i < 300; i += 1) {
      // A transition Recharts retargets ends cancelled, which rejects.
      await Promise.all(running().map((a) => a.finished.catch(() => {})));
      await frame();
      const now = read();
      same = now === last && running().length === 0 ? same + 1 : 0;
      last = now;
      if (same === 2) return JSON.parse(now);
    }
    throw new Error("The tooltip never stopped moving.");
  });
}

async function expectTooltip(surface, label) {
  const wrapper = surface.locator(
    "xpath=ancestor::div[contains(@class,'recharts-wrapper')]",
  );
  const tooltip = wrapper.locator(".recharts-tooltip-wrapper");
  const title = tooltip.locator(
    ".recharts-default-tooltip .recharts-tooltip-label",
  );
  await expect(tooltip).toBeVisible();
  await expect(title).toHaveText(label);
  const edges = await settledEdges(tooltip);
  for (const [left, right] of [edges.wrapper, edges.box]) {
    expect(left).toBeGreaterThanOrEqual(0);
    expect(right).toBeLessThanOrEqual(WIDTH);
  }
  // No line of text runs past the box.
  expect(edges.overflow).toBe(0);
  // Still the chosen shift once it has settled.
  await expect(title).toHaveText(label);
}

// Where to point at one shift, relative to the chart: over the x-axis tick
// for that shift, at the plot's middle height, kept 1px inside the plot's
// left edge and 2px inside its right edge. Read in one pass, so a smooth
// scroll between reads can't shift one box against the other.
function pointAt(surface, shift) {
  return surface.evaluate((svg, value) => {
    const chart = svg.getBoundingClientRect();
    const plot = svg
      .querySelector(".recharts-cartesian-grid")
      .getBoundingClientRect();
    const tick = [
      ...svg.querySelectorAll(".recharts-cartesian-axis-tick-value"),
    ].find((node) => node.textContent.trim() === `${value}%`);
    const at = tick.getBoundingClientRect();
    const x = Math.min(
      Math.max(at.left + at.width / 2, plot.left + 1),
      plot.right - 2,
    );
    return { x: x - chart.left, y: plot.top + plot.height / 2 - chart.top };
  }, shift);
}

test("tooltips show the hovered shift and stay on screen", async ({ page }) => {
  const surfaces = await charts(page);
  for (let i = 0; i < 3; i += 1) {
    const surface = surfaces.nth(i);
    await surface.scrollIntoViewIfNeeded();
    for (const shift of [20, 60, 100]) {
      await surface.hover({ position: await pointAt(surface, shift) });
      await expectTooltip(surface, shiftLabel(shift));
    }
  }
});

test("tooltips show the keyed shift and stay on screen", async ({ page }) => {
  const surfaces = await charts(page);
  for (let i = 0; i < 3; i += 1) {
    const surface = surfaces.nth(i);
    await surface.focus();
    await expectTooltip(surface, shiftLabel(0));
    for (let shift = 10; shift <= 100; shift += 10) {
      await surface.press("ArrowRight");
      await expectTooltip(surface, shiftLabel(shift));
    }
  }
});
