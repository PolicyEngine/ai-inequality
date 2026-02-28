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

from .constants import YEAR, CAPITAL_INCOME_VARS, EMPLOYER_PAYROLL_RATE
from .metrics import extract_results as _extract_results

SHIFT_LEVELS = [0.10, 0.25, 0.50]


def _apply_shift(baseline, branch_name, shift_pct):
    """Create a branch with labor income shifted to capital income.

    Reduces employment_income and self_employment_income by shift_pct
    and distributes the freed amount into capital income variables
    proportionally.

    The freed amount includes employer payroll tax savings: when AI
    replaces workers, the employer saves wages PLUS the employer-side
    payroll taxes on those wages. This total employer cost of
    compensation is what flows to capital owners, conserving total
    economic value rather than just wages.
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

    # Total wages freed (weighted aggregate)
    wages_freed = float(wage_reduction.sum() + se_reduction.sum())

    # Employer payroll savings: when AI replaces a worker, the employer
    # saves the employer-side payroll tax in addition to wages.
    # Use flat 7.65% (6.2% SS + 1.45% Medicare) — exact for workers
    # below the SS wage base, slightly overstates for high earners
    # above the cap (where effective rate is only 1.45%).
    # We avoid computing employer payroll from the simulation to prevent
    # branch caching issues with PolicyEngine.
    er_savings = wages_freed * EMPLOYER_PAYROLL_RATE

    # Total freed = wages + employer payroll savings
    total_freed = wages_freed + er_savings

    # Compute POSITIVE-ONLY weighted totals for redistribution.
    # Using positive totals for both shares and scale factors ensures
    # that every freed dollar is redistributed (conservation of market income).
    cap_positive_totals = {}
    for var in CAPITAL_INCOME_VARS:
        vals = baseline.calculate(var, period=YEAR)
        raw = np.array(vals)
        w = np.array(vals.weights)
        cap_positive_totals[var] = float((np.where(raw >= 0, raw, 0) * w).sum())

    total_positive_cap = sum(cap_positive_totals.values())

    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        pos_total = cap_positive_totals[var]
        if pos_total > 0 and total_positive_cap > 0:
            share = pos_total / total_positive_cap
            scale = 1 + (share * total_freed) / pos_total
            vals = np.array(original)
            scaled = np.where(vals >= 0, vals * scale, vals)
            branch.set_input(var, YEAR, scaled)

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
