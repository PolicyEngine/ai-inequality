import { cloneElement } from "react";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import AIScenarios from "../components/AIScenarios";
import IncomeDistributionBreakdown from "../components/IncomeDistributionBreakdown";
import ShiftSweep from "../components/ShiftSweep";
import sweepData from "../data/shiftSweepData.json";
import { TEXT } from "./kitTheme";

// jsdom gives ResponsiveContainer no size, so Recharts draws no legend there.
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

// Each legend entry's name, the colour it's written in and its swatch's
// accessible name.
function legendEntries() {
  return [...document.querySelectorAll(".recharts-legend-item")].map((item) => {
    const text = item.querySelector(".recharts-legend-item-text");
    return {
      name: text.textContent,
      colour: text.style.color,
      swatch: item.querySelector("svg").getAttribute("aria-label"),
    };
  });
}

function expectInkAndNames(entries) {
  expect(entries.length).toBeGreaterThan(0);
  for (const entry of entries) {
    expect(entry.colour).toBe(TEXT.muted);
    expect(entry.swatch).toBe(`${entry.name} legend icon`);
  }
}

describe("chart legends", () => {
  it("write the sweep's band names in ink, with plain swatch names", () => {
    render(
      <MemoryRouter>
        <ShiftSweep sweepData={sweepData} />
      </MemoryRouter>,
    );
    fireEvent.click(
      screen.getByRole("radio", { name: /net government revenue change/i }),
    );
    expectInkAndNames(legendEntries());
  });

  it("write the income components' names in ink, with plain swatch names", () => {
    render(<IncomeDistributionBreakdown />);
    expectInkAndNames(legendEntries());
  });

  it("write the AI scenarios' series names in ink, with plain swatch names", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expectInkAndNames(legendEntries());
  });
});

// Recharts writes each tooltip row in its series' colour unless the Tooltip
// sets itemStyle, so every Tooltip in the site's chart code takes the kit's.
describe("chart tooltips", () => {
  const ROOT = process.cwd();
  const DIRS = ["src/components", "src/charts", "src/views"];
  const files = DIRS.flatMap((dir) =>
    readdirSync(join(ROOT, dir))
      .filter((name) => /\.jsx$/.test(name) && !/\.test\./.test(name))
      .map((name) => join(dir, name)),
  );

  it("each set the kit's label and item styles", () => {
    const missing = files.flatMap((path) => {
      const code = readFileSync(join(ROOT, path), "utf8");
      const tooltips = [...code.matchAll(/<Tooltip\b[\s\S]*?\/>/g)].map(
        (match) => match[0],
      );
      return tooltips
        .filter(
          (tag) =>
            !tag.includes("{...TOOLTIP_PROPS}") &&
            !(tag.includes("itemStyle=") && tag.includes("labelStyle=")),
        )
        .map((tag) => `${path}: ${tag.slice(0, 60)}`);
    });
    expect(missing).toEqual([]);
  });
});
