import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";
import { UK_PATH, serveUkStudyPath } from "./ukStudyRoute";

// On a 375px phone the policy-analysis page, at its US and UK addresses, is
// never wider than the screen, and no chart's legend squeezes its plot. The
// test measures the page:
// - on load, and with the benchmark tables open;
// - in every combination of the income breakdown's concept and view;
// - under each sweep measure, in every combination of the sweep's own options;
// - for each jurisdiction in the revenue view.
const WIDTH = 375;

// A phone, not a narrow desktop window. Chromium then lays the page out at the
// screen's width only because the page's viewport tag asks it to, as a phone
// does.
test.use({
  viewport: { width: WIDTH, height: 812 },
  isMobile: true,
  hasTouch: true,
  deviceScaleFactor: 2,
});

// Every tab and radio group outside the sweep's measure picker. Each group is
// named by its role, its label and its number of options.
const GROUPS = "[role=radiogroup]:not([aria-label='Measure']), [role=tablist]";

// The groups each version draws, in page order. The income breakdown sits
// outside the sweep and draws the same groups under every measure. The test
// checks the groups and the measures against these, so a group, an option or
// a measure that stops rendering fails it instead of shrinking it.
const BREAKDOWN = ["tablist Income concept 2", "tablist View 3"];
const INEQUALITY = { groups: ["radiogroup Income concept 2"] };
const VERSIONS = [
  {
    name: "US",
    url: appUrl("/policy-analysis"),
    benchmarks: true,
    outside: BREAKDOWN,
    measures: {
      "Gini coefficient": INEQUALITY,
      "Top 10% share": INEQUALITY,
      "Top 1% share": INEQUALITY,
      "Top 0.1% share": INEQUALITY,
      "SPM poverty rate": { groups: [] },
      // The decile chart's shift, then the state exposure chart's. The
      // jurisdictions are federal and 51 states.
      "Net government revenue change": {
        groups: [
          "radiogroup Shift percentage 5",
          "radiogroup Shift percentage 5",
        ],
        jurisdictions: 52,
      },
    },
  },
  {
    // The address policyengine.org serves the UK view at.
    name: "UK",
    url: `${UK_PATH}/policy-analysis`,
    benchmarks: false,
    outside: [],
    measures: {
      "Gini coefficient": INEQUALITY,
      "Top 10% share": INEQUALITY,
      "Top 1% share": INEQUALITY,
      "Top 0.1% share": INEQUALITY,
      "Net government revenue change": {
        groups: ["radiogroup Units 2", "radiogroup Shift percentage 5"],
      },
    },
  },
];

// How wide the page is once React and Recharts have drawn the current state,
// and which charts give their plot less than half their height. A legend
// drawn inside a chart takes its height from the plot.
async function expectFits(page, state) {
  const { innerWidth, scrollWidth, clientWidth, squeezed } =
    await page.evaluate(async () => {
      const frame = () =>
        new Promise((resolve) => requestAnimationFrame(resolve));
      await frame();
      await frame();
      const root = document.documentElement;
      const squeezed = [
        ...document.querySelectorAll("svg.recharts-surface"),
      ].flatMap((chart) => {
        const grid = chart.querySelector(".recharts-cartesian-grid");
        const height = chart.getBoundingClientRect().height;
        if (!grid || height === 0) return [];
        const plot = grid.getBoundingClientRect().height;
        return plot < height / 2
          ? [`a ${Math.round(plot)}px plot in a ${Math.round(height)}px chart`]
          : [];
      });
      return {
        innerWidth: window.innerWidth,
        scrollWidth: root.scrollWidth,
        clientWidth: root.clientWidth,
        squeezed,
      };
    });
  // Soft, so one run lists every failing state.
  expect
    .soft(innerWidth, `${state}: the page lays out ${innerWidth}px wide`)
    .toBe(WIDTH);
  expect
    .soft(
      scrollWidth,
      `${state}: the page is ${scrollWidth}px wide on a ${clientWidth}px screen`,
    )
    .toBeLessThanOrEqual(clientWidth);
  expect.soft(squeezed, `${state}: a legend squeezes its chart`).toEqual([]);
}

