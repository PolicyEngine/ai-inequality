"""Unit tests for inequality metrics (no PolicyEngine dependency needed).

Gini is provided by microdf (MicroSeries.gini()) and tested there.
These tests cover decile shares and Lorenz curve utilities.
"""

import numpy as np
import pytest

from analysis.metrics import compute_decile_shares, lorenz_curve


class TestDecileShares:
    def test_equal_incomes(self):
        """Equal incomes -> each decile gets ~10%."""
        values = np.full(1000, 100.0)
        weights = np.ones(1000)
        shares = compute_decile_shares(values, weights)

        assert len(shares) == 10
        assert sum(shares) == pytest.approx(1.0)
        for s in shares:
            assert s == pytest.approx(0.1, abs=0.02)

    def test_shares_sum_to_one(self):
        """Shares always sum to 1."""
        rng = np.random.default_rng(42)
        values = rng.lognormal(10, 2, size=500)
        weights = rng.uniform(0.5, 2.0, size=500)
        shares = compute_decile_shares(values, weights)

        assert len(shares) == 10
        assert sum(shares) == pytest.approx(1.0, abs=1e-6)

    def test_top_decile_largest(self):
        """With skewed income, top decile has largest share."""
        rng = np.random.default_rng(42)
        values = rng.lognormal(10, 2, size=1000)
        weights = np.ones(1000)
        shares = compute_decile_shares(values, weights)

        assert shares[9] > shares[0]
        assert shares[9] == max(shares)

    def test_quintiles(self):
        """Can compute quintile shares (n=5)."""
        values = np.full(100, 50.0)
        weights = np.ones(100)
        shares = compute_decile_shares(values, weights, n=5)

        assert len(shares) == 5
        assert sum(shares) == pytest.approx(1.0)


class TestLorenzCurve:
    def test_perfect_equality(self):
        """Equal incomes -> Lorenz curve is the 45-degree line."""
        values = np.full(100, 100.0)
        weights = np.ones(100)
        x, y = lorenz_curve(values, weights, n_points=50)

        assert len(x) == 50
        assert len(y) == 50
        np.testing.assert_allclose(y, x, atol=0.02)

    def test_endpoints(self):
        """Lorenz curve starts at (0,0) and ends at (1,1)."""
        rng = np.random.default_rng(42)
        values = rng.lognormal(10, 2, size=200)
        weights = rng.uniform(0.5, 2.0, size=200)
        x, y = lorenz_curve(values, weights)

        assert x[0] == pytest.approx(0.0)
        assert x[-1] == pytest.approx(1.0)
        assert y[0] == pytest.approx(0.0, abs=0.01)
        assert y[-1] == pytest.approx(1.0, abs=0.01)

    def test_monotonic(self):
        """Lorenz curve is monotonically non-decreasing."""
        rng = np.random.default_rng(42)
        values = rng.lognormal(10, 2, size=200)
        weights = np.ones(200)
        x, y = lorenz_curve(values, weights)

        assert np.all(np.diff(x) >= 0)
        assert np.all(np.diff(y) >= -1e-10)

    def test_below_diagonal(self):
        """With inequality, Lorenz curve is below the 45-degree line."""
        values = np.array([1, 1, 1, 1, 100])
        weights = np.ones(5)
        x, y = lorenz_curve(values, weights, n_points=50)

        # Interior points should be below diagonal
        interior = (x > 0.05) & (x < 0.95)
        assert np.all(y[interior] <= x[interior] + 0.01)
