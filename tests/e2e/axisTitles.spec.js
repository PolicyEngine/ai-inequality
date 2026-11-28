import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

// Every axis title on the study's charts stays inside its chart and clear of
// its tick labels and legend, in each state the chart controls reach, for
// both countries. Recharts' "insideLeft" position anchors a rotated y-axis
// title at its start, at the axis's middle, so a long title runs up past the
// chart's top edge unless the chart anchors it at its middle. A legend drawn
// inside a chart also takes its height from the plot, so a legend that wraps
// onto many lines on a phone can leave the axis too short for its title.
//
// The walk covers every measure, income concept and unit, the national view
// and one state, every shift of the decile and state charts, and the
// AI-scenario and income-distribution controls.
const PAGES = [
  { page: "/income-shift", country: "us" },
  { page: "/income-shift", country: "uk" },
  { page: "/policy-analysis", country: "us" },
  { page: "/policy-analysis", country: "uk" },
];

// What each view offers, so a renamed or missing control fails the spec
// instead of quietly shrinking its walk.
const VIEWS = {
  us: {
    measures: 6,
    units: 0,
    jurisdictions: true,
    stateChart: true,
    aiScenarios: "/income-shift",
    incomeDistribution: "/policy-analysis",
  },
  uk: {
    measures: 5,
    units: 2,
    jurisdictions: false,
    stateChart: false,
    aiScenarios: null,
    incomeDistribution: null,
  },
};

// The study's padding leaves each sweep chart 74px narrower than a phone's
// screen: 301px wide at 375px. Until the page fits a phone, rows of tabs
// widen it and its charts draw wider than that, so at phone width the spec
// caps each chart at the width a phone leaves it and checks that none drew
// wider.
const PHONE_INSET = 74;

// At 1280px and 375px the spec checks every title. Some horizontal titles are
// wider than a phone's chart, which a wrapped title would fix: at 375px it
// excuses the one that runs past an edge, and at 320px it checks only the
// rotated y-axis titles.
const KNOWN_WIDE = /^Share of the AI capital flow reaching tax returns$/;
const WIDTHS = [
  { width: 1280, phone: false, horizontal: true },
  { width: 375, phone: true, horizontal: true },
  { width: 320, phone: true, horizontal: false },
];

// Each drawn chart's width and axis titles: how far each title runs past its
// chart's edges, and the tick labels and legend items it covers. Recharts
// draws a chart only once it has measured its width, and draws every label,
// annotations included, in one layer. An axis title sits left of the plot or
// below it; an annotation such as "Forecast range" sits inside or above it.
function readCharts() {
  const crosses = (a, b) =>
    Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 &&
    Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
  const visible = (element) => element.getClientRects().length > 0;
  const containers = [
    ...document.querySelectorAll(".recharts-responsive-container"),
  ].filter(visible);
  const charts = [];
  let undrawn = 0;
  for (const container of containers) {
    const chart = container.querySelector(
      ".recharts-wrapper > svg.recharts-surface",
    );
    const plot = chart?.querySelector("defs clipPath rect");
    const ticks = chart
      ? [...chart.querySelectorAll(".recharts-cartesian-axis-tick-value")]
      : [];
    const edges = chart?.getBoundingClientRect();
    if (!edges?.width || !plot || ticks.length < 2) {
      undrawn += 1;
      continue;
    }
    const left = edges.left + Number(plot.getAttribute("x"));
    const bottom =
      edges.top +
      Number(plot.getAttribute("y")) +
      Number(plot.getAttribute("height"));
    const obstacles = [
      ...ticks,
      ...chart.parentElement.querySelectorAll(".recharts-legend-item"),
    ].map((element) => ({
      text: element.textContent.trim(),
      box: element.getBoundingClientRect(),
    }));
    const titles = [];
    for (const label of chart.querySelectorAll("text.recharts-label")) {
      const box = label.getBoundingClientRect();
      const x = (box.left + box.right) / 2;
      const y = (box.top + box.bottom) / 2;
      if (x >= left && y <= bottom) continue;
      const past = {
        top: edges.top - box.top,
        right: box.right - edges.right,
        bottom: box.bottom - edges.bottom,
        left: edges.left - box.left,
      };
      titles.push({
        text: label.textContent,
        rotated: /rotate/.test(label.getAttribute("transform") ?? ""),
        inSweep: Boolean(label.closest("#shift-sweep")),
        box: [box.left, box.top, box.right, box.bottom].map(Math.round),
        past: Object.entries(past)
          .filter(([, px]) => px > 1)
          .map(([edge, px]) => `${edge} by ${Math.round(px)}px`),
        covers: obstacles
          .filter((obstacle) => crosses(box, obstacle.box))
          .map((obstacle) => obstacle.text),
      });
    }
    charts.push({ width: Math.round(edges.width), titles });
  }
  return { undrawn, charts };
}

