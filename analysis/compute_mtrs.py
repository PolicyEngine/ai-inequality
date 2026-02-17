"""Compute average effective marginal tax rates by income source.

For each income source, bumps every person's income by $1, measures the
change in household net income, and reports the population-average MTR.

MTR = 1 - (delta_net_income / delta_gross_income)

Runs one scenario at a time (fresh simulation each) to avoid OOM from
too many branches.  Within each scenario, all MTR branches are created
BEFORE computing any downstream variables (avoids cache staleness).
"""

import json
import numpy as np
from policyengine_us import Microsimulation

YEAR = 2026

INCOME_SOURCES = [
    "employment_income",
    "self_employment_income",
    "long_term_capital_gains",
    "short_term_capital_gains",
    "qualified_dividend_income",
]

CAPITAL_INCOME_VARS = [
    "long_term_capital_gains",
    "short_term_capital_gains",
    "taxable_interest_income",
    "qualified_dividend_income",
    "non_qualified_dividend_income",
    "rental_income",
]

# $100 bump avoids threshold/cliff artifacts in benefit phase-ins
# that dominate at $1 increments. MTR estimates are stable at $100+.
DELTA = 100.0


def _compute_mtr_for_scenario(sim, label):
    """Compute MTRs for one scenario simulation.

    Creates MTR branches, then computes downstream.
    Returns dict of {income_source: mtr_value}.
    """
    # Phase 1: create all MTR branches before any downstream calc
    mtr_branches = {}
    for var in INCOME_SOURCES:
        name = f"mtr_{var}"[:50]
        branch = sim.get_branch(name)
        original = sim.calculate(var, period=YEAR)
        branch.set_input(var, YEAR, np.array(original) + DELTA)
        mtr_branches[var] = branch

    # Phase 2: compute downstream
    # NB: MicroSeries.sum() auto-weights (= sum(val*weight)), so for
    # person_weight it returns sum(weight^2).  We need sum(weight).
    person_weights = sim.calculate("person_weight", period=YEAR)
    n_people = float(np.array(person_weights).sum())  # raw sum of weights
    base_net = float(sim.calculate("household_net_income", period=YEAR).sum())

    row = {"label": label}
    for var in INCOME_SOURCES:
        bumped_net = float(
            mtr_branches[var].calculate(
                "household_net_income", period=YEAR
            ).sum()
        )
        total_delta_net = bumped_net - base_net
        total_delta_gross = n_people * DELTA
        mtr = 1 - (total_delta_net / total_delta_gross)
        row[var] = mtr
        print(f"    {var:35s}  MTR = {mtr:6.1%}")

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

    # Positive-only weighted totals for conservation
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

    # Define scenarios: (label, setup_fn)
    # Each setup_fn takes a fresh baseline and returns the sim to measure
    scenario_defs = [
        ("Baseline", lambda b: b),
        ("2x capital", lambda b: _apply_capital_mult(b, 2)),
        ("5x capital", lambda b: _apply_capital_mult(b, 5)),
        ("10% shift", lambda b: _apply_shift(b, 0.10)),
        ("50% shift", lambda b: _apply_shift(b, 0.50)),
    ]

    all_results = []
    for label, setup_fn in scenario_defs:
        print(f"\n--- {label} ---")
        print("  Loading microsimulation...")
        baseline = Microsimulation()
        sim = setup_fn(baseline)
        row = _compute_mtr_for_scenario(sim, label)
        all_results.append(row)
        # sim and baseline go out of scope -> GC can reclaim memory
        del baseline, sim

    # Summary table
    print("\n" + "=" * 90)
    print("SUMMARY: Average effective MTR by income source")
    print("=" * 90)

    short_names = {
        "employment_income": "Emp",
        "self_employment_income": "Self-emp",
        "long_term_capital_gains": "LTCG",
        "short_term_capital_gains": "STCG",
        "qualified_dividend_income": "Qual div",
    }

    header = f"{'Scenario':>15s}"
    for var in INCOME_SOURCES:
        header += f"  {short_names[var]:>10s}"
    print(header)
    print("-" * 90)

    for r in all_results:
        row = f"{r['label']:>15s}"
        for var in INCOME_SOURCES:
            row += f"  {r[var]:>9.1%}"
        print(row)

    # Save to JSON
    output = {
        "year": YEAR,
        "income_sources": INCOME_SOURCES,
        "short_names": short_names,
        "results": [
            {
                "label": r["label"],
                "mtrs": {var: r[var] for var in INCOME_SOURCES},
            }
            for r in all_results
        ],
    }
    with open("analysis/outputs/mtr_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved to analysis/outputs/mtr_results.json")


if __name__ == "__main__":
    main()
