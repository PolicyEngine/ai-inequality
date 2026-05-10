import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import incomeDistributionData from "../data/incomeDistributionData.json";
import ukShiftSweepData from "../data/ukShiftSweepData.json";
import IncomeShift from "./IncomeShift";

function renderIncomeShift(initialEntry = "/income-shift") {
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <IncomeShift />
    </MemoryRouter>,
  );
}

test("renders standalone income-shift page with overview navigation", () => {
  const positiveCapitalTop01 =
    incomeDistributionData.capitalBenchmarks.local.find(
      (row) => row.label === "Positive capital income, ranked by market income",
    ).shares.top01.share;

  renderIncomeShift();

  expect(
    screen.getByRole("heading", {
      name: /what if income shifts from labor to capital/i,
    }),
  ).toBeInTheDocument();
  expect(screen.getAllByText(/positive labor income/i).length).toBeGreaterThan(
    0,
  );
  expect(
    screen.getByRole("link", { name: /back to ai inequality overview/i }),
  ).toHaveAttribute("href", "https://www.policyengine.org/us/ai-inequality");
  expect(
    screen.getByRole("heading", { name: /baseline distribution/i }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/positive capital income share/i),
  ).toBeInTheDocument();
  expect(document.body).toHaveTextContent(
    `${(positiveCapitalTop01 * 100).toFixed(1)}%`,
  );
});

test("renders UK income-shift data from the country selector", () => {
  const ukFacts = ukShiftSweepData.metadata.baseline_facts;

  renderIncomeShift("/income-shift?country=uk");

  expect(
    screen.getByRole("radio", { name: /united kingdom/i }),
  ).toHaveAttribute("aria-checked", "true");
  expect(
    screen.getByRole("link", { name: /back to ai inequality overview/i }),
  ).toHaveAttribute("href", "https://www.policyengine.org/uk/ai-inequality");
  expect(
    screen.getByRole("heading", {
      name: /what if income shifts from labour to capital/i,
    }),
  ).toBeInTheDocument();
  expect(screen.getAllByText(/positive labour income/i).length).toBeGreaterThan(
    0,
  );
  expect(document.body).toHaveTextContent(
    `£${ukFacts.labor_income_t.toFixed(1)}T`,
  );
  expect(document.body).toHaveTextContent(
    `${(ukFacts.positive_capital_top_10_share * 100).toFixed(1)}%`,
  );
});