// Each group on the page: its place among GROUPS, whether it sits in the
// sweep, and its name.
async function readGroups(page) {
  return page.locator(GROUPS).evaluateAll((nodes) =>
    nodes.map((node, index) => ({
      index,
      sweep: node.closest("#shift-sweep") !== null,
      name: [
        node.getAttribute("role"),
        node.getAttribute("aria-label"),
        node.querySelectorAll("[role=radio], [role=tab]").length,
      ].join(" "),
    })),
  );
}

// Click through every combination of the groups' options, measuring the page
// at each.
async function visitEveryCombination(page, groups, state) {
  if (groups.length === 0) {
    await expectFits(page, state);
    return;
  }
  const [first, ...rest] = groups;
  const group = page.locator(GROUPS).nth(first.index);
  const label = await group.getAttribute("aria-label");
  const selected =
    (await group.getAttribute("role")) === "tablist"
      ? "aria-selected"
      : "aria-checked";
  const options = group.locator("[role=radio], [role=tab]");
  const count = await options.count();
  for (let o = 0; o < count; o += 1) {
    const option = options.nth(o);
    const text = (await option.textContent()).trim();
    await option.click();
    await expect(option).toHaveAttribute(selected, "true");
    await visitEveryCombination(page, rest, `${state} / ${label}: ${text}`);
  }
}

for (const version of VERSIONS) {
  test(`the ${version.name} policy-analysis page fits a 375px phone with every chart option`, async ({
    page,
  }) => {
    // About 100 states on the US page.
    test.setTimeout(150 * 1000);
    const upstreamFailures = [];
    await serveUkStudyPath(page, (upstream, response) => {
      if (![200, 304].includes(response.status())) {
        upstreamFailures.push(`${upstream.pathname}: ${response.status()}`);
      }
    });
    await page.goto(version.url);

    // The page has drawn: the sweep's measure picker, the baseline table and
    // a sweep chart. count() doesn't wait, so wait for the first measure
    // first.
    const measures = page.locator(
      "#shift-sweep [role=radiogroup][aria-label='Measure'] [role=radio]",
    );
    await expect(measures.first()).toBeVisible();
    expect(
      (await measures.allTextContents()).map((text) => text.trim()),
    ).toEqual(Object.keys(version.measures));
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

    // The groups outside the sweep, once.
    const outside = (await readGroups(page)).filter((group) => !group.sweep);
    expect(outside.map((group) => group.name)).toEqual(version.outside);
    await visitEveryCombination(page, outside, "Outside the sweep");

    const jurisdiction = page.locator("#jurisdiction-select");
    for (const [label, expected] of Object.entries(version.measures)) {
      const measure = page
        .locator("#shift-sweep")
        .getByRole("radiogroup", { name: "Measure", exact: true })
        .getByRole("radio", { name: label, exact: true });
      await measure.click();
      await expect(measure).toHaveAttribute("aria-checked", "true");
      await expect(
        page.locator("#shift-sweep svg.recharts-surface").first(),
      ).toBeVisible();

      const groups = await readGroups(page);
      expect(groups.filter((group) => !group.sweep).map((g) => g.name)).toEqual(
        version.outside,
      );
      const sweep = groups.filter((group) => group.sweep);
      expect(sweep.map((group) => group.name)).toEqual(expected.groups);
      await visitEveryCombination(page, sweep, `Measure: ${label}`);

      await expect(jurisdiction).toHaveCount(expected.jurisdictions ? 1 : 0);
      if (!expected.jurisdictions) continue;
      const values = await jurisdiction
        .locator("option")
        .evaluateAll((nodes) => nodes.map((node) => node.value));
      expect(values).toHaveLength(expected.jurisdictions);
      for (const value of values) {
        await jurisdiction.selectOption(value);
        // The chosen jurisdiction's chart, so the check measures it and not
        // the one before.
        await expect(
          page.getByRole("heading", {
            name:
              value === "federal"
                ? "Federal revenue decomposition"
                : `${value} state revenue decomposition`,
            exact: true,
          }),
        ).toBeVisible();
        await expectFits(page, `Measure: ${label} / Jurisdiction: ${value}`);
      }
      await jurisdiction.selectOption(values[0]);
    }

    expect(upstreamFailures).toEqual([]);
  });
}
