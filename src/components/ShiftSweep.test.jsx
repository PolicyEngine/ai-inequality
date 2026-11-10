import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import sweepData from "../data/shiftSweepData.json";
import ShiftSweep from "./ShiftSweep";

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
  scenarios: sweepData.scenarios.map((scenario) => ({
    ...scenario,
    revenue_change_b: -scenario.shift_pct,
    total_rev_change_b: -scenario.shift_pct,
    federal_health_change_b: scenario.shift_pct / 10,
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
    /leaves out health coverage such as medicaid/i,
  );
  expect(
    screen.getByRole("heading", { name: /federal revenue decomposition/i }),
  ).toBeInTheDocument();
  expect(document.body).toHaveTextContent(
    /payroll band includes employers' state unemployment insurance/i,
  );
  expect(document.body).toHaveTextContent(/the additional medicare tax/i);
  expect(document.body).toHaveTextContent(
    /new york city's and maryland's local income taxes count in those states' charts/i,
  );
  expect(document.body).toHaveTextContent(
    /montgomery county's earned income credit; san francisco's working families tax credit; and three los angeles programs/i,
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
    /leaves out health coverage such as medicaid/i,
  );
  expect(document.body).toHaveTextContent(
    /the health band includes what the federal government spends on aca premium tax credits/i,
  );
  expect(document.body).toHaveTextContent(
    /fixed tanf block grant, so the states pay for any change in tanf benefits, and their charts count it/i,
  );
  expect(document.body).toHaveTextContent(/the additional medicare tax/i);
  expect(document.body).not.toHaveTextContent(
    /the benefits band counts tanf as federal/i,
  );
  // The state ranking nets TANF and health spending.
  expect(document.body).toHaveTextContent(
    /tanf − the state's spending on health coverage/i,
  );
  expect(document.body).not.toHaveTextContent(
    /it leaves out medicaid, chip and tanf/i,
  );
  // Revenue falls at every step of the mock, so the summary has no rebound.
  expect(document.body).toHaveTextContent(
    /reaches \$-50B at a 50% shift and falls to \$-100B at a 100% shift/i,
  );

  fireEvent.change(screen.getByLabelText(/jurisdiction/i), {
    target: { value: "CA" },
  });
  expect(
    screen.getByRole("heading", { name: /ca state revenue decomposition/i }),
  ).toBeInTheDocument();
  expect(document.body).toHaveTextContent(
    /the state pays for any change in tanf benefits, and the tanf band counts it/i,
  );
});

test("the old copy survives on a run without health coverage and TANF", () => {
  renderSweep(withoutHealthTanf(sweepData));

  fireEvent.click(
    screen.getByRole("radio", { name: /net government revenue change/i }),
  );
  expect(document.body).toHaveTextContent(
    /the benefits band counts tanf as federal/i,
  );
  expect(document.body).toHaveTextContent(
    /it leaves out medicaid, chip and tanf \(apart from massachusetts's tafdc\)/i,
  );
  expect(document.body).not.toHaveTextContent(/the health band includes/i);

  fireEvent.change(screen.getByLabelText(/jurisdiction/i), {
    target: { value: "CA" },
  });
  expect(document.body).not.toHaveTextContent(/the tanf band counts/i);
});
