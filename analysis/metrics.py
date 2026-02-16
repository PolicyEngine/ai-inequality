"""Pure functions for inequality metrics: Gini, decile shares, Lorenz curve."""

import numpy as np


def weighted_gini(values, weights):
    """Compute the Gini coefficient for a weighted distribution.

    Uses the Lerman-Yitzhaki (1989) formula with midpoint ranks,
    which is scale-invariant in weights.

    Args:
        values: Array of income/wealth values.
        weights: Array of corresponding weights (e.g., household weights).

    Returns:
        Gini coefficient in [0, 1].
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)

    mask = weights > 0
    values, weights = values[mask], weights[mask]

    if len(values) == 0:
        return 0.0

    idx = np.argsort(values)
    values, weights = values[idx], weights[idx]

    cumw = np.cumsum(weights)
    total_w = cumw[-1]
    mu = np.sum(values * weights) / total_w

    if mu == 0:
        return 0.0

    # Midpoint rank: F_i = (cumw_i - w_i/2) / total_w
    ranks = (cumw - weights / 2) / total_w

    return float(2 * np.sum(weights * values * ranks) / (total_w * mu) - 1)


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
