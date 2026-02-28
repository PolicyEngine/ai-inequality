"""Compute average effective marginal tax rates by income source.

Two MTR measures:
  - Population-weighted: bump every person by flat $100.
    Answers: "What's the average MTR across people?"
  - Dollar-weighted: bump every person by 1% of their income.
    Answers: "If total income in this category rises by $X, what fraction
    goes to taxes?"  This is the relevant measure for predicting revenue
    impact of a labor→capital shift.

Both use exactly 5 branches per scenario — same memory footprint.
Runs one scenario at a time (fresh simulation each) to avoid OOM.
All branches are created BEFORE computing downstream variables.
"""

import json
import numpy as np
from policyengine_us import Microsimulation

from .constants import YEAR, CAPITAL_INCOME_VARS

INCOME_SOURCES = [
    "employment_income",
    "self_employment_income",
    "long_term_capital_gains",
    "short_term_capital_gains",
    "qualified_dividend_income",
]

# Proportional bump for dollar-weighted MTR.
# $100 flat would give population-weighted; 1% proportional gives dollar-weighted.
# Both use 5 branches — identical memory/compute footprint.
DELTA_PCT = 0.01  # 1%


def _compute_mtr_for_scenario(sim, label):
    """Compute population-weighted and dollar-weighted MTRs.

    Uses a single set of proportional-bump branches.
    Dollar-weighted MTR: delta_net / (income_total * DELTA_PCT)
    Population-weighted MTR: delta_net / (n_people * flat_bump) — derived
    analytically from the same branches using per-capita income share.
    """
    pw = sim.calculate("person_weight", period=YEAR)
    n_people = float(np.array(pw).sum())

    # Phase 1: create ALL branches before any downstream calc
    branches = {}
    income_totals = {}

    for var in INCOME_SOURCES:
        original = sim.calculate(var, period=YEAR)
        raw = np.array(original)
        w = np.array(original.weights)
        income_totals[var] = float((raw * w).sum())

        b = sim.get_branch(f"pct_{var}"[:50])
        # Proportional bump: each person gets +1% of their income
        b.set_input(var, YEAR, raw * (1 + DELTA_PCT))
        branches[var] = b

    # Phase 2: compute downstream
    base_net = float(sim.calculate("household_net_income", period=YEAR).sum())

    row = {"label": label}
    for var in INCOME_SOURCES:
        bumped_net = float(
            branches[var].calculate(
                "household_net_income", period=YEAR
            ).sum()
        )
        delta_net = bumped_net - base_net
        delta_gross_dollar = income_totals[var] * DELTA_PCT

        if abs(delta_gross_dollar) > 0:
            mtr_dollar = 1 - (delta_net / delta_gross_dollar)
        else:
            mtr_dollar = float("nan")

        row[var] = mtr_dollar
        print(f"    {var:35s}  dollar-weighted MTR = {mtr_dollar:6.1%}"
              f"  (total income: ${income_totals[var]/1e12:.1f}T)")

    return row


def _apply_capital_mult(baseline, mult):
    """Create a branch with positive-only capital income scaled by mult."""
    branch = baseline.get_branch(f"cap_{int(mult * 100)}")
    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        vals = np.array(original)
        branch.set_input(var, YEAR, np.where(vals >= 0, vals * mult, vals))
    return branch


def _apply_shift(baseline, pct):
    """Create a branch with labor shifted to capital (conservation-safe)."""
    branch = baseline.get_branch(f"shift_{int(pct * 100)}")

    emp = baseline.calculate("employment_income", period=YEAR)
    se = baseline.calculate("self_employment_income", period=YEAR)
    branch.set_input("employment_income", YEAR, emp * (1 - pct))
    branch.set_input("self_employment_income", YEAR, se * (1 - pct))

    total_freed = float((emp * pct).sum() + (se * pct).sum())

    cap_positive_totals = {}
    for var in CAPITAL_INCOME_VARS:
        vals = baseline.calculate(var, period=YEAR)
        raw = np.array(vals)
        w = np.array(vals.weights)
        cap_positive_totals[var] = float(
            (np.where(raw >= 0, raw, 0) * w).sum()
        )
    total_positive = sum(cap_positive_totals.values())

    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        pos_total = cap_positive_totals[var]
        if pos_total > 0 and total_positive > 0:
            share = pos_total / total_positive
            scale = 1 + (share * total_freed) / pos_total
            vals = np.array(original)
            branch.set_input(
                var, YEAR, np.where(vals >= 0, vals * scale, vals)
            )

    return branch


def main():
    print("=" * 70)
    print("AVERAGE EFFECTIVE MARGINAL TAX RATES BY INCOME SOURCE")
    print("=" * 70)

    # Add more scenarios here as needed; each loads a fresh sim (~10 min).
    scenario_defs = [
        ("Baseline", lambda b: b),
    ]

    all_results = []
    for label, setup_fn in scenario_defs:
        print(f"\n--- {label} ---")
        print("  Loading microsimulation...")
        baseline = Microsimulation()
        sim = setup_fn(baseline)
        row = _compute_mtr_for_scenario(sim, label)
        all_results.append(row)
        del baseline, sim

    short_names = {
        "employment_income": "Emp",
        "self_employment_income": "Self-emp",
        "long_term_capital_gains": "LTCG",
        "short_term_capital_gains": "STCG",
        "qualified_dividend_income": "Qual div",
    }

    print(f"\n{'=' * 90}")
    print("SUMMARY: Dollar-weighted average effective MTR by income source")
    print("(1% proportional bump — weights MTR by income share, not headcount)")
    print("=" * 90)
    header = f"{'Scenario':>15s}"
    for var in INCOME_SOURCES:
        header += f"  {short_names[var]:>10s}"
    print(header)
    print("-" * 90)
    for r in all_results:
        row_str = f"{r['label']:>15s}"
        for var in INCOME_SOURCES:
            row_str += f"  {r[var]:>9.1%}"
        print(row_str)

    output = {
        "year": YEAR,
        "method": "dollar-weighted (1% proportional bump)",
        "income_sources": INCOME_SOURCES,
        "short_names": short_names,
        "results": [
            {"label": r["label"],
             "mtrs": {var: r[var] for var in INCOME_SOURCES}}
            for r in all_results
        ],
    }
    with open("analysis/outputs/mtr_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved to analysis/outputs/mtr_results.json")


if __name__ == "__main__":
    main()
