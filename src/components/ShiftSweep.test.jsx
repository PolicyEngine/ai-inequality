import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import stateHealthPrograms from "../../analysis/tests/fixtures/state_health_programs.json";
import sweepData from "../data/shiftSweepData.json";
import ShiftSweep, {
  healthProgramState,
  stateLineNoteHealthTanf,
} from "./ShiftSweep";

// The site's sweep file as a run before d2671 wrote it: no health coverage or
// TANF fields, so the page keeps the bands and copy it published with.
function withoutHealthTanf(data) {
  return {
    ...data,
    scenarios: data.scenarios.map((scenario) => {
      const row = { ...scenario };
      delete row.federal_health_change_b;
      return row;
    }),
  };
}

// MOCK_HEALTH_TANF_PAYLOAD: made-up health and TANF amounts on the site's
// sweep file, to test the copy and bands that a run counting them gets. Its
// revenue falls at every step, so the summary takes its "falls to" form. None
// of these numbers come from a simulation.
const MOCK_HEALTH_TANF_PAYLOAD = {
  ...sweepData,
  metadata: {
    ...sweepData.metadata,
    health_tanf_programs: {
      state: ["co_omnisalud", "or_healthier_oregon_cost"],
    },
  },
  scenarios: sweepData.scenarios.map((scenario) => ({
    ...scenario,
    revenue_change_b: -scenario.shift_pct,
    total_rev_change_b: -scenario.shift_pct,
    federal_health_change_b: scenario.shift_pct / 10,
    state_health_change_b: scenario.shift_pct / 20,
    tanf_change_b: scenario.shift_pct / 100,
    state_deltas: Object.fromEntries(
      Object.entries(scenario.state_deltas ?? {}).map(([code, delta]) => [
        code,
        {
          ...delta,
          state_health_change_b: scenario.shift_pct / 1000,
          tanf_change_b: scenario.shift_pct / 10000,
          tanf_in_state_benefits_change_b: 0,
        },
      ]),
    ),
  })),
};

function renderSweep(data) {
  render(
    <MemoryRouter>
      <ShiftSweep sweepData={data} />
    </MemoryRouter>,
  );
}

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

  renderSweep(withoutHealthTanf(sweepData));

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
    /new york city's and maryland's local income taxes count in those states' charts instead/i,
  );
  expect(document.body).toHaveTextContent(
    /montgomery county's earned income credit\. california's include san francisco's working families tax credit and los angeles county's ez save program, infant supplement and expectant parent payment\./i,
  );
});

test("a run that counts health coverage and TANF gets their bands and copy", () => {
  renderSweep(MOCK_HEALTH_TANF_PAYLOAD);

  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(document.body).toHaveTextContent(
    /we count what governments spend on medicaid, chip, the medicare savings programs, aca premium tax credits/i,
  );
  expect(document.body).not.toHaveTextContent(
    /leaves? out health coverage such as medicaid/i,
  );
  expect(document.body).toHaveTextContent(
    /the health band includes what the federal government spends on aca premium tax credits/i,
  );
  expect(document.body).toHaveTextContent(
    /congress sets each state's tanf block grant at a fixed amount, so we charge every change in tanf benefits to the states\./i,
  );
  // The description names the taxes outside the charts, since a state's view
  // shows no list of them.
  expect(document.body).toHaveTextContent(
    /the federal and state charts add up to the total, apart from three groups of taxes\. we count workers' state payroll taxes such as california's sdi, the additional medicare tax, and local taxes on income and occupations only in the total\. new york city's and maryland's local income taxes count in those states' charts instead\./i,
  );
  expect(document.body).toHaveTextContent(/the additional medicare tax/i);
  expect(document.body).not.toHaveTextContent(
    /the benefits band includes tanf/i,
  );
  // The state ranking nets TANF and health spending.
  expect(document.body).toHaveTextContent(
    /− tanf − state health coverage spending\./i,
  );
  expect(document.body).not.toHaveTextContent(
    /we leave medicaid, chip and tanf out/i,
  );
  // Revenue falls at every step of the mock, so the summary has no rebound,
  // and its second sentence gives health spending rather than tax drivers.
  expect(document.body).toHaveTextContent(
    /reaches \$-50B at a 50% shift and falls to \$-100B at a 100% shift\. At that shift, we estimate the federal government spends \$10B more on health coverage and the states \$5\.0B more\./i,
  );
  expect(document.body).not.toHaveTextContent(/capital-gains tax and niit/i);
  // The state ranking charges each state the federal share it moves.
  expect(document.body).toHaveTextContent(
    /we also charge the state the federal share of coverage for enrollees whose immigration status bars federal matching\. the federal government still matches those enrollees' emergency care, so we overstate the state's cost\./i,
  );
  expect(document.body).not.toHaveTextContent(/the whole cost/i);

  fireEvent.change(screen.getByLabelText(/jurisdiction/i), {
    target: { value: "CA" },
  });
  expect(
    screen.getByRole("heading", { name: /ca state revenue decomposition/i }),
  ).toBeInTheDocument();
  expect(document.body).toHaveTextContent(
    /medicare savings programs\. for enrollees whose immigration status bars federal matching, we charge the state the federal share as well/i,
  );
  expect(document.body).toHaveTextContent(
    /congress sets each state's tanf block grant at a fixed amount, so we charge the state every change in its tanf benefits\./i,
  );

  fireEvent.change(screen.getByLabelText(/jurisdiction/i), {
    target: { value: "CO" },
  });
  expect(document.body).toHaveTextContent(
    /medicare savings programs, and on omnisalud, which it runs on its own\./i,
  );
});

