import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import ukShiftSweepData from "../data/ukShiftSweepData.json";
import BudgetLabMemo from "./BudgetLabMemo";
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
  // Project images load from the UK path, which policyengine.org serves.
  const images = [...document.querySelectorAll("img.project-image")];
  expect(images.length).toBeGreaterThan(0);
  for (const image of images) {
    expect(image.getAttribute("src")).toMatch(/^\/uk\/ai-inequality\/images\//);
  }
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

// Names every plain object inherits name no country, so each page falls back
// to its path's country.
test.each(["constructor", "toString", "__proto__"])(
  "?country=%s shows the path's country",
  (key) => {
    renderAtUkPath(`/income-shift?country=${key}`, IncomeShift);
    expect(
      screen.getByRole("radio", { name: /united kingdom/i }),
    ).toHaveAttribute("aria-checked", "true");
    cleanup();
    renderAtUkPath(`/policy-analysis?country=${key}`, PolicyAnalysis);
    expect(document.querySelector("section.health-coverage")).toBeNull();
    expect(document.body).toHaveTextContent(
      "We model no behavioural responses.",
    );
  },
);

// The Budget Lab memo covers the US scenarios, so its link opens the US
// experiment from either country's path.
function followMemoLink(path) {
  window.history.replaceState(null, "", `${path}/budget-lab`);
  render(
    <MemoryRouter initialEntries={["/budget-lab"]}>
      <Routes>
        <Route path="/budget-lab" element={<BudgetLabMemo />} />
        <Route path="/income-shift" element={<IncomeShift />} />
      </Routes>
      <Search />
    </MemoryRouter>,
  );
  fireEvent.click(
    screen.getByRole("link", { name: /interactive version of this analysis/i }),
  );
}

test("on the UK path, the US memo's link opens the US experiment", () => {
  followMemoLink("/uk/ai-inequality");

  expect(screen.getByRole("radio", { name: /united states/i })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  expect(screen.getByTestId("search")).toHaveTextContent("?country=us");
});

test("on the US path, the memo's link opens the US experiment with no query", () => {
  followMemoLink("/us/ai-inequality");

  expect(screen.getByRole("radio", { name: /united states/i })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  expect(screen.getByTestId("search")).toBeEmptyDOMElement();
});

// The UK figures come from licensed survey microdata, so the overview calls
// the models and the data-processing code open source, not the data (Max's
// ruling on d3496, 2026-11-27).
test("the UK overview doesn't call the household data open source", () => {
  renderAtUkPath("/", Home);
  const text = document.body.textContent;

  expect(text).toContain(
    "Open-source UK tax-benefit model and data-processing code",
  );
  expect(text).toContain(
    "We publish our tax-benefit models and data-processing code as open source, with the models under AGPL-3.0.",
  );
  expect(text).not.toMatch(/household microdata|models, data, and code/i);

  // No block that says "open source" mentions data, other than the
  // data-processing code.
  const openSourceBlocks = [...document.body.querySelectorAll("*")].filter(
    (element) =>
      /open[- ]source/i.test(element.textContent) &&
      ![...element.children].some((child) =>
        /open[- ]source/i.test(child.textContent),
      ),
  );
  expect(openSourceBlocks.length).toBeGreaterThan(2);
  expect(
    openSourceBlocks
      .map((element) => element.textContent)
      .filter((block) => /\b(?:micro)?data\b(?!-processing)/i.test(block)),
  ).toEqual([]);
});

// The copy the UK view shows once the UK path is its default.
test("the UK income-shift page names the tax year and its limits, with no US wording", () => {
  renderAtUkPath("/income-shift", IncomeShift);
  const text = document.body.textContent;

  expect(text).toContain("The 2026-27 United Kingdom baseline");
  expect(text).toContain("on a 2026-27 baseline");
  expect(text).toContain("PolicyEngine 4.4.4, 2026-27 baseline.");
  expect(text).toContain(
    "income they already receive. We model no behavioural responses.",
  );
  expect(text).toMatch(
    /The change in net revenue bottoms out at -£130B at a 70% shift/,
  );
  expect(text).toMatch(
    /the top decile's mean net income rises 38% while decile \d+'s falls \d+\.\d%\./,
  );
  expect(text).not.toMatch(/dollars|\+\d+%|loses -/);
  // In the UK sweep the net-income Gini rises more than the market-income
  // Gini, so the page doesn't say current law dampens the shock.
  expect(text).toContain(
    "Net income Gini coefficient rises from 0.375 at baseline to 0.752 at a 100% shift.",
  );
  expect(text).not.toContain("dampens");
});

test("the US income-shift page keeps its year, limits and Gini sentence", () => {
  render(
    <MemoryRouter initialEntries={["/income-shift"]}>
      <IncomeShift />
    </MemoryRouter>,
  );
  const text = document.body.textContent;

  expect(text).toContain("on a 2026 baseline");
  expect(text).not.toContain("2026-27");
  expect(text).toContain(
    "Households' total market income stays the same. We don't pass employers' savings on payroll tax to anyone, and we model no behavioral responses.",
  );
  expect(text).toContain(
    "Current law dampens the shock, but it does not come close to offsetting it.",
  );
});

test("the UK revenue summary says which taxes it counts", () => {
  renderAtUkPath("/income-shift", IncomeShift);
  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );

  expect(document.body).toHaveTextContent(
    "These estimates count Income Tax, Capital Gains Tax, National Insurance and household benefits, so they leave out any change in Corporation Tax revenue.",
  );
  expect(document.body).not.toHaveTextContent(/corporate income tax/);
});

test("the baseline table says how each column ranks households", () => {
  renderAtUkPath("/policy-analysis", PolicyAnalysis);

  expect(document.body).toHaveTextContent(
    "The market and positive capital income columns rank households by baseline market income, and the net income column ranks them by net income.",
  );
  expect(document.body).toHaveTextContent(
    "The 2026-27 United Kingdom baseline",
  );
});
