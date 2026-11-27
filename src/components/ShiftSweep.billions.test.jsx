import { cloneElement } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import sweepData from "../data/shiftSweepData.json";
import ukSweepData from "../data/ukShiftSweepData.json";
import ShiftSweep, { signedBillions } from "./ShiftSweep";

// jsdom gives ResponsiveContainer no size, so Recharts draws no axes there.
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

// The sweep writes signed billions as the health-coverage figures do: the
// sign before the currency symbol, and none on an amount that prints as zero.
// Each chart keeps the decimals it has always printed.
test("signs billions before the currency symbol, at each chart's precision", () => {
  expect(signedBillions(-172.101481)).toBe("-$172B");
  expect(signedBillions(2.082155, { precision: 1 })).toBe("+$2.1B");
  expect(signedBillions(-2011.26, { precision: 1 })).toBe("-$2011.3B");
  expect(signedBillions(-0.4567, { precision: 2, currencySymbol: "£" })).toBe(
    "-£0.46B",
  );
  expect(signedBillions(0)).toBe("$0B");
  expect(signedBillions(-0.3)).toBe("$0B");
  expect(signedBillions(0.004, { precision: 2 })).toBe("$0.00B");
});

// billions() throws on these. A tooltip that threw would empty the page.
test("prints a dash for a value that isn't a finite number", () => {
  for (const value of [NaN, Infinity, -Infinity, undefined, null]) {
    expect(signedBillions(value, { precision: 1 })).toBe("—");
  }
});

describe.each([
  ["US", sweepData, "$"],
  ["UK", ukSweepData, "£"],
])("the %s sweep's revenue axes", (_country, data, symbol) => {
  it("write signed billions with the sign before the currency symbol", () => {
    render(
      <MemoryRouter>
        <ShiftSweep sweepData={data} />
      </MemoryRouter>,
    );
    fireEvent.click(
      screen.getByRole("radio", { name: /net government revenue change/i }),
    );
    const ticks = [
      ...document.querySelectorAll(".recharts-cartesian-axis-tick-value"),
    ]
      .map((tick) => tick.textContent)
      .filter((text) => text.endsWith("B"));
    expect(ticks.length).toBeGreaterThan(0);
    const symbolAt = `[${symbol}]`;
    for (const tick of ticks) {
      expect(tick).toMatch(
        new RegExp(`^(?:[-+]${symbolAt}[1-9]\\d*|${symbolAt}0)B$`),
      );
    }
    expect(ticks).toContain(`${symbol}0B`);
    expect(ticks.some((tick) => tick.startsWith(`-${symbol}`))).toBe(true);
    expect(ticks.some((tick) => tick.startsWith(`+${symbol}`))).toBe(true);
  });
});

// Hover each revenue chart from corner to corner, so the pointer crosses every
// bar and point whichever way the chart lies, and collect what its tooltip
// prints.
async function tooltipValues(wrapper) {
  const plot = wrapper.querySelector("clipPath rect");
  const [x, y, width, height] = ["x", "y", "width", "height"].map((key) =>
    Number(plot.getAttribute(key)),
  );
  const values = new Set();
  for (let step = 0; step < 80; step++) {
    const along = (step + 0.5) / 80;
    fireEvent.mouseMove(wrapper, {
      clientX: x + width * along,
      clientY: y + height * along,
    });
    await act(async () => {
      vi.advanceTimersByTime(50);
    });
    for (const value of wrapper.querySelectorAll(
      ".recharts-default-tooltip .recharts-tooltip-item-value",
    )) {
      values.add(value.textContent);
    }
  }
  return [...values];
}

// The decimals each revenue chart's tooltip has always printed, in page
// order: the revenue breakdown, the US income tax breakdown, the deciles and
// the US state ranking.
describe.each([
  ["US", sweepData, "$", [1, 1, 1, 2]],
  ["UK", ukSweepData, "£", [1, 1]],
])("the %s sweep's revenue tooltips", (_country, data, symbol, decimals) => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("write signed billions at each chart's decimals", async () => {
    const { container } = render(
      <MemoryRouter>
        <ShiftSweep sweepData={data} />
      </MemoryRouter>,
    );
    fireEvent.click(
      screen.getByRole("radio", { name: /net government revenue change/i }),
    );
    const charts = [...container.querySelectorAll(".recharts-wrapper")];
    expect(charts).toHaveLength(decimals.length);
    for (const [index, chart] of charts.entries()) {
      const values = await tooltipValues(chart);
      expect(values.length).toBeGreaterThan(5);
      const form = new RegExp(
        `^([-+]?)[${symbol}](\\d+\\.\\d{${decimals[index]}})B$`,
      );
      for (const value of values) {
        const [, sign, digits] = value.match(form) ?? [];
        expect(digits, value).toBeDefined();
        expect(sign === "", value).toBe(Number(digits) === 0);
      }
      expect(values.some((value) => value.startsWith(`-${symbol}`))).toBe(true);
    }
  }, 30000);
});
