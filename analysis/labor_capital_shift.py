"""Microsimulation scenarios for labor-to-capital income shift.

Models AI-driven automation as a shift from positive labor income to capital income
while keeping modeled household market income constant. For each shift level
(e.g. 10%, 25%, 50%), we reduce positive labor income by that fraction and
redistribute the lost labor income into capital income variables
proportionally.
"""

import numpy as np
from policyengine_us import Microsimulation
from policyengine_core.reforms import Reform

from .constants import YEAR, CAPITAL_INCOME_VARS
from .fiscal import compute_ubi_amount, net_fiscal_impact, revenue_components
from .metrics import extract_results as _extract_results

SHIFT_LEVELS = [0.10, 0.25, 0.50]


def _apply_shift(baseline, branch_name, shift_pct):
    """Create a branch with labor income shifted to capital income.

    Reduces positive employment_income and self_employment_income by shift_pct
    and distributes the freed amount into positive capital income variables
    proportionally.

    Redistributes only the positive labor income removed from wages and
    self-employment income. Negative self-employment income is left unchanged.
    Employer payroll tax effects remain fiscal
    effects in the model; they are not added back into household capital
    income.
    """
    branch = baseline.get_branch(branch_name)

    # Cut only positive labor income. Losses are not "freed" income.
    emp_income = baseline.calculate("employment_income", period=YEAR)
    emp_raw = np.asarray(emp_income, dtype=float)
    emp_weights = np.asarray(emp_income.weights, dtype=float)
    wage_reduction = np.where(emp_raw > 0, emp_raw * shift_pct, 0)
    branch.set_input("employment_income", YEAR, emp_raw - wage_reduction)

    se_income = baseline.calculate("self_employment_income", period=YEAR)
    se_raw = np.asarray(se_income, dtype=float)
    se_weights = np.asarray(se_income.weights, dtype=float)
    se_reduction = np.where(se_raw > 0, se_raw * shift_pct, 0)
    branch.set_input("self_employment_income", YEAR, se_raw - se_reduction)

    # Total labor income freed (weighted aggregate).
    total_freed = float(
        (wage_reduction * emp_weights).sum()
        + (se_reduction * se_weights).sum()
    )

    # Compute POSITIVE-ONLY weighted totals for redistribution.
    # Using positive totals for both shares and scale factors ensures
    # that every freed dollar is redistributed (conservation of market income).
    cap_positive_totals = {}
    for var in CAPITAL_INCOME_VARS:
        vals = baseline.calculate(var, period=YEAR)
        raw = np.array(vals)
        w = np.array(vals.weights)
        cap_positive_totals[var] = float((np.where(raw > 0, raw, 0) * w).sum())

    total_positive_cap = sum(cap_positive_totals.values())

    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        pos_total = cap_positive_totals[var]
        if pos_total > 0 and total_positive_cap > 0:
            share = pos_total / total_positive_cap
            scale = 1 + (share * total_freed) / pos_total
            vals = np.array(original)
            scaled = np.where(vals > 0, vals * scale, vals)
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

    # UBI scenario: use the largest shift's net fiscal gain to fund UBI
    baseline_fiscal = revenue_components(baseline)
    largest_fiscal = revenue_components(branches[shift_levels[-1]][0])
    extra_budget = net_fiscal_impact(
        largest_fiscal, baseline_fiscal
    )["total_change"]
    ubi_amount = compute_ubi_amount(extra_budget, total_population)

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
