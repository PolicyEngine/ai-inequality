import { cloneElement } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import sweepData from "../data/shiftSweepData.json";
import ShiftSweep from "./ShiftSweep";

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

function legend(chart) {
  return [...chart.querySelectorAll(".recharts-legend-item-text")]
    .map((node) => node.textContent)
    .sort();
}

// The outline of each band's area, in the order the chart stacks them.
function bandOutlines(chart) {
  return [...chart.querySelectorAll(".recharts-area-area")].map(
    (node) => node.getAttribute("d") ?? "",
  );
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
  for (const outline of outlines) expect(outline).toMatch(/\d/);
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
  for (const outline of outlines) expect(outline).toMatch(/\d/);
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
  // Teal gains, orange loses.
  const fills = [...ranking.querySelectorAll(".recharts-rectangle")].map(
    (node) => node.getAttribute("fill"),
  );
  expect(fills).toEqual(
    withHealth.map((code) =>
      deltas[code].state_net_change_b >= 0 ? "#227773" : "#DD6B20",
    ),
  );
});
