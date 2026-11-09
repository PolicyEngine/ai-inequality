// Tests for the sweep's revenue builders.
//
// Invariants:
//
// * every row's revenue equals the sum of its bands;
// * a missing field counts as zero;
// * without health coverage and TANF, the federal chart, every state's chart
//   and the taxes outside them add up to the published total (taxes less
//   refundable credits and household benefits);
// * with them, they add up to the total that pays for health coverage and
//   counts TANF once (analysis/fiscal.py's total_change_with_health_tanf);
// * a state's chart total equals the state_net_change_b that
//   analysis/compute_shift_sweep.py writes for it.
//
// The property tests draw from a seeded generator so a failure reproduces.

import sweepData from "../data/shiftSweepData.json";
import {
  countsHealthTanf,
  federalRow,
  stateDeltaRow,
  stateRow,
} from "./sweepRevenue";

// mulberry32: a small deterministic generator, so a failing case reproduces.
function generator(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function bandsSum(row) {
  return Object.entries(row)
    .filter(([key]) => key !== "revenue")
    .reduce((sum, [, value]) => sum + value, 0);
}

test("federal row: hand example with and without health coverage and TANF", () => {
  const scenario = {
    fed_income_tax_before_refundable_credits_change_b: 10,
    refundable_credits_change_b: 4,
    state_refundable_credits_change_b: 1,
    employer_payroll_change_b: -3,
    employee_ss_tax_change_b: -2,
    employee_medicare_tax_change_b: -1,
    self_employment_tax_change_b: 0.5,
    benefits_change_b: 6,
    state_benefits_change_b: 1,
    tanf_change_b: 0.5,
    health_federal_change_b: 2,
  };
  expect(federalRow(scenario)).toEqual({
    rev_fed_income_tax_net: 7,
    rev_payroll_all: -5.5,
    rev_fed_benefits: -5,
    revenue: -3.5,
  });
  expect(federalRow(scenario, true)).toEqual({
    rev_fed_income_tax_net: 7,
    rev_payroll_all: -5.5,
    rev_fed_benefits: -4.5,
    rev_fed_health: -2,
    revenue: -5,
  });
});

test("state row: hand example where the state's benefits hold part of its TANF", () => {
  const delta = {
    state_tax_before_refundable_credits_change_b: 3,
    state_refundable_credits_change_b: 0.5,
    state_benefits_change_b: 1,
    tanf_in_state_benefits_change_b: 0.2,
    tanf_change_b: 0.4,
    state_health_change_b: 0.7,
  };
  expect(stateDeltaRow(delta)).toEqual({
    rev_state_income_tax_net: 2.5,
    rev_state_benefits: -1,
    revenue: 1.5,
  });
  const withHealth = stateDeltaRow(delta, true);
  expect(withHealth.rev_state_income_tax_net).toBe(2.5);
  expect(withHealth.rev_state_benefits).toBeCloseTo(-0.8, 12);
  expect(withHealth.rev_state_tanf).toBe(-0.4);
  expect(withHealth.rev_state_health).toBe(-0.7);
  expect(withHealth.revenue).toBeCloseTo(0.6, 12);
  expect(
    stateRow({ state_deltas: { MA: delta } }, "MA", true).revenue,
  ).toBeCloseTo(0.6, 12);
});

test("missing fields and missing states count as zero", () => {
  expect(federalRow({}).revenue).toBe(0);
  expect(federalRow(undefined, true)).toEqual({
    rev_fed_income_tax_net: 0,
    rev_payroll_all: 0,
    rev_fed_benefits: -0,
    rev_fed_health: -0,
    revenue: 0,
  });
  expect(stateRow({ state_deltas: {} }, "CA", true).revenue).toBe(0);
  expect(stateRow(undefined, "CA").revenue).toBe(0);
});

test("countsHealthTanf keys on health_federal_change_b, zero included", () => {
  expect(countsHealthTanf(undefined)).toBe(false);
  expect(countsHealthTanf({ scenarios: [] })).toBe(false);
  expect(countsHealthTanf({ scenarios: [{ revenue_change_b: 1 }] })).toBe(
    false,
  );
  expect(
    countsHealthTanf({ scenarios: [{}, { health_federal_change_b: 0 }] }),
  ).toBe(true);
});

// A national scenario row and its states, built the way
// analysis/compute_shift_sweep.py builds them: every national state field adds
// up the states' fields, and the totals follow analysis/fiscal.py.
function randomScenario(random) {
  const draw = (scale = 10) => (random() - 0.5) * 2 * scale;
  const codes = ["CA", "MA", "NY", "TX", "WA"].slice(
    0,
    1 + Math.floor(random() * 5),
  );
  const states = {};
  for (const code of codes) {
    const tanf = draw(1);
    const tanfInStateBenefits = code === "MA" ? tanf : 0;
    const d = {
      state_tax_before_refundable_credits_change_b: draw(),
      state_refundable_credits_change_b: draw(2),
      state_benefits_change_b: draw(2) + tanfInStateBenefits,
      tanf_change_b: tanf,
      tanf_in_state_benefits_change_b: tanfInStateBenefits,
      state_health_change_b: draw(3),
    };
    // compute_shift_sweep._state_delta_rows's state_net_change_b.
    d.state_net_change_b =
      d.state_tax_before_refundable_credits_change_b -
      d.state_refundable_credits_change_b -
      d.state_benefits_change_b -
      (d.tanf_change_b - d.tanf_in_state_benefits_change_b) -
      d.state_health_change_b;
    states[code] = d;
  }
  const sumStates = (key) =>
    Object.values(states).reduce((sum, d) => sum + d[key], 0);
  const s = {
    fed_income_tax_before_refundable_credits_change_b: draw(50),
    employee_ss_tax_change_b: draw(5),
    employee_medicare_tax_change_b: draw(2),
    self_employment_tax_change_b: draw(2),
    employer_payroll_change_b: draw(5),
    taxes_outside_charts_change_b: draw(1),
    state_tax_before_refundable_credits_change_b: sumStates(
      "state_tax_before_refundable_credits_change_b",
    ),
    state_refundable_credits_change_b: sumStates(
      "state_refundable_credits_change_b",
    ),
    state_benefits_change_b: sumStates("state_benefits_change_b"),
    tanf_change_b: sumStates("tanf_change_b"),
    tanf_counted_twice_change_b: sumStates("tanf_in_state_benefits_change_b"),
    health_federal_change_b: draw(5),
    health_state_change_b: sumStates("state_health_change_b"),
    state_deltas: states,
  };
  s.refundable_credits_change_b = s.state_refundable_credits_change_b + draw(5);
  s.benefits_change_b = s.state_benefits_change_b + s.tanf_change_b + draw(5);
  // household_tax_before_refundable_credits: every chart tax plus the taxes
  // outside the charts.
  s.household_tax_change_b =
    s.fed_income_tax_before_refundable_credits_change_b +
    s.employee_ss_tax_change_b +
    s.employee_medicare_tax_change_b +
    s.self_employment_tax_change_b +
    s.state_tax_before_refundable_credits_change_b +
    s.taxes_outside_charts_change_b;
  // fiscal.net_fiscal_impact's total_change, then the total with health
  // coverage and TANF counted once.
  s.total_rev_change_published_definition_b =
    s.household_tax_change_b +
    s.employer_payroll_change_b -
    s.refundable_credits_change_b -
    s.benefits_change_b;
  s.revenue_change_b =
    s.total_rev_change_published_definition_b +
    s.tanf_counted_twice_change_b -
    (s.health_federal_change_b + s.health_state_change_b);
  return s;
}

function chartsTotal(scenario, withHealthTanf) {
  const states = Object.keys(scenario.state_deltas).reduce(
    (sum, code) => sum + stateRow(scenario, code, withHealthTanf).revenue,
    0,
  );
  return (
    federalRow(scenario, withHealthTanf).revenue +
    states +
    scenario.taxes_outside_charts_change_b
  );
}

test("property: the charts and the taxes outside them add up to the total", () => {
  const random = generator(20261109);
  for (let i = 0; i < 500; i += 1) {
    const s = randomScenario(random);
    const context = `case ${i}: ${JSON.stringify(s)}`;
    expect(chartsTotal(s, true), context).toBeCloseTo(s.revenue_change_b, 9);
    expect(chartsTotal(s, false), context).toBeCloseTo(
      s.total_rev_change_published_definition_b,
      9,
    );
    for (const row of [federalRow(s), federalRow(s, true)]) {
      expect(row.revenue).toBeCloseTo(bandsSum(row), 12);
    }
    for (const d of Object.values(s.state_deltas)) {
      const row = stateDeltaRow(d, true);
      expect(row.revenue).toBeCloseTo(bandsSum(row), 12);
      expect(row.revenue, context).toBeCloseTo(d.state_net_change_b, 9);
    }
  }
});

// Differential checks against what analysis/compute_shift_sweep.py wrote to
// the site's data file.
const withHealthTanf = countsHealthTanf(sweepData);

test("each state's chart total matches the sweep's state_net_change_b", () => {
  let checked = 0;
  for (const scenario of sweepData.scenarios) {
    for (const [code, d] of Object.entries(scenario.state_deltas ?? {})) {
      if (d.state_net_change_b == null) continue;
      expect(
        stateDeltaRow(d, withHealthTanf).revenue,
        `${code} at ${scenario.shift_pct}%`,
      ).toBeCloseTo(d.state_net_change_b, 9);
      checked += 1;
    }
  }
  expect(checked).toBeGreaterThan(0);
});

test.skipIf(!withHealthTanf)(
  "the site's charts leave the sweep's chart identity residual of its total",
  () => {
    for (const scenario of sweepData.scenarios) {
      const label = `shift ${scenario.shift_pct}%`;
      // policyengine-us adds float32 values, so the identity holds to about a
      // millionth of the aggregates (analysis/tests/test_health_tanf.py's
      // _float32_slack): tens of millions of dollars on the full dataset. A
      // band that left out a program would miss by billions.
      expect(Math.abs(scenario.chart_identity_residual_b), label).toBeLessThan(
        0.1,
      );
      // The states' rows add up to the national state lines, so the page's
      // charts leave the same residual the sweep computed, to the dollar.
      expect(
        scenario.revenue_change_b - chartsTotal(scenario, true),
        label,
      ).toBeCloseTo(scenario.chart_identity_residual_b, 6);
    }
  },
);
