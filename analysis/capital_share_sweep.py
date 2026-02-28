"""Sweep capital income from 1x to 5x and measure inequality/poverty/revenue.

Instead of a single "doubled capital income" scenario, this runs the full
spectrum to show how metrics evolve as capital's share of total income rises.
The x-axis is expressed as both a multiplier and as capital's share of total
market income.
"""

import numpy as np
from policyengine_us import Microsimulation

from .constants import YEAR, CAPITAL_INCOME_VARS
from .metrics import extract_results as _extract_results

MULTIPLIERS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0]


def _apply_multiplier(baseline, branch_name, mult, positive_only=False):
    """Create a branch with capital income scaled by mult.

    Args:
        baseline: Base Microsimulation.
        branch_name: Name for the branch.
        mult: Multiplier to apply.
        positive_only: If True, only scale non-negative values. Losses
            stay at their original level. This better models AI generating
            new capital returns without amplifying existing losses.

    Returns:
        The branch simulation.
    """
    branch = baseline.get_branch(branch_name)
    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        if positive_only:
            vals = np.array(original)
            scaled = np.where(vals >= 0, vals * mult, vals)
            branch.set_input(var, YEAR, scaled)
        else:
            branch.set_input(var, YEAR, original * mult)
    return branch


def run_sweep(multipliers=None, positive_only=True):
    """Run capital income sweep across multiplier values.

    Args:
        multipliers: List of floats (default MULTIPLIERS).
        positive_only: Only scale non-negative capital income (default True).
            Losses stay at their original level. Set False to scale everything
            including losses (not recommended — distorts bottom decile).

    Returns:
        Dict with "baseline_capital_share", "rows" (list of per-multiplier
        result dicts), and "meta".
    """
    if multipliers is None:
        multipliers = MULTIPLIERS

    mode = "positive-only" if positive_only else "all capital"
    print(f"Running baseline microsimulation ({mode} mode)...")
    baseline = Microsimulation()

    # Create ALL branches before computing anything downstream
    branches = {}
    for mult in multipliers:
        if mult == 1.0:
            continue
        suffix = "_pos" if positive_only else ""
        name = f"cap_{int(mult * 100)}{suffix}"
        branches[mult] = _apply_multiplier(
            baseline, name, mult, positive_only=positive_only
        )

    # Compute baseline capital share of market income
    baseline_market = baseline.calculate(
        "household_market_income", period=YEAR
    )
    total_market = float(baseline_market.sum())

    baseline_cap_total = 0.0
    for var in CAPITAL_INCOME_VARS:
        vals = baseline.calculate(var, period=YEAR)
        baseline_cap_total += float(vals.sum())

    baseline_cap_share = baseline_cap_total / total_market if total_market else 0
    print(f"Baseline capital share of market income: {baseline_cap_share:.1%}")

    weights = np.array(baseline.calculate("household_weight", period=YEAR))
    hh_people = baseline.calculate("household_count_people", period=YEAR)
    total_pop = float(hh_people.sum())

    # Extract results for each multiplier
    rows = []
    for mult in multipliers:
        label = f"{mult:.2g}x" if mult != 1.0 else "Baseline"
        print(f"  Computing {label}...")

        sim = baseline if mult == 1.0 else branches[mult]
        r = _extract_results(sim, label)
        r["multiplier"] = mult

        # Compute capital share at this multiplier
        new_cap_total = baseline_cap_total * mult
        new_market_total = total_market + (mult - 1) * baseline_cap_total
        r["capital_share"] = (
            new_cap_total / new_market_total if new_market_total else 0
        )

        rows.append(r)

    return {
        "baseline_capital_share": baseline_cap_share,
        "rows": rows,
        "positive_only": positive_only,
        "meta": {
            "year": YEAR,
            "total_households": float(weights.sum()),
            "total_population": total_pop,
            "multipliers": multipliers,
        },
    }
