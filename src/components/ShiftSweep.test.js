import { fireEvent, render, screen } from "@testing-library/react";

import sweepData from "../data/shiftSweepData.json";
import ShiftSweep from "./ShiftSweep";

test("switches the single sweep chart between inequality and revenue outcomes", () => {
  const shift100 = sweepData.scenarios.find(
    (scenario) => scenario.shift_pct === 100,
  );
  const formatBillions = (value) =>
    `$${value >= 0 ? "+" : ""}${value.toFixed(0)}B`;
  const formatShare = (value) => {
    const pct = value * 100;
    if (Math.abs(pct) >= 10) {
      return `${pct.toFixed(0)}%`;
    }
    if (Math.abs(pct) >= 1) {
      return `${pct.toFixed(1)}%`;
    }
    return `${pct.toFixed(2)}%`;
  };

  render(<ShiftSweep />);

  expect(
    screen.getByRole("radio", { name: /gini coefficient/i }),
  ).toHaveAttribute("aria-checked", "true");
  expect(screen.getByRole("radio", { name: /net income/i })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  expect(document.body).toHaveTextContent(
    sweepData.scenarios[0].net_gini.toFixed(3),
  );
  expect(document.body).toHaveTextContent(shift100.net_gini.toFixed(3));

  fireEvent.click(screen.getByRole("radio", { name: /market income/i }));
  expect(screen.getByRole("radio", { name: /market income/i })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  expect(document.body).toHaveTextContent(
    sweepData.scenarios[0].market_gini.toFixed(3),
  );
  expect(document.body).toHaveTextContent(shift100.market_gini.toFixed(3));

  fireEvent.click(screen.getByRole("radio", { name: /top 1% share/i }));
  expect(document.body).toHaveTextContent(
    formatShare(sweepData.scenarios[0].market_top_1_share),
  );
  expect(document.body).toHaveTextContent(
    formatShare(shift100.market_top_1_share),
  );

  fireEvent.click(
    screen.getByRole("radio", { name: /net federal revenue change/i }),
  );
  expect(
    screen.queryByRole("radiogroup", { name: /income concept/i }),
  ).not.toBeInTheDocument();
  expect(document.body).toHaveTextContent(
    formatBillions(shift100.revenue_change_b),
  );
  expect(document.body).toHaveTextContent(/payroll-tax losses/i);
});
