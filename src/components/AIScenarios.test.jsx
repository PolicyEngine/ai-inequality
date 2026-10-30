import React from "react";
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AIScenarios, { realizationBreakeven } from "./AIScenarios";
import scenariosData from "../data/aiScenariosData.json";

// Derive expected strings from the committed payload so a data-build refresh
// changes the numbers without breaking the tests. This mirrors the
// component's own formatter.
const fmtBillions = (value) =>
  `${value >= 0 ? "+" : "\u2212"}$${Math.abs(value).toFixed(0)}B`;

function revenueOf(name, variant) {
  const row = scenariosData.scenarios.find(
    (r) => r.name === name && r.inequality === variant && !r.holdSharesFixed,
  );
  return fmtBillions(row.revenueChange);
}

describe("AIScenarios", () => {
  it("renders the section with scenario and variant controls", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expect(
      screen.getByText("What forecasters expect, under current law"),
    ).toBeTruthy();
    expect(screen.getByRole("radio", { name: "Rapid" })).toBeTruthy();
    expect(screen.getByRole("radio", { name: "Proportional" })).toBeTruthy();
  });

  it("defaults to Rapid / proportional and shows its revenue", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expect(
      screen.getAllByText(revenueOf("Rapid", "proportional")).length,
    ).toBeGreaterThan(0);
  });

  it("states the survey inputs the payload was run on", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    // Rapid: 3.3% growth, labor share to 52.0% (revised 9 October 2026).
    expect(
      screen.getByText(/assumes 3\.3% annual real GDP growth/),
    ).toBeTruthy();
    expect(screen.getByText(/labor share falling to 52\.0%/)).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "Moderate" }));
    expect(screen.getByText(/labor share falling to 54\.0%/)).toBeTruthy();
  });

  it("describes the realization sweep the payload actually shows", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    const unrealized = scenariosData.sensitivities.realization.find(
      (row) => row.realizationRate === 0,
    );
    expect(
      screen.getByText(
        new RegExp(
          `to \\${fmtBillions(unrealized.revenueChange).replace("$", "\\$")} if none of it does`,
        ),
      ),
    ).toBeTruthy();
    expect(screen.queryByText(/turns negative below the breakeven/)).toBeNull();
  });

  it("states the capital-scope cut from the payload", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    const full = scenariosData.scenarios.find(
      (r) =>
        r.name === "Rapid" &&
        r.inequality === "proportional" &&
        !r.holdSharesFixed,
    ).revenueChange;
    const excl =
      scenariosData.sensitivities.capital_scope_excluding_retirement.find(
        (r) => r.name === "Rapid",
      ).revenueChange;
    const cut = Math.round((100 * (full - excl)) / full);
    expect(
      screen.getByText(
        new RegExp(
          `cuts the Rapid estimate by ${cut}% and turns Slow negative`,
        ),
      ),
    ).toBeTruthy();
  });

  it("labels the state-tax figure with the selected variant", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("radio", { name: "Wages spread" }));
    const expansive = scenariosData.scenarios.find(
      (r) =>
        r.name === "Rapid" &&
        r.inequality === "expansive" &&
        !r.holdSharesFixed,
    );
    expect(
      screen.getByText(
        new RegExp(
          `Under Rapid / expansive, state income tax is \\${fmtBillions(expansive.stateTaxChange).replace("$", "\\$")}`,
        ),
      ),
    ).toBeTruthy();
  });

  it("links the October revision notice to the write-up", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    const link = screen.getByRole("link", { name: "the write-up" });
    expect(link.getAttribute("href")).toBe("/budget-lab");
  });

  it("switches scenario when a tab is clicked", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("radio", { name: "Slow" }));
    expect(
      screen.getAllByText(revenueOf("Slow", "proportional")).length,
    ).toBeGreaterThan(0);
  });

  it("shows the crossover wage only for spread variants", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expect(screen.queryByText(/workers earning below/i)).toBeNull();
    fireEvent.click(screen.getByRole("radio", { name: "Wages spread" }));
    expect(screen.getByText(/workers earning below/i)).toBeTruthy();
  });

  it("carries the corporate-tax scope note from the payload", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expect(screen.getByText(/no corporate income tax/i)).toBeTruthy();
  });

  it("cites the model and data build", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expect(screen.getByText(/populace_us_2024/)).toBeTruthy();
  });
});

describe("realizationBreakeven", () => {
  it("interpolates the zero crossing", () => {
    const rows = [
      { realizationRate: 0, revenueChange: -60 },
      { realizationRate: 0.25, revenueChange: 5 },
      { realizationRate: 1, revenueChange: 205 },
    ];
    // Crosses zero between 0 and 0.25: 60 / 65 of the way.
    expect(realizationBreakeven(rows)).toBeCloseTo(0.25 * (60 / 65), 5);
  });

  it("returns null when revenue never crosses zero", () => {
    expect(
      realizationBreakeven([
        { realizationRate: 0, revenueChange: 10 },
        { realizationRate: 1, revenueChange: 200 },
      ]),
    ).toBeNull();
  });

  it("finds no crossing in the committed payload", async () => {
    // On the Budget Lab's revised inputs Rapid labor income grows, so revenue
    // stays positive even at a 0% realized share. (On the July inputs it
    // crossed zero near 22.5%.)
    const { default: data } = await import("../data/aiScenariosData.json");
    const rows = data.sensitivities.realization;
    expect(realizationBreakeven(rows)).toBeNull();
    const unrealized = rows.find((row) => row.realizationRate === 0);
    expect(unrealized.revenueChange).toBeGreaterThan(0);
  });
});
