import { cloneElement } from "react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { BAND_EDGE, GAIN, LOSS, SERIES, TEXT } from "../charts/kitTheme";
import {
  colourDistance,
  tokenHex,
  touchingPairs,
} from "../charts/stackNeighbours";
import sweepData from "../data/shiftSweepData.json";
import ukSweepData from "../data/ukShiftSweepData.json";
import ShiftSweep, { decompositionCharts } from "./ShiftSweep";

// jsdom gives ResponsiveContainer no size, so Recharts draws no bands or bars
// there. A fixed size lets these tests read what the charts draw from the
// site's sweep file, which counts health coverage and TANF.
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    ResponsiveContainer: ({ children, height }) =>
      cloneElement(children, {
        width: 800,
        height: typeof height === "number" ? height : 400,
      }),
  };
});

function renderRevenue() {
  render(
    <MemoryRouter>
      <ShiftSweep sweepData={sweepData} />
    </MemoryRouter>,
  );
  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
}

// The chart Recharts draws under a decomposition heading.
function chartUnder(name) {
  return screen.getByRole("heading", { name }).nextElementSibling;
}

// A decomposition chart draws its legend in its own element, just below the
// chart.
function legendOf(chart) {
  return chart.nextElementSibling;
}

function legend(chart) {
  return [...legendOf(chart).querySelectorAll(".recharts-legend-item-text")]
    .map((node) => node.textContent)
    .sort();
}

// The outline of each band's area, in the order the chart stacks them.
function bandOutlines(chart) {
  return [...chart.querySelectorAll(".recharts-area-area")].map(
    (node) => node.getAttribute("d") ?? "",
  );
}

// The area an outline encloses, in square pixels, by the shoelace formula over
// its points (curve control points included). A band of zeros runs out along
// its top edge and back along the same points, so it encloses none.
function enclosedArea(outline) {
  const points = [...outline.matchAll(/(-?[\d.]+),(-?[\d.]+)/g)].map(
    ([, x, y]) => [Number(x), Number(y)],
  );
  let twice = 0;
  points.forEach(([x1, y1], i) => {
    const [x2, y2] = points[(i + 1) % points.length];
    twice += x1 * y2 - x2 * y1;
  });
  return Math.abs(twice) / 2;
}

test("the federal chart draws a health band for a run that counts health coverage", () => {
  renderRevenue();
  const chart = chartUnder(/federal revenue decomposition/i);
  expect(legend(chart)).toEqual([
    "Federal benefits other than TANF (negated)",
    "Federal health coverage (negated)",
    "Net (sum of components)",
    "Net federal income tax (after refundable credits)",
    "Payroll tax (employee + employer + self-employment)",
  ]);
  const outlines = bandOutlines(chart);
  expect(outlines).toHaveLength(4);
  // Every band, health included, has amounts to draw.
  for (const outline of outlines)
    expect(enclosedArea(outline)).toBeGreaterThan(1);
});

test("a state's chart draws its TANF and health bands", () => {
  renderRevenue();
  fireEvent.change(screen.getByLabelText(/jurisdiction/i), {
    target: { value: "CA" },
  });
  const chart = chartUnder(/ca state revenue decomposition/i);
  expect(legend(chart)).toEqual([
    "Net (sum of components)",
    "Net state income tax (after refundable credits)",
    "State benefits other than TANF (negated)",
    "State health coverage (negated)",
    "TANF (negated)",
  ]);
  const outlines = bandOutlines(chart);
  expect(outlines).toHaveLength(4);
  for (const outline of outlines)
    expect(enclosedArea(outline)).toBeGreaterThan(1);
});

test("the state ranking orders states by their net change with health coverage and TANF", () => {
  renderRevenue();
  const ranking = screen
    .getByRole("heading", { name: /state revenue exposure at 50% shift/i })
    .closest(".shift-sweep-state-exposure");
  const deltas = Object.fromEntries(
    Object.entries(
      sweepData.scenarios.find((scenario) => scenario.shift_pct === 50)
        .state_deltas,
    ),
  );
  const order = (field) =>
    Object.keys(deltas).sort((a, b) => deltas[b][field] - deltas[a][field]);
  const withHealth = order("state_net_change_b");
  // The ranking without health and TANF differs, so the test can tell them apart.
  expect(order("state_net_excluding_health_tanf_change_b")).not.toEqual(
    withHealth,
  );
  // The y-axis labels, top to bottom; Recharts draws them in a layer apart
  // from the axis, so read every label that names a state.
  const drawn = [...ranking.querySelectorAll("svg text")]
    .map((node) => node.textContent)
    .filter((text) => text in deltas);
  expect(drawn).toEqual(withHealth);
  // Teal gains, gray loses: the kit's gain and loss tokens.
  const fills = [...ranking.querySelectorAll(".recharts-rectangle")].map(
    (node) => node.getAttribute("fill"),
  );
  expect(fills).toEqual(
    withHealth.map((code) =>
      deltas[code].state_net_change_b >= 0 ? GAIN : LOSS,
    ),
  );
});

