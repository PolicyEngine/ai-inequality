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
import { GRID_STYLE, TEXT } from "./kitTheme";

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

// Recharts draws axis lines, tick marks and tick text in #666 unless an axis
// sets them, so every axis takes the kit's settings through AXIS_PROPS: tick
// text and axis titles in muted ink, axis lines in the grid's colour and no
// tick marks.
const all = (selector) => [...document.querySelectorAll(selector)];
const KIT_PAINT = /^(none|var\(--[\w-]+\))$/;

// The colour an element paints: an inline style wins over the attribute, as
// it does in the browser. Recharts writes fill="#808080" on every axis title,
// and the kit's style covers it.
function paint(element, prop) {
  const style = element.getAttribute("style") ?? "";
  const match = style.match(new RegExp(`(?:^|;)\\s*${prop}:\\s*([^;]+)`));
  return match ? match[1].trim() : element.getAttribute(prop);
}

function expectKitAxes() {
  const lines = all(".recharts-cartesian-axis-line");
  const ticks = all(".recharts-cartesian-axis-tick-value");
  const titles = all(".recharts-label");
  expect(lines.length).toBeGreaterThan(0);
  expect(ticks.length).toBeGreaterThan(0);
  expect(titles.length).toBeGreaterThan(0);
  for (const line of lines)
    expect(paint(line, "stroke")).toBe(GRID_STYLE.stroke);
  expect(all(".recharts-cartesian-axis-tick-line")).toHaveLength(0);
  for (const tick of ticks) expect(paint(tick, "fill")).toBe(TEXT.muted);
  for (const title of titles) expect(paint(title, "fill")).toBe(TEXT.muted);
  // Nothing else in an axis paints a colour of its own.
  const painted = [
    ...all(".recharts-cartesian-axis, .recharts-cartesian-axis *"),
    ...ticks,
  ].flatMap((element) =>
    ["stroke", "fill"]
      .map((prop) => paint(element, prop))
      .filter((value) => value !== null && !KIT_PAINT.test(value)),
  );
  expect(painted).toEqual([]);
}

describe("chart axes", () => {
  it("draw the sweep's axes in the kit's colours", () => {
    render(
      <MemoryRouter>
        <ShiftSweep sweepData={sweepData} />
      </MemoryRouter>,
    );
    fireEvent.click(
      screen.getByRole("radio", { name: /net government revenue change/i }),
    );
    expectKitAxes();
  });

  it("draw the income components' axes in the kit's colours", () => {
    render(<IncomeDistributionBreakdown />);
    expectKitAxes();
  });

  it("draw the AI scenarios' axes in the kit's colours", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expectKitAxes();
  });

  // The renders above reach some of each file's charts; this reaches every
  // axis in the site's chart code.
  it("each take the kit's axis props", () => {
    const ROOT = process.cwd();
    const files = ["src/components", "src/charts", "src/views"].flatMap((dir) =>
      readdirSync(join(ROOT, dir))
        .filter((name) => /\.jsx$/.test(name) && !/\.test\./.test(name))
        .map((name) => join(dir, name)),
    );
    const axes = files.flatMap((path) =>
      [
        ...readFileSync(join(ROOT, path), "utf8").matchAll(
          /<(?:XAxis|YAxis)\b[\s\S]*?\/>/g,
        ),
      ].map((match) => [path, match[0]]),
    );
    expect(axes.length).toBeGreaterThan(0);
    const missing = axes
      .filter(
        ([, tag]) =>
          !tag.includes("{...AXIS_PROPS}") &&
          !(tag.includes("axisLine=") && tag.includes("tickLine={false}")),
      )
      .map(([path, tag]) => `${path}: ${tag.slice(0, 60)}`);
    expect(missing).toEqual([]);
  });
});
