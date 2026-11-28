import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

// Every axis title on the study's charts stays inside its chart, in each state
// the chart controls reach, for both countries. Recharts' "insideLeft"
// position anchors a rotated y-axis title at its start, at the axis's middle,
// so a long title runs up past the chart's top edge unless the chart anchors
// it at its middle.
//
// At desktop width the spec checks every title. At phone width it checks the
// rotated y-axis titles: some horizontal x-axis titles are wider than a phone
// chart, which a wrapped title would fix.
const PAGES = [
  { page: "/income-shift", country: "us" },
  { page: "/income-shift", country: "uk" },
  { page: "/policy-analysis", country: "us" },
  { page: "/policy-analysis", country: "uk" },
];
const WIDTHS = [
  { width: 1280, rotatedOnly: false },
  { width: 375, rotatedOnly: true },
];

// Each chart title's text and how far it runs past its chart's edges, for the
// charts on screen. Recharts draws a chart only once it has measured its
// width, so a chart still at zero width has no titles yet.
function readTitles(rotatedOnly) {
  const titles = [];
  for (const chart of document.querySelectorAll("svg.recharts-surface")) {
    const edges = chart.getBoundingClientRect();
    if (edges.width === 0) continue;
    for (const title of chart.querySelectorAll("text.recharts-label")) {
      const rotated = /rotate/.test(title.getAttribute("transform") ?? "");
      if (rotatedOnly && !rotated) continue;
      const box = title.getBoundingClientRect();
      const past = {
        top: edges.top - box.top,
        right: box.right - edges.right,
        bottom: box.bottom - edges.bottom,
        left: edges.left - box.left,
      };
      titles.push({
        text: title.textContent,
        past: Object.entries(past)
          .filter(([, px]) => px > 1)
          .map(([edge, px]) => `${edge} by ${Math.round(px)}px`),
      });
    }
  }
  return titles;
}

// The titles every state must show before the spec measures it, so a state
// whose charts haven't drawn yet can't pass with nothing to check.
const SWEEP_TITLE = /income shifted to capital/;
const DECILE_TITLE = /decile-total net income|mean household net income/;

async function expectTitlesInside(page, { rotatedOnly, state, revenue }) {
  await expect
    .poll(
      async () => {
        const titles = await page.evaluate(readTitles, rotatedOnly);
        const texts = titles.map(({ text }) => text);
        if (!rotatedOnly && !texts.some((text) => SWEEP_TITLE.test(text))) {
          return ["the sweep chart hasn't drawn its titles"];
        }
        if (revenue && !texts.some((text) => DECILE_TITLE.test(text))) {
          return ["the decile chart hasn't drawn its titles"];
        }
        if (texts.length === 0) return ["no chart has drawn its titles"];
        return titles
          .filter(({ past }) => past.length > 0)
          .map(
            ({ text, past }) => `"${text}" runs past the ${past.join(", ")}`,
          );
      },
      { message: state, timeout: 10_000 },
    )
    .toEqual([]);
}

const radios = (page, group) =>
  page.getByRole("radiogroup", { name: group, exact: true }).getByRole("radio");

async function choose(page, group, name) {
  const radio = page
    .getByRole("radiogroup", { name: group, exact: true })
    .getByRole("radio", { name, exact: true });
  await radio.click();
  await expect(radio).toHaveAttribute("aria-checked", "true");
}

for (const { width, rotatedOnly } of WIDTHS) {
  test.describe(`at ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    for (const { page: path, country } of PAGES) {
      test(`${path} (${country}) keeps each axis title inside its chart`, async ({
        page,
      }) => {
        test.setTimeout(180_000);
        const query = country === "us" ? "" : `?country=${country}`;
        await page.goto(appUrl(`${path}${query}`));
        await expect(radios(page, "Measure").first()).toBeVisible();

        const where = `${path} (${country}) at ${width}px`;
        const measures = await radios(page, "Measure").allTextContents();
        expect(measures.length).toBeGreaterThan(0);
        for (const measure of measures) {
          await choose(page, "Measure", measure);
          const revenue = /revenue/i.test(measure);
          if (!revenue) {
            // Each income concept the measure offers, or the measure alone.
            const concepts = await radios(
              page,
              "Income concept",
            ).allTextContents();
            for (const concept of concepts.length ? concepts : [null]) {
              if (concept) await choose(page, "Income concept", concept);
              await expectTitlesInside(page, {
                rotatedOnly,
                revenue,
                state: `${where}: ${measure}${concept ? `, ${concept}` : ""}`,
              });
            }
            continue;
          }
          // Revenue: each unit, at the national level and for one state.
          const units = await radios(page, "Units").allTextContents();
          for (const unit of units.length ? units : [null]) {
            if (unit) await choose(page, "Units", unit);
            const select = page.locator("#jurisdiction-select");
            const jurisdictions = (await select.count())
              ? (
                  await select
                    .locator("option")
                    .evaluateAll((options) =>
                      options.map((option) => option.value),
                    )
                ).slice(0, 2)
              : [null];
            for (const jurisdiction of jurisdictions) {
              if (jurisdiction) await select.selectOption(jurisdiction);
              await expectTitlesInside(page, {
                rotatedOnly,
                revenue,
                state: `${where}: ${measure}, ${unit ?? "dollars"}, ${jurisdiction ?? "national"}`,
              });
            }
            if (jurisdictions.length > 1)
              await select.selectOption(jurisdictions[0]);
          }
        }
      });
    }
  });
}
