"""Microsimulation scenarios for labor-to-capital income shift.

Models AI-driven automation as a shift from labor income to capital income
at constant total GDP. For each shift level (e.g. 10%, 25%, 50%), we reduce
all employment income by that fraction and redistribute the lost wages into
capital income variables proportionally.
"""

import numpy as np
import pandas as pd
from policyengine_us import Microsimulation
from policyengine_core.reforms import Reform

from .metrics import compute_decile_shares

YEAR = 2026

CAPITAL_INCOME_VARS = [
    "long_term_capital_gains",
    "short_term_capital_gains",
    "taxable_interest_income",
    "qualified_dividend_income",
    "non_qualified_dividend_income",
    "rental_income",
]

SHIFT_LEVELS = [0.10, 0.25, 0.50]


def _extract_results(sim, label):
    """Extract standard metrics from a simulation or branch."""
    net_income = sim.calculate("household_net_income", period=YEAR)
    market_income = sim.calculate("household_market_income", period=YEAR)
    income_tax = sim.calculate("income_tax", map_to="household", period=YEAR)
    state_tax = sim.calculate("state_income_tax", map_to="household", period=YEAR)
    in_poverty = sim.calculate(
        "spm_unit_is_in_spm_poverty", map_to="person", period=YEAR
    )

    return {
        "label": label,
        "mean_net_income": float(net_income.mean()),
        "market_gini": float(market_income.gini()),
        "net_gini": float(net_income.gini()),
        "spm_poverty_rate": float(in_poverty.mean()),
        "fed_revenue": float(income_tax.sum()),
        "state_revenue": float(state_tax.sum()),
        "decile_shares": compute_decile_shares(
            np.array(net_income.values), np.array(net_income.weights)
        ),
        "_net_income": net_income,
        "_market_income": market_income,
    }


def _apply_shift(baseline, branch_name, shift_pct):
    """Create a branch with labor income shifted to capital income.

    Reduces employment_income by shift_pct and distributes the freed
    wages across capital income variables in proportion to their
    existing totals.
    """
    branch = baseline.get_branch(branch_name)

    # Cut employment income
    emp_income = baseline.calculate("employment_income", period=YEAR)
    wage_reduction = emp_income * shift_pct
    branch.set_input("employment_income", YEAR, emp_income - wage_reduction)

    # Also cut self-employment income by the same fraction
    se_income = baseline.calculate("self_employment_income", period=YEAR)
    se_reduction = se_income * shift_pct
    branch.set_input("self_employment_income", YEAR, se_income - se_reduction)

    # Total labor income freed up (person-level)
    total_freed = float((wage_reduction.sum() + se_reduction.sum()))

    # Distribute freed income across capital vars proportional to existing totals
    cap_totals = {}
    for var in CAPITAL_INCOME_VARS:
        vals = baseline.calculate(var, period=YEAR)
        cap_totals[var] = float(vals.sum())

    total_existing_cap = sum(cap_totals.values())

    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        if total_existing_cap > 0:
            share = cap_totals[var] / total_existing_cap
        else:
            share = 1.0 / len(CAPITAL_INCOME_VARS)
        # Scale up each person's capital income proportionally
        # so the aggregate increase equals share * total_freed
        original_total = cap_totals[var]
        if original_total > 0:
            scale = 1 + (share * total_freed) / original_total
            branch.set_input(var, YEAR, original * scale)
        # If a capital var has zero total, skip — can't distribute proportionally

    return branch, total_freed


def run_scenarios(shift_levels=None):
    """Run labor→capital shift scenarios at multiple shift levels.

    Args:
        shift_levels: List of floats (e.g. [0.10, 0.25, 0.50]).
            Defaults to SHIFT_LEVELS.

    Returns:
        Dict with keys "baseline", "shifts" (list of per-level results),
        and "meta" with population/household counts.
    """
    if shift_levels is None:
        shift_levels = SHIFT_LEVELS

    print("Running baseline microsimulation...")
    baseline = Microsimulation()

    # Create all branches BEFORE computing any downstream variables
    branches = {}
    for pct in shift_levels:
        name = f"shift_{int(pct * 100)}"
        print(f"Creating {int(pct * 100)}% labor→capital shift branch...")
        branch, freed = _apply_shift(baseline, name, pct)
        branches[pct] = (branch, freed)

    weights = np.array(baseline.calculate("household_weight", period=YEAR))
    hh_count_people = baseline.calculate("household_count_people", period=YEAR)
    total_population = float(hh_count_people.sum())

    baseline_results = _extract_results(baseline, "Baseline")

    shift_results = []
    for pct in shift_levels:
        branch, freed = branches[pct]
        label = f"{int(pct * 100)}% shift"
        r = _extract_results(branch, label)
        r["shift_pct"] = pct
        r["total_freed"] = freed
        shift_results.append(r)

    # UBI scenario: use the largest shift's extra revenue to fund UBI
    largest = shift_results[-1]
    extra_fed = largest["fed_revenue"] - baseline_results["fed_revenue"]
    ubi_amount = extra_fed / total_population if extra_fed > 0 else 0

    ubi_results = None
    if ubi_amount > 0:
        print(f"UBI from {int(shift_levels[-1] * 100)}% shift: "
              f"${ubi_amount:,.2f}/person/year (${ubi_amount/12:,.2f}/month)")

        reform = Reform.from_dict({
            "gov.contrib.ubi_center.basic_income.amount.person.flat": {
                f"{YEAR}-01-01.2100-12-31": round(ubi_amount, 2)
            },
        }, country_id="us")

        ubi_sim = Microsimulation(reform=reform)
        ubi_branch, _ = _apply_shift(ubi_sim, "shift_ubi", shift_levels[-1])
        ubi_results = _extract_results(
            ubi_branch, f"{int(shift_levels[-1] * 100)}% shift + UBI"
        )
        ubi_results["ubi_per_person"] = ubi_amount

    return {
        "baseline": baseline_results,
        "shifts": shift_results,
        "ubi": ubi_results,
        "meta": {
            "year": YEAR,
            "total_households": float(weights.sum()),
            "total_population": total_population,
            "shift_levels": shift_levels,
        },
    }