// Every state health program the sweep's metadata can list, across
// policyengine-us releases. analysis/tests/test_health_tanf.py checks the
// fixture against analysis/health_tanf.py's STATE_HEALTH.
const STATE_HEALTH = stateHealthPrograms.programs.map(
  ({ variable }) => variable,
);

test("each state health program maps to its state", () => {
  expect(STATE_HEALTH.map(healthProgramState)).toEqual(
    stateHealthPrograms.programs.map(({ state }) => state),
  );
});

test("a state's health note names only the programs that state runs", () => {
  // At policyengine-us 1.764.6, the sweep's metadata lists these two.
  const programs = ["co_omnisalud", "or_healthier_oregon_cost"];
  expect(stateLineNoteHealthTanf("OR", programs)).toMatch(
    /Medicare Savings Programs, and on Healthier Oregon, which it runs on its own\./,
  );
  expect(stateLineNoteHealthTanf("CO", programs)).toMatch(
    /Medicare Savings Programs, and on OmniSalud, which it runs on its own\./,
  );
  expect(stateLineNoteHealthTanf("TX", programs)).toMatch(
    /Medicare Savings Programs\. For enrollees/,
  );
  expect(stateLineNoteHealthTanf("TX")).not.toMatch(/OmniSalud|Oregon/);
  // Later releases add programs the page has no display name for.
  expect(stateLineNoteHealthTanf("CO", STATE_HEALTH)).toMatch(
    /Medicare Savings Programs, and on OmniSalud and other health programs it runs on its own\./,
  );
  for (const state of ["CA", "NM", "MD", "MA"]) {
    expect(stateLineNoteHealthTanf(state, STATE_HEALTH)).toMatch(
      /Medicare Savings Programs, and on health programs it runs on its own\./,
    );
  }
  expect(stateLineNoteHealthTanf("TX", STATE_HEALTH)).toMatch(
    /Medicare Savings Programs\. For enrollees/,
  );
});

// Baseline totals turn share mode on (src/data/ukShiftSweepData.json carries
// them); these are made up.
const MOCK_BASELINE_TOTALS = {
  national: { fed_income_tax: 2.4e12, employer_payroll_tax: 1.3e12 },
  per_state: {
    CA: {
      household_state_tax_before_refundable_credits: 1.5e11,
      household_refundable_state_tax_credits: 5e9,
      household_state_benefits: 1e10,
    },
  },
};

function withTotals(data) {
  return {
    ...data,
    metadata: {
      ...data.metadata,
      baseline_facts: {
        ...(data.metadata?.baseline_facts ?? {}),
        totals: MOCK_BASELINE_TOTALS,
      },
    },
  };
}

test("share mode shows only for runs that count no health coverage or TANF", () => {
  renderSweep(withTotals(withoutHealthTanf(sweepData)));
  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(screen.getByRole("radiogroup", { name: /units/i })).toBeInTheDocument();
  cleanup();

  renderSweep(withTotals(MOCK_HEALTH_TANF_PAYLOAD));
  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(
    screen.queryByRole("radiogroup", { name: /units/i }),
  ).not.toBeInTheDocument();
});

function withRevenue(data, revenueAt) {
  return {
    ...data,
    scenarios: data.scenarios.map((scenario) => ({
      ...scenario,
      revenue_change_b: revenueAt(scenario.shift_pct),
      total_rev_change_b: revenueAt(scenario.shift_pct),
    })),
  };
}

test("the revenue summary handles a sweep that never falls or ends early", () => {
  renderSweep(
    withRevenue(withoutHealthTanf(sweepData), (pct) => pct),
  );
  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(document.body).toHaveTextContent(
    /never falls below zero and reaches \$\+100B at a 100% shift/i,
  );
  expect(document.body).not.toHaveTextContent(/bottoms out at \$\+0B/i);
  cleanup();

  const toNinety = withRevenue(withoutHealthTanf(sweepData), (pct) => -pct);
  toNinety.scenarios = toNinety.scenarios.filter(
    (scenario) => scenario.shift_pct <= 90,
  );
  renderSweep(toNinety);
  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(document.body).toHaveTextContent(
    /reaches \$-50B at a 50% shift and falls to \$-90B at a 90% shift/i,
  );
});

test("the old copy survives on a run without health coverage and TANF", () => {
  renderSweep(withoutHealthTanf(sweepData));

  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(document.body).toHaveTextContent(
    /the benefits band includes tanf\./i,
  );
  expect(document.body).toHaveTextContent(
    /we leave medicaid, chip and tanf out of these figures, apart from massachusetts's tafdc\./i,
  );
  expect(document.body).not.toHaveTextContent(/the health band includes/i);

  fireEvent.change(screen.getByLabelText(/jurisdiction/i), {
    target: { value: "CA" },
  });
  expect(document.body).not.toHaveTextContent(
    /congress sets each state's tanf block grant/i,
  );
});
