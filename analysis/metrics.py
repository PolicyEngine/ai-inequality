"""Utility functions for inequality metrics not provided by microdf."""

import numpy as np

from .constants import YEAR

TOP_SHARE_FRACTIONS = (0.10, 0.01, 0.001)


def _calculate_first_available(sim, variable_names, *, period=None, map_to=None):
    """Calculate the first available variable in priority order.

    The managed PolicyEngine bundle can lag newer country-model APIs. This
    keeps the analysis compatible with renamed variables across bundle versions.
    """

    last_error = None
    for variable_name in variable_names:
        try:
            return sim.calculate(variable_name, map_to=map_to, period=period)
        except (KeyError, ValueError) as error:
            last_error = error

    if last_error is not None:
        raise last_error
    raise ValueError("No candidate variable names were provided.")


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

    if n <= 0:
        raise ValueError("n must be positive")

    idx = np.argsort(values)
    values, weights = values[idx], weights[idx]

    total_w = float(weights.sum())
    if total_w <= 0:
        return [0.0] * n

    # Split each weighted record across quantile boundaries instead of
    # assigning the full record to a single bucket.
    lower_bounds = np.concatenate([[0.0], np.cumsum(weights[:-1])])
    upper_bounds = lower_bounds + weights
    bucket_edges = np.linspace(0.0, total_w, n + 1)
    shares = np.zeros(n, dtype=float)

    bucket_idx = 0
    for value, lower, upper in zip(values, lower_bounds, upper_bounds):
        while bucket_idx < n and bucket_edges[bucket_idx + 1] <= lower:
            bucket_idx += 1

        current_idx = bucket_idx
        while current_idx < n and bucket_edges[current_idx] < upper:
            overlap = min(upper, bucket_edges[current_idx + 1]) - max(
                lower, bucket_edges[current_idx]
            )
            if overlap > 0:
                shares[current_idx] += value * overlap
            current_idx += 1

    total = float(shares.sum())
    return list(shares / total) if total > 0 else list(shares)


def compute_top_share(values, weights, top_fraction):
    """Compute the income share received by the top weighted fraction.

    Splits weighted records across the cutoff when a household weight spans the
    threshold separating the top group from the rest of the distribution.
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)

    if not 0 < top_fraction <= 1:
        raise ValueError("top_fraction must be between 0 and 1")

    idx = np.argsort(values)
    values, weights = values[idx], weights[idx]

    total_w = float(weights.sum())
    if total_w <= 0:
        return 0.0

    total_income = float((values * weights).sum())
    if total_income == 0:
        return 0.0

    cutoff = (1 - top_fraction) * total_w
    lower_bounds = np.concatenate([[0.0], np.cumsum(weights[:-1])])
    upper_bounds = lower_bounds + weights

    top_income = 0.0
    for value, lower, upper in zip(values, lower_bounds, upper_bounds):
        overlap = upper - max(lower, cutoff)
        if overlap > 0:
            top_income += value * overlap

    return top_income / total_income


def compute_top_shares(values, weights, top_fractions=TOP_SHARE_FRACTIONS):
    """Return a mapping of weighted top-share cutoffs to income shares."""
    return {
        top_fraction: compute_top_share(values, weights, top_fraction)
        for top_fraction in top_fractions
    }


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

    Includes both standard post-tax income metrics and a broader household
    resources concept that adds the cash-equivalent value of health coverage
    support (e.g. Medicaid, CHIP, ACA premium tax credits).

    Uses MicroSeries.gini() from microdf for Gini calculation.
    """
    net_income = sim.calculate("household_net_income", period=YEAR)
    net_income_including_health_benefits = sim.calculate(
        "household_net_income_including_health_benefits", period=YEAR
    )
    market_income = sim.calculate("household_market_income", period=YEAR)
    income_tax = sim.calculate("income_tax", map_to="household", period=YEAR)
    state_income_tax = sim.calculate(
        "state_income_tax", map_to="household", period=YEAR
    )
    healthcare_benefit_value = sim.calculate(
        "healthcare_benefit_value", period=YEAR
    )
    medicaid_cost = sim.calculate("medicaid_cost", map_to="household", period=YEAR)
    chip_benefit = sim.calculate("per_capita_chip", map_to="household", period=YEAR)
    aca_ptc = _calculate_first_available(
        sim,
        ("assigned_aca_ptc", "aca_ptc"),
        map_to="household",
        period=YEAR,
    )
    in_poverty = sim.calculate(
        "spm_unit_is_in_spm_poverty", map_to="person", period=YEAR
    )

    decile_shares = compute_decile_shares(
        np.array(net_income.values), np.array(net_income.weights)
    )
    decile_shares_including_health_benefits = compute_decile_shares(
        np.array(net_income_including_health_benefits.values),
        np.array(net_income_including_health_benefits.weights),
    )
    market_top_shares = compute_top_shares(
        np.array(market_income.values), np.array(market_income.weights)
    )
    net_top_shares = compute_top_shares(
        np.array(net_income.values), np.array(net_income.weights)
    )

    return {
        "label": label,
        "mean_net_income": float(net_income.mean()),
        "mean_net_income_including_health_benefits": float(
            net_income_including_health_benefits.mean()
        ),
        "mean_market_income": float(market_income.mean()),
        "market_gini": float(market_income.gini()),
        "net_gini": float(net_income.gini()),
        "net_gini_including_health_benefits": float(
            net_income_including_health_benefits.gini()
        ),
        "spm_poverty_rate": float(in_poverty.mean()),
        "fed_revenue": float(income_tax.sum()),
        "state_revenue": float(state_income_tax.sum()),
        "total_revenue": float(income_tax.sum()) + float(state_income_tax.sum()),
        "healthcare_benefit_value_total": float(healthcare_benefit_value.sum()),
        "medicaid_cost_total": float(medicaid_cost.sum()),
        "chip_benefit_total": float(chip_benefit.sum()),
        "aca_ptc_total": float(aca_ptc.sum()),
        "decile_shares": decile_shares,
        "decile_shares_including_health_benefits": (
            decile_shares_including_health_benefits
        ),
        "top_10_share": decile_shares[9],
        "top_1_share": net_top_shares[0.01],
        "top_0_1_share": net_top_shares[0.001],
        "bottom_10_share": decile_shares[0],
        "top_20_share": decile_shares[8] + decile_shares[9],
        "bottom_20_share": decile_shares[0] + decile_shares[1],
        "market_top_10_share": market_top_shares[0.10],
        "market_top_1_share": market_top_shares[0.01],
        "market_top_0_1_share": market_top_shares[0.001],
        "top_10_share_including_health_benefits": (
            decile_shares_including_health_benefits[9]
        ),
        "bottom_10_share_including_health_benefits": (
            decile_shares_including_health_benefits[0]
        ),
        "top_20_share_including_health_benefits": (
            decile_shares_including_health_benefits[8]
            + decile_shares_including_health_benefits[9]
        ),
        "bottom_20_share_including_health_benefits": (
            decile_shares_including_health_benefits[0]
            + decile_shares_including_health_benefits[1]
        ),
        # Raw MicroSeries for downstream use (charts, state breakdown)
        "_net_income": net_income,
        "_net_income_including_health_benefits": (
            net_income_including_health_benefits
        ),
        "_market_income": market_income,
        "_income_tax": income_tax,
        "_state_income_tax": state_income_tax,
        "_healthcare_benefit_value": healthcare_benefit_value,
    }
