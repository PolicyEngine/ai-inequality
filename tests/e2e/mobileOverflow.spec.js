import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

// On a 375px phone screen the policy-analysis page never scrolls sideways,
// whichever measure, income concept, view, unit, shift or jurisdiction the
// reader picks, and with the benchmark tables open.
const WIDTH = 375;

test.use({ viewport: { width: WIDTH, height: 812 } });

// How wide the page is once React and Recharts have drawn the current state.
async function expectFits(page, state) {
  const { scrollWidth, clientWidth } = await page.evaluate(async () => {
    const frame = () =>
      new Promise((resolve) => requestAnimationFrame(resolve));
    await frame();
    await frame();
    const root = document.documentElement;
    return { scrollWidth: root.scrollWidth, clientWidth: root.clientWidth };
  });
  expect(clientWidth).toBe(WIDTH);
  expect
    .soft(
      scrollWidth,
      `${state}: the page is ${scrollWidth}px wide on a ${clientWidth}px screen`,
    )
    .toBeLessThanOrEqual(clientWidth);
}

// Click each option of every tab group and radio group outside the sweep's
// measure picker, measuring the page after each click.
async function visitEveryOption(page, prefix) {
  const groups = page.locator(
    "[role=radiogroup]:not([aria-label='Measure']), [role=tablist]",
  );
  const groupCount = await groups.count();
  for (let g = 0; g < groupCount; g += 1) {
    const group = groups.nth(g);
    const name = await group.getAttribute("aria-label");
    const options = group.locator("[role=radio], [role=tab]");
    const optionCount = await options.count();
    expect(optionCount).toBeGreaterThan(1);
    for (let o = 0; o < optionCount; o += 1) {
      const option = options.nth(o);
      const label = (await option.textContent()).trim();
      await option.click();
      await expect(option).toHaveAttribute(
        (await option.getAttribute("role")) === "tab"
          ? "aria-selected"
          : "aria-checked",
        "true",
      );
      await expectFits(page, `${prefix} / ${name}: ${label}`);
    }
  }
}

test("the policy-analysis page fits a 375px screen in every state", async ({
  page,
}) => {
  await page.goto(appUrl("/policy-analysis"));

  // The page has drawn: both tables, the sweep's measure picker and a chart.
  // count() doesn't wait, so wait for the first measure before counting.
  const measures = page.locator(
    "#shift-sweep [role=radiogroup][aria-label='Measure'] [role=radio]",
  );
  await expect(measures.first()).toBeVisible();
  expect(await measures.count()).toBeGreaterThan(1);
  await expect(page.locator("table.baseline-distribution-table")).toBeVisible();
  await expect(
    page.locator("#shift-sweep svg.recharts-surface").first(),
  ).toBeVisible();
  await expectFits(page, "On load");

  // Open the benchmark tables.
  const benchmarks = page.locator("details.income-benchmark-disclosure");
  await benchmarks.locator("summary").click();
  await expect(benchmarks).toHaveAttribute("open", "");
  await expect(page.locator("table.income-benchmark-table")).toBeVisible();
  await expectFits(page, "Benchmarks open");

  const measureCount = await measures.count();
  for (let m = 0; m < measureCount; m += 1) {
    const measure = measures.nth(m);
    const label = (await measure.textContent()).trim();
    await measure.click();
    await expect(measure).toHaveAttribute("aria-checked", "true");
    await expect(
      page.locator("#shift-sweep svg.recharts-surface").first(),
    ).toBeVisible();
    await expectFits(page, `Measure: ${label}`);
    await visitEveryOption(page, `Measure: ${label}`);

    const jurisdiction = page.locator("#jurisdiction-select");
    if (await jurisdiction.isVisible()) {
      const values = await jurisdiction
        .locator("option")
        .evaluateAll((nodes) => nodes.map((node) => node.value));
      expect(values.length).toBeGreaterThan(1);
      for (const value of values) {
        await jurisdiction.selectOption(value);
        await expectFits(page, `Measure: ${label} / Jurisdiction: ${value}`);
      }
    }
  }
});
