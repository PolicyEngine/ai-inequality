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

// The state tax note's change, as the component words it.
function stateTaxMoveOf(name, variant) {
  const row = scenariosData.scenarios.find(
    (r) => r.name === name && r.inequality === variant && !r.holdSharesFixed,
  );
  const verb = row.stateTaxChange >= 0 ? "rise" : "fall";
  return `${verb} by $${Math.abs(row.stateTaxChange).toFixed(0)}B`;
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

  it("names the selected wage variant in the state tax note", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expect(document.body.textContent).toContain(
      `Under rapid adoption with proportional wage changes, we estimate state income and use taxes before refundable credits ${stateTaxMoveOf("Rapid", "proportional")}.`,
    );
    fireEvent.click(screen.getByRole("radio", { name: "Wages spread" }));
    expect(document.body.textContent).toContain(
      `Under rapid adoption with wages spreading, we estimate state income and use taxes before refundable credits ${stateTaxMoveOf("Rapid", "expansive")}.`,
    );
    expect(document.body.textContent).not.toMatch(/proportional wage changes/);
    fireEvent.click(screen.getByRole("radio", { name: "Slow" }));
    fireEvent.click(screen.getByRole("radio", { name: "Wages compress" }));
    expect(document.body.textContent).toContain(
      `Under slow adoption with wages compressing, we estimate state income and use taxes before refundable credits ${stateTaxMoveOf("Slow", "compressive")}.`,
    );
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

  it("handles the committed payload without error", async () => {
    const { default: data } = await import("../data/aiScenariosData.json");
    const breakeven = realizationBreakeven(data.sensitivities.realization);
    expect(breakeven).toBeGreaterThan(0.2);
    expect(breakeven).toBeLessThan(0.26);
  });
});
