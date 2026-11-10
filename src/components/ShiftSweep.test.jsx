import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import sweepData from "../data/shiftSweepData.json";
import ukSweepData from "../data/ukShiftSweepData.json";
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

  render(
    <MemoryRouter>
      <ShiftSweep />
    </MemoryRouter>,
  );

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
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(
    screen.queryByRole("radiogroup", { name: /income concept/i }),
  ).not.toBeInTheDocument();
  expect(document.body).toHaveTextContent(
    formatBillions(shift100.revenue_change_b),
  );
  expect(document.body).toHaveTextContent(/capital-gains tax and niit/i);
  expect(document.body).toHaveTextContent(
    /we leave out health coverage such as medicaid/i,
  );
  expect(
    screen.getByRole("heading", { name: /federal revenue decomposition/i }),
  ).toBeInTheDocument();
  expect(document.body).toHaveTextContent(
    /payroll band includes employers' state unemployment insurance/i,
  );
  expect(document.body).toHaveTextContent(/the additional medicare tax/i);
  expect(document.body).toHaveTextContent(
    /we put new york city's and maryland's local income taxes in those states' charts instead/i,
  );
  expect(document.body).toHaveTextContent(
    /montgomery county's earned income credit\. california's include san francisco's working families tax credit\. teal gains, orange loses\./i,
  );
  expect(document.body).toHaveTextContent(
    "We sort households into deciles by weighted baseline market income and keep each household in its baseline decile in every scenario. Bars show the total change in each decile's net income ($B).",
  );
});

test("the UK revenue view prices its deciles in pounds and names what moves its total", () => {
  render(
    <MemoryRouter>
      <ShiftSweep sweepData={ukSweepData} />
    </MemoryRouter>,
  );
  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(document.body).toHaveTextContent(
    "Bars show the total change in each decile's net income (£B).",
  );
  expect(document.body).not.toHaveTextContent(/dollar/i);
  expect(document.body).toHaveTextContent(
    "We estimate Income Tax and Capital Gains Tax receipts, taken together, climb at the top of the sweep, while National Insurance receipts keep falling and household benefits keep rising.",
  );
  // No decile has a baseline mean net income of zero or less, so the chart
  // drops none.
  expect(document.body).not.toHaveTextContent(/we leave out d\d/i);
});

test("the decile chart names each decile it leaves out", () => {
  // compute_decile_impacts writes no percentage change for a decile whose
  // baseline mean net income is zero or less.
  const data = JSON.parse(JSON.stringify(sweepData));
  for (const scenario of data.metadata.baseline_facts.decile_impacts
    .scenarios) {
    scenario.deciles[0].pct_change = null;
    scenario.deciles[1].pct_change = null;
  }
  render(
    <MemoryRouter>
      <ShiftSweep sweepData={data} />
    </MemoryRouter>,
  );
  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(document.body).toHaveTextContent(
    "We leave out D1 and D2, whose baseline mean net incomes are zero or negative.",
  );
});