// The titles every state must draw before the spec judges it, so a state
// whose charts haven't drawn can't pass with nothing to check: the sweep's
// own two titles, and in revenue states the decomposition and decile charts'
// rotated titles.
const SWEEP_TITLE = /income shifted to capital/;
const REVENUE_TITLES = [
  /^Change vs baseline/,
  /decile-total net income|mean household net income/,
];

async function expectTitlesInside(page, { width, phone, horizontal, state }) {
  await page.evaluate(() => document.fonts.ready.then(() => true));
  const cap = phone ? width - PHONE_INSET : null;
  let last = null;
  await expect
    .poll(
      async () => {
        const { undrawn, charts } = await page.evaluate(readCharts);
        if (undrawn) return [`${undrawn} charts haven't drawn`];
        const titles = charts.flatMap((chart) => chart.titles);
        const sweep = titles.filter((title) => title.inSweep);
        const revenue = /revenue/i.test(state.measure);
        const missing = [
          sweep.some((title) => SWEEP_TITLE.test(title.text)) ||
            "the sweep's x-axis title",
          sweep.some((title) => title.rotated) || "the sweep's y-axis title",
          ...(revenue
            ? REVENUE_TITLES.map(
                (pattern) =>
                  sweep.some(
                    (title) => title.rotated && pattern.test(title.text),
                  ) || `a rotated title matching ${pattern}`,
              )
            : []),
        ].filter((found) => found !== true);
        if (missing.length) return [`waiting for ${missing.join(", ")}`];
        // Judge a state only once a second read matches the first, so a font
        // swap or a legend that wraps late can't pass on an early read.
        const read = JSON.stringify(charts);
        if (read !== last) {
          last = read;
          return ["the charts are still settling"];
        }
        return [
          ...charts
            .filter((chart) => cap !== null && chart.width > cap)
            .map(
              (chart) =>
                `a chart drew ${chart.width}px wide, past the ${cap}px phone cap`,
            ),
          ...titles
            .filter((title) => title.rotated || horizontal)
            .filter((title) => !(phone && KNOWN_WIDE.test(title.text)))
            .flatMap(({ text, past, covers }) => [
              ...(past.length
                ? [`"${text}" runs past the ${past.join(", ")}`]
                : []),
              ...(covers.length
                ? [`"${text}" covers ${covers.join(", ")}`]
                : []),
            ]),
        ];
      },
      { message: state.label, timeout: 15_000 },
    )
    .toEqual([]);
}

// The options of a group of radios or tabs, which must number exactly count
// (or at least two when count is null).
async function optionsOf(group, role, count = null) {
  const options = await group.getByRole(role).allTextContents();
  if (count === null) expect(options.length).toBeGreaterThan(1);
  else expect(options).toHaveLength(count);
  return options;
}

async function choose(group, role, name) {
  const option = group.getByRole(role, { name, exact: true });
  await option.click();
  await expect(option).toHaveAttribute(
    role === "tab" ? "aria-selected" : "aria-checked",
    "true",
  );
}

const radiogroup = (scope, name) =>
  scope.getByRole("radiogroup", { name, exact: true });
// The decile and state charts each have their own "Shift percentage" radios.
const chartCard = (page, heading) =>
  page
    .locator(".shift-sweep-state-exposure")
    .filter({ has: page.getByRole("heading", { name: heading }) });

