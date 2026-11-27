import { cloneElement } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
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
