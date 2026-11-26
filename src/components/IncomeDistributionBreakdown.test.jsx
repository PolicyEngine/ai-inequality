import { cloneElement } from "react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { BAND_EDGE, GAIN, LOSS, SERIES } from "../charts/kitTheme";
import {
  colourDistance,
  tokenHex,
  touchingPairs,
} from "../charts/stackNeighbours";
import incomeDistributionData from "../data/incomeDistributionData.json";
import IncomeDistributionBreakdown, {
  SEGMENT_COLOURS,
  chartRows,
} from "./IncomeDistributionBreakdown";

// jsdom gives ResponsiveContainer no size and Recharts grows bars from zero
// over an animation, so the chart draws nothing to read without these.
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    ResponsiveContainer: ({ children, height }) =>
      cloneElement(children, { width: 800, height }),
    Bar: (props) => <actual.Bar {...props} isAnimationActive={false} />,
  };
});

test("switches income distribution breakdown between concepts and views", () => {
  render(<IncomeDistributionBreakdown />);

  expect(
    screen.getByRole("heading", { name: /current income distribution/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /market income/i })).toHaveClass(
    "active",
  );
  expect(document.body).toHaveTextContent(/measured capital income/i);
  expect(document.body).toHaveTextContent(
    /benchmark capital-income concentration/i,
  );
  expect(document.body).toHaveTextContent(/IRS Statistics of Income/i);

  fireEvent.click(screen.getByRole("tab", { name: /net income/i }));
  expect(document.body).toHaveTextContent(/taxes before refundable credits/i);

  fireEvent.click(screen.getByRole("tab", { name: /share of total/i }));
  expect(document.body).toHaveTextContent(/national total income/i);
});

test("segments take kit colours by key, never the data file's", () => {
  expect(SEGMENT_COLOURS.taxes).toBe(LOSS);
  expect(SEGMENT_COLOURS.benefits).toBe(GAIN);
  for (const conceptKey of ["market", "net"]) {
    const components = incomeDistributionData[conceptKey].components;
    const colours = components.map((c) => SEGMENT_COLOURS[c.key]);
    for (const colour of colours) {
      expect([...SERIES, GAIN, LOSS]).toContain(colour);
    }
    // Every segment in a concept has its own colour.
    expect(new Set(colours).size).toBe(colours.length);
  }

  render(<IncomeDistributionBreakdown />);
  fireEvent.click(screen.getByRole("tab", { name: /net income/i }));
  const swatches = [...document.querySelectorAll(".income-component-swatch")];
  expect(swatches.map((node) => node.getAttribute("style"))).toEqual(
    incomeDistributionData.net.components.map(
      (c) => `background: ${SEGMENT_COLOURS[c.key]};`,
    ),
  );
});

const KIT_TOKENS = readFileSync(
  join(process.cwd(), "node_modules/@policyengine/ui-kit/src/theme/tokens.css"),
  "utf8",
);
const distance = (a, b) =>
  colourDistance(tokenHex(KIT_TOKENS, a), tokenHex(KIT_TOKENS, b));

// Segments meet wherever the data stacks them next to each other: refundable
// credits are too small to keep market income off benefits, and in the bottom
// 10%, whose total is negative, market income and taxes share a side.
test("segments that touch never share a colour, and each segment draws an edge", () => {
  const close = [];
  for (const conceptKey of ["market", "net"]) {
    const keys = incomeDistributionData[conceptKey].components.map(
      (c) => c.key,
    );
    for (const viewKey of ["composition", "absolute", "shareOfTotal"]) {
      const rows = chartRows(conceptKey, viewKey);
      for (const [a, b] of touchingPairs(rows, keys)) {
        const [colourA, colourB] = [keys[a], keys[b]].map(
          (key) => SEGMENT_COLOURS[key],
        );
        expect(colourA).not.toBe(colourB);
        if (distance(colourA, colourB) < 15) {
          close.push(`${viewKey}: ${keys[a]} / ${keys[b]}`);
        }
      }
    }
  }
  // No four kit colours clear a ΔE of 15 against each other.
  expect(close).toContain("absolute: market / benefits");

  render(<IncomeDistributionBreakdown />);
  fireEvent.click(screen.getByRole("tab", { name: /net income/i }));
  const segments = [...document.querySelectorAll("path.recharts-rectangle")];
  expect(segments.length).toBeGreaterThan(0);
  for (const segment of segments) {
    expect(segment.getAttribute("stroke")).toBe(BAND_EDGE.stroke);
    expect(segment.getAttribute("stroke-width")).toBe(
      String(BAND_EDGE.strokeWidth),
    );
  }
});

test("the stack, the legend and the components list share one order", () => {
  render(<IncomeDistributionBreakdown />);
  for (const conceptKey of ["market", "net"]) {
    fireEvent.click(
      screen.getByRole("tab", {
        name: conceptKey === "net" ? /net income/i : /market income/i,
      }),
    );
    const components = incomeDistributionData[conceptKey].components;
    const listed = [
      ...document.querySelectorAll(".income-component-item strong"),
    ].map((node) => node.textContent);
    expect(listed).toEqual(components.map((c) => c.label));
    const legend = [
      ...document.querySelectorAll(".recharts-legend-item-text"),
    ].map((node) => node.textContent);
    expect(legend).toEqual(listed);
    // Each bar layer draws one segment per group, in the stacking order.
    const layers = [...document.querySelectorAll(".recharts-bar-rectangles")];
    expect(
      layers.map((layer) =>
        layer.querySelector("path.recharts-rectangle")?.getAttribute("fill"),
      ),
    ).toEqual(components.map((c) => SEGMENT_COLOURS[c.key]));
  }
});