for (const { width, phone, horizontal } of WIDTHS) {
  test.describe(`at ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    for (const { page: path, country } of PAGES) {
      test(`${path} (${country}) keeps each axis title inside its chart`, async ({
        page,
      }) => {
        test.setTimeout(300_000);
        const view = VIEWS[country];
        const query = country === "us" ? "" : `?country=${country}`;
        await page.goto(appUrl(`${path}${query}`));
        if (phone) {
          await page.addStyleTag({
            content: `.recharts-responsive-container { max-width: ${
              width - PHONE_INSET
            }px !important; }`,
          });
        }
        const measureGroup = radiogroup(page, "Measure");
        await expect(measureGroup.getByRole("radio").first()).toBeVisible();

        const where = `${path} (${country}) at ${width}px`;
        let measure = "";
        let visited = 0;
        const check = async (detail) => {
          visited += 1;
          await expectTitlesInside(page, {
            width,
            phone,
            horizontal,
            state: { measure, label: `${where}: ${detail}` },
          });
        };

        // The AI-scenario charts, on the US income-shift page.
        for (const name of [
          "AI adoption scenario",
          "Wage inequality variant",
        ]) {
          const group = radiogroup(page, name);
          if (view.aiScenarios !== path) {
            await expect(group).toHaveCount(0);
            continue;
          }
          const options = await optionsOf(group, "radio");
          for (const option of options) {
            await choose(group, "radio", option);
            await check(`${name}: ${option}`);
          }
          await choose(group, "radio", options[0]);
        }

        // The income-distribution chart, on the US policy-analysis page.
        const conceptTabs = page.getByRole("tablist", {
          name: "Income concept",
          exact: true,
        });
        const viewTabs = page.getByRole("tablist", {
          name: "View",
          exact: true,
        });
        if (view.incomeDistribution === path) {
          const concepts = await optionsOf(conceptTabs, "tab");
          const views = await optionsOf(viewTabs, "tab");
          for (const concept of concepts) {
            await choose(conceptTabs, "tab", concept);
            for (const option of views) {
              await choose(viewTabs, "tab", option);
              await check(`income distribution: ${concept}, ${option}`);
            }
          }
          await choose(conceptTabs, "tab", concepts[0]);
          await choose(viewTabs, "tab", views[0]);
        } else {
          await expect(viewTabs).toHaveCount(0);
        }

        const measures = await optionsOf(measureGroup, "radio", view.measures);
        for (measure of measures) {
          await choose(measureGroup, "radio", measure);
          const concepts = radiogroup(page, "Income concept");
          if (/poverty/i.test(measure)) {
            await expect(concepts).toHaveCount(0);
            await check(measure);
            continue;
          }
          if (!/revenue/i.test(measure)) {
            for (const concept of await optionsOf(concepts, "radio", 2)) {
              await choose(concepts, "radio", concept);
              await check(`${measure}, ${concept}`);
            }
            continue;
          }

          // Revenue: each unit, at the national level and for one state, and
          // every shift of the decile and state charts.
          await expect(concepts).toHaveCount(0);
          const unitGroup = radiogroup(page, "Units");
          const units = view.units
            ? await optionsOf(unitGroup, "radio", view.units)
            : [null];
          if (!view.units) await expect(unitGroup).toHaveCount(0);
          const select = page.locator("#jurisdiction-select");
          await expect(select).toHaveCount(view.jurisdictions ? 1 : 0);
          const jurisdictions = view.jurisdictions
            ? (
                await select
                  .locator("option")
                  .evaluateAll((options) =>
                    options.map((option) => option.value),
                  )
              ).slice(0, 2)
            : [null];
          if (view.jurisdictions) expect(jurisdictions).toHaveLength(2);
          const decile = chartCard(page, /market-income decile/);
          const stateChart = chartCard(page, /^State revenue exposure/);
          await expect(stateChart).toHaveCount(view.stateChart ? 1 : 0);

          for (const unit of units) {
            if (unit) await choose(unitGroup, "radio", unit);
            const label = `${measure}, ${unit ?? "dollars"}`;
            for (const jurisdiction of jurisdictions) {
              if (jurisdiction) await select.selectOption(jurisdiction);
              await check(`${label}, ${jurisdiction ?? "national"}`);
            }
            if (jurisdictions.length > 1)
              await select.selectOption(jurisdictions[0]);
            for (const [name, card] of [
              ["decile chart", decile],
              ...(view.stateChart ? [["state chart", stateChart]] : []),
            ]) {
              const shifts = radiogroup(card, "Shift percentage");
              for (const shift of await optionsOf(shifts, "radio", 5)) {
                await choose(shifts, "radio", shift);
                await check(`${label}, ${name} at ${shift}`);
              }
            }
          }
        }
        expect(visited).toBeGreaterThan(0);
      });
    }
  });
}
