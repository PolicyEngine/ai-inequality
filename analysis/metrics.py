"""Utility functions for inequality metrics not provided by microdf."""

import numpy as np


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
