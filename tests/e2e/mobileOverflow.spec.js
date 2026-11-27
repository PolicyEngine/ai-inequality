import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

// On a 375px phone screen the policy-analysis page, in its US and UK
// versions, is never wider than the screen, whichever measure, income
// concept, view, unit, shift or jurisdiction the reader picks, and with the
// benchmark tables open.
const WIDTH = 375;

test.use({ viewport: { width: WIDTH, height: 812 } });

// What each version of the page offers. The test checks that it visited
// these, so it fails instead of passing on fewer states if one stops
// rendering.
const VERSIONS = [
  {
    name: "US",
    path: "/policy-analysis",
    benchmarks: true,
    groups: ["Income concept", "View", "Shift percentage"],
    jurisdictions: true,
  },
  {
    name: "UK",
    path: "/policy-analysis?country=uk",
    benchmarks: false,
    groups: ["Income concept", "Units", "Shift percentage"],
    jurisdictions: false,
  },
];

// How wide the page is once React and Recharts have drawn the current state.
async function expectFits(page, state) {
  const { innerWidth, scrollWidth, clientWidth } = await page.evaluate(
    async () => {
      const frame = () =>
        new Promise((resolve) => requestAnimationFrame(resolve));
      await frame();
      await frame();
      const root = document.documentElement;
      return {
        innerWidth: window.innerWidth,
        scrollWidth: root.scrollWidth,
        clientWidth: root.clientWidth,
      };
    },
  );
  expect(innerWidth).toBe(WIDTH);
  expect
    .soft(
      scrollWidth,
      `${state}: the page is ${scrollWidth}px wide on a ${clientWidth}px screen`,
    )
    .toBeLessThanOrEqual(clientWidth);
}

// Click each option of every tab group and radio group outside the sweep's
// measure picker, measuring the page after each click, and note each group.
async function visitEveryOption(page, prefix, seen) {
  const groups = page.locator(
    "[role=radiogroup]:not([aria-label='Measure']), [role=tablist]",
  );
  const groupCount = await groups.count();
  for (let g = 0; g < groupCount; g += 1) {
    const group = groups.nth(g);
    const name = await group.getAttribute("aria-label");
    seen.add(name);
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

for (const version of VERSIONS) {
  test(`the ${version.name} policy-analysis page fits a 375px screen in every state`, async ({
    page,
  }) => {
    // About 110 states on the US page; CI drew them in about 16 seconds.
    test.setTimeout(90 * 1000);
    await page.goto(appUrl(version.path));

    // The page has drawn: the sweep's measure picker, the baseline table and
    // a sweep chart. count() doesn't wait, so wait for the first measure
    // before counting.
    const measures = page.locator(
      "#shift-sweep [role=radiogroup][aria-label='Measure'] [role=radio]",
    );
    await expect(measures.first()).toBeVisible();
    expect(await measures.count()).toBeGreaterThan(1);
    await expect(
      page.locator("table.baseline-distribution-table"),
    ).toBeVisible();
    await expect(
      page.locator("#shift-sweep svg.recharts-surface").first(),
    ).toBeVisible();
    await expectFits(page, "On load");

    // Open the benchmark tables, which only the US page has.
    const benchmarks = page.locator("details.income-benchmark-disclosure");
    await expect(benchmarks).toHaveCount(version.benchmarks ? 1 : 0);
    if (version.benchmarks) {
      await benchmarks.locator("summary").click();
      await expect(benchmarks).toHaveAttribute("open", "");
      await expect(page.locator("table.income-benchmark-table")).toBeVisible();
      await expectFits(page, "Benchmarks open");
    }

    const seen = new Set();
    let jurisdictionsVisited = 0;
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
      await visitEveryOption(page, `Measure: ${label}`, seen);

      const jurisdiction = page.locator("#jurisdiction-select");
      if ((await jurisdiction.count()) > 0) {
        const values = await jurisdiction
          .locator("option")
          .evaluateAll((nodes) => nodes.map((node) => node.value));
        expect(values.length).toBeGreaterThan(1);
        for (const value of values) {
          await jurisdiction.selectOption(value);
          await expectFits(page, `Measure: ${label} / Jurisdiction: ${value}`);
          jurisdictionsVisited += 1;
        }
      }
    }

    expect([...seen]).toEqual(expect.arrayContaining(version.groups));
    expect(jurisdictionsVisited > 0).toBe(version.jurisdictions);
  });
}
