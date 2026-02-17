"""Sweep capital income from 1x to 5x and measure inequality/poverty/revenue.

Instead of a single "doubled capital income" scenario, this runs the full
spectrum to show how metrics evolve as capital's share of total income rises.
The x-axis is expressed as both a multiplier and as capital's share of total
market income.
"""

import numpy as np
import pandas as pd
from policyengine_us import Microsimulation

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


def _extract_results(sim, label):
    """Extract standard metrics from a simulation or branch."""
    net_income = sim.calculate("household_net_income", period=YEAR)
    market_income = sim.calculate("household_market_income", period=YEAR)
    income_tax = sim.calculate("income_tax", map_to="household", period=YEAR)
    state_tax = sim.calculate(
        "state_income_tax", map_to="household", period=YEAR
    )
    in_poverty = sim.calculate(
        "spm_unit_is_in_spm_poverty", map_to="person", period=YEAR
    )

    decile_shares = compute_decile_shares(
        np.array(net_income.values), np.array(net_income.weights)
    )

    return {
        "label": label,
        "mean_net_income": float(net_income.mean()),
        "mean_market_income": float(market_income.mean()),
        "market_gini": float(market_income.gini()),
        "net_gini": float(net_income.gini()),
        "spm_poverty_rate": float(in_poverty.mean()),
        "fed_revenue": float(income_tax.sum()),
        "state_revenue": float(state_tax.sum()),
        "total_revenue": float(income_tax.sum()) + float(state_tax.sum()),
        "decile_shares": decile_shares,
        "top_10_share": decile_shares[9],
        "bottom_10_share": decile_shares[0],
        "top_20_share": decile_shares[8] + decile_shares[9],
        "bottom_20_share": decile_shares[0] + decile_shares[1],
    }


def run_sweep(multipliers=None, positive_only=False):
    """Run capital income sweep across multiplier values.

    Args:
        multipliers: List of floats (default MULTIPLIERS).
        positive_only: If True, only scale non-negative capital income.
            Losses stay at their original level.

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
