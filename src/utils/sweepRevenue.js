// Revenue lines for the labor-to-capital shift sweep.
//
// Each function reads scenario rows of src/data/shiftSweepData.json, which
// analysis/compute_shift_sweep.py writes. A run that counts health coverage
// and TANF (analysis/health_tanf.py) gives every row federal_health_change_b
// and the other health and TANF fields. For those rows the builders mirror
// federal_chart_change and states_chart_change in analysis/fiscal.py: the
// federal chart, every state's chart and the taxes outside them add up to
// revenue_change_b. Rows from older runs keep the bands they were published
// with.

function amount(row, key) {
  return row?.[key] ?? 0;
}

function withTotal(bands) {
  return {
    ...bands,
    revenue: Object.values(bands).reduce((sum, value) => sum + value, 0),
  };
}

// True when the sweep's rows count health coverage and TANF.
export function countsHealthTanf(sweepData) {
  return (sweepData?.scenarios ?? []).some(
    (scenario) => scenario.federal_health_change_b != null,
  );
}

// Federal chart bands in $B, positive when federal revenue rises.
export function federalRow(scenario, withHealthTanf = false) {
  const rev_fed_income_tax_net =
    amount(scenario, "fed_income_tax_before_refundable_credits_change_b") -
    (amount(scenario, "refundable_credits_change_b") -
      amount(scenario, "state_refundable_credits_change_b"));
  const rev_payroll_all =
    amount(scenario, "employer_payroll_change_b") +
    amount(scenario, "employee_ss_tax_change_b") +
    amount(scenario, "employee_medicare_tax_change_b") +
    amount(scenario, "self_employment_tax_change_b");
  // Household benefits less household_state_benefits (the programs
  // PolicyEngine counts as state-paid). Federal law fixes each state's TANF
  // block grant, so runs that count health coverage and TANF charge every
  // change in TANF benefits to the states.
  const federalBenefits =
    amount(scenario, "benefits_change_b") -
    amount(scenario, "state_benefits_change_b") -
    (withHealthTanf ? amount(scenario, "tanf_change_b") : 0);
  const bands = {
    rev_fed_income_tax_net,
    rev_payroll_all,
    rev_fed_benefits: -federalBenefits,
  };
  if (withHealthTanf) {
    bands.rev_fed_health = -amount(scenario, "federal_health_change_b");
  }
  return withTotal(bands);
}

// One state's chart bands in $B from its entry in a scenario's state_deltas.
export function stateDeltaRow(delta, withHealthTanf = false) {
  const rev_state_income_tax_net =
    amount(delta, "state_tax_before_refundable_credits_change_b") -
    amount(delta, "state_refundable_credits_change_b");
  const stateBenefits = amount(delta, "state_benefits_change_b");
  if (!withHealthTanf) {
    return withTotal({
      rev_state_income_tax_net,
      rev_state_benefits: -stateBenefits,
    });
  }
  // household_state_benefits lists some states' TANF programs (Massachusetts's
  // TAFDC at policyengine-us 1.764.6) at their full amount for every eligible
  // family. The TANF band holds the state's TANF as tanf pays it, to families
  // that take it up, so the benefits band leaves that copy out.
  return withTotal({
    rev_state_income_tax_net,
    rev_state_benefits: -(
      stateBenefits - amount(delta, "tanf_in_state_benefits_change_b")
    ),
    rev_state_tanf: -amount(delta, "tanf_change_b"),
    rev_state_health: -amount(delta, "state_health_change_b"),
  });
}

export function stateRow(scenario, stateCode, withHealthTanf = false) {
  return stateDeltaRow(scenario?.state_deltas?.[stateCode], withHealthTanf);
}