// Each legend entry's colour, by name, from the swatch Recharts draws beside
// it, and each band's fill in the order the chart stacks them.
function legendColours(chart) {
  return Object.fromEntries(
    [...legendOf(chart).querySelectorAll(".recharts-legend-item")].map(
      (item) => [
        item.textContent,
        item.querySelector("path")?.getAttribute("stroke"),
      ],
    ),
  );
}

function bandFills(chart) {
  return [...chart.querySelectorAll(".recharts-area-area")].map((node) =>
    node.getAttribute("fill"),
  );
}

test("bands take the kit's series colours, and a state's match the federal chart's", () => {
  renderRevenue();
  const federalChart = chartUnder(/federal revenue decomposition/i);
  expect(bandFills(federalChart)).toEqual(SERIES.slice(0, 4));
  const federal = legendColours(federalChart);
  fireEvent.change(screen.getByLabelText(/jurisdiction/i), {
    target: { value: "CA" },
  });
  const stateChart = chartUnder(/ca state revenue decomposition/i);
  expect(bandFills(stateChart)).toEqual(SERIES.slice(0, 4));
  const state = legendColours(stateChart);
  expect(state["Net state income tax (after refundable credits)"]).toBe(
    federal["Net federal income tax (after refundable credits)"],
  );
  expect(state["State benefits other than TANF (negated)"]).toBe(
    federal["Federal benefits other than TANF (negated)"],
  );
  expect(state["State health coverage (negated)"]).toBe(
    federal["Federal health coverage (negated)"],
  );
  expect(federal["Net (sum of components)"]).toBe(TEXT.primary);
});

const KIT_TOKENS = readFileSync(
  join(process.cwd(), "node_modules/@policyengine/ui-kit/src/theme/tokens.css"),
  "utf8",
);
const distance = (a, b) =>
  colourDistance(tokenHex(KIT_TOKENS, a), tokenHex(KIT_TOKENS, b));

// Bands meet wherever the data stacks them next to each other, which is not
// only where they sit next to each other in the bucket list: a band near zero
// lets the two either side of it touch.
test("bands that touch never share a colour, and each band draws an edge between close ones", () => {
  const close = [];
  for (const data of [sweepData, ukSweepData]) {
    for (const chart of decompositionCharts(data)) {
      const keys = chart.buckets.map((bucket) => bucket.key);
      for (const [a, b] of touchingPairs(chart.rows, keys)) {
        expect(SERIES[a]).not.toBe(SERIES[b]);
        if (distance(SERIES[a], SERIES[b]) < 15) {
          close.push(`${chart.name}: ${keys[a]} / ${keys[b]}`);
        }
      }
    }
  }
  // The kit has no four series colours that all clear a ΔE of 15 against each
  // other, and the data puts close ones together: TANF on health coverage in
  // Alaska's chart, for one.
  expect(close).toContain("AK: rev_state_tanf / rev_state_health");

  // So every band draws BAND_EDGE along its outer edge, and the legend keeps
  // each band's fill as its swatch.
  renderRevenue();
  fireEvent.change(screen.getByLabelText(/jurisdiction/i), {
    target: { value: "AK" },
  });
  const chart = chartUnder(/ak state revenue decomposition/i);
  const edges = [...chart.querySelectorAll(".recharts-area-curve")];
  expect(edges).toHaveLength(4);
  for (const edge of edges) {
    expect(edge.getAttribute("stroke")).toBe(BAND_EDGE.stroke);
    expect(edge.getAttribute("stroke-width")).toBe(
      String(BAND_EDGE.strokeWidth),
    );
  }
  expect(bandFills(chart)).toEqual(SERIES.slice(0, 4));
  const swatches = legendColours(chart);
  expect(
    [
      "Net state income tax (after refundable credits)",
      "TANF (negated)",
      "State benefits other than TANF (negated)",
      "State health coverage (negated)",
    ].map((name) => swatches[name]),
  ).toEqual(SERIES.slice(0, 4));
});
