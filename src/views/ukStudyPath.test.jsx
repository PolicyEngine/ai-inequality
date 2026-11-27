import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";

import ukShiftSweepData from "../data/ukShiftSweepData.json";
import Home from "./Home";
import IncomeShift from "./IncomeShift";
import PolicyAnalysis from "./PolicyAnalysis";

// policyengine.org serves the UK view at /uk/ai-inequality by rewriting it
// to this export's /us/ai-inequality pages with ?country=uk. The query
// reaches only that upstream request, so the browser shows the UK path with
// no query, and the router, whose basename is /uk/ai-inequality, sees the
// page's own path. These tests put the browser there the same way.
function renderAtUkPath(page, View) {
  window.history.replaceState(null, "", `/uk/ai-inequality${page}`);
  render(
    <MemoryRouter initialEntries={[page]}>
      <View />
      <Search />
    </MemoryRouter>,
  );
}

function Search() {
  return <output data-testid="search">{useLocation().search}</output>;
}

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

test("the UK path shows the UK overview", () => {
  renderAtUkPath("/", Home);

  expect(screen.getByText("£144bn")).toBeInTheDocument();
  expect(screen.getByText(/UK GenAI exposure/i)).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /income-shift experiment/i }),
  ).toHaveAttribute(
    "href",
    "https://www.policyengine.org/uk/ai-inequality/income-shift",
  );
  expect(screen.queryByText(/MIT Iceberg Index/i)).not.toBeInTheDocument();
});

test("the UK path shows the UK income-shift experiment", () => {
  const ukFacts = ukShiftSweepData.metadata.baseline_facts;

  renderAtUkPath("/income-shift", IncomeShift);

  expect(
    screen.getByRole("radio", { name: /united kingdom/i }),
  ).toHaveAttribute("aria-checked", "true");
  expect(
    screen.getByRole("link", { name: /back to ai inequality overview/i }),
  ).toHaveAttribute("href", "https://www.policyengine.org/uk/ai-inequality");
  expect(document.body).toHaveTextContent(
    `£${ukFacts.labor_income_t.toFixed(1)}T`,
  );
  expect(document.body).not.toHaveTextContent(/Medicaid/);
});

test("the UK path shows the UK policy analysis, without the US health-coverage figures", () => {
  renderAtUkPath("/policy-analysis", PolicyAnalysis);

  expect(document.body).toHaveTextContent("We model no behavioural responses.");
  expect(document.body).not.toHaveTextContent(/market income stays/i);
  expect(document.querySelector("section.health-coverage")).toBeNull();
  expect(document.querySelector(".study-figure")).toBeNull();
  expect(document.body).not.toHaveTextContent(/Medicaid/);
});

test("on the UK path, the country selector reaches the US and comes back", () => {
  renderAtUkPath("/income-shift", IncomeShift);
  const radio = (name) => screen.getByRole("radio", { name });

  fireEvent.click(radio(/united states/i));
  expect(radio(/united states/i)).toHaveAttribute("aria-checked", "true");
  expect(screen.getByTestId("search")).toHaveTextContent("?country=us");
  expect(
    screen.getByRole("link", { name: /back to ai inequality overview/i }),
  ).toHaveAttribute("href", "https://www.policyengine.org/us/ai-inequality");

  // The UK is this path's own country, so choosing it drops the query.
  fireEvent.click(radio(/united kingdom/i));
  expect(radio(/united kingdom/i)).toHaveAttribute("aria-checked", "true");
  expect(screen.getByTestId("search")).toBeEmptyDOMElement();
});
