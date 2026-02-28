"""Utility functions for inequality metrics not provided by microdf."""

import numpy as np

from .constants import YEAR


def compute_decile_shares(values, weights, n=10):
    """Compute income shares by quantile.

    Args:
        values: Array of income values.
        weights: Array of corresponding weights.
        n: Number of quantile groups (default 10 for deciles).

    Returns:
        List of n floats summing to 1.0 (share of total income per group).
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)

    idx = np.argsort(values)
    values, weights = values[idx], weights[idx]

    cumw = np.cumsum(weights)
    total_w = cumw[-1]

    shares = []
    for i in range(n):
        lower = i / n * total_w
        upper = (i + 1) / n * total_w
        mask = (cumw > lower) & (cumw <= upper)
        if i == 0:
            mask = cumw <= upper
        shares.append(float((values[mask] * weights[mask]).sum()))

    total = sum(shares)
    return [s / total for s in shares] if total > 0 else shares


def lorenz_curve(values, weights, n_points=100):
    """Compute Lorenz curve points.

    Args:
        values: Array of income values.
        weights: Array of corresponding weights.
        n_points: Number of evenly spaced points to return.

    Returns:
        Tuple of (x, y) arrays where x is cumulative population share
        and y is cumulative income share.
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)

    idx = np.argsort(values)
    values, weights = values[idx], weights[idx]

    cumw = np.cumsum(weights)
    cumwv = np.cumsum(values * weights)
    total_w, total_wv = cumw[-1], cumwv[-1]

    pop_fracs = np.concatenate([[0], cumw / total_w])
    if total_wv > 0:
        income_fracs = np.concatenate([[0], cumwv / total_wv])
    else:
        income_fracs = pop_fracs.copy()

    x = np.linspace(0, 1, n_points)
    return x, np.interp(x, pop_fracs, income_fracs)


def extract_results(sim, label):
    """Extract standard metrics from a simulation or branch.

    Returns a dict with core inequality/poverty/revenue metrics plus
    raw MicroSeries for downstream use (charts, state breakdowns).

    Uses MicroSeries.gini() from microdf for Gini calculation.
    """
    net_income = sim.calculate("household_net_income", period=YEAR)
    market_income = sim.calculate("household_market_income", period=YEAR)
    income_tax = sim.calculate("income_tax", map_to="household", period=YEAR)
    state_income_tax = sim.calculate(
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
        "state_revenue": float(state_income_tax.sum()),
        "total_revenue": float(income_tax.sum()) + float(state_income_tax.sum()),
        "decile_shares": decile_shares,
        "top_10_share": decile_shares[9],
        "bottom_10_share": decile_shares[0],
        "top_20_share": decile_shares[8] + decile_shares[9],
        "bottom_20_share": decile_shares[0] + decile_shares[1],
        # Raw MicroSeries for downstream use (charts, state breakdown)
        "_net_income": net_income,
        "_market_income": market_income,
        "_income_tax": income_tax,
        "_state_income_tax": state_income_tax,
    }
