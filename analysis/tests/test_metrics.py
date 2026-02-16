"""Unit tests for inequality metrics (no PolicyEngine dependency needed)."""

import numpy as np
import pytest

from analysis.metrics import weighted_gini, compute_decile_shares, lorenz_curve


class TestWeightedGini:
    def test_perfect_equality(self):
        """All incomes equal → Gini ≈ 0."""
        values = np.array([100.0, 100.0, 100.0, 100.0])
        weights = np.array([1.0, 1.0, 1.0, 1.0])
        # With the discrete correction term (+1/N), perfectly equal
        # distribution gives a small positive value, not exactly 0.
        assert weighted_gini(values, weights) == pytest.approx(0.0, abs=0.01)

    def test_maximum_inequality(self):
        """One person has everything → Gini ≈ 1."""
        values = np.array([0.0, 0.0, 0.0, 1_000_000.0])
        weights = np.array([1.0, 1.0, 1.0, 1.0])
        assert weighted_gini(values, weights) > 0.7

    def test_weight_scale_invariant(self):
        """Scaling all weights equally doesn't change Gini."""
        values = np.array([10.0, 50.0, 200.0, 1000.0])
        w1 = np.array([1.0, 1.0, 1.0, 1.0])
        w2 = np.array([100.0, 100.0, 100.0, 100.0])
        assert weighted_gini(values, w1) == pytest.approx(
            weighted_gini(values, w2), abs=0.02
        )

    def test_all_zero_income(self):
        """Zero incomes → Gini = 0."""
        values = np.array([0.0, 0.0, 0.0])
        weights = np.array([1.0, 1.0, 1.0])
        assert weighted_gini(values, weights) == 0.0

    def test_empty_after_filtering(self):
        """All zero weights → Gini = 0."""
        values = np.array([100.0, 200.0])
        weights = np.array([0.0, 0.0])
        assert weighted_gini(values, weights) == 0.0

    def test_single_observation(self):
        """Single observation → Gini well-defined."""
        values = np.array([500.0])
        weights = np.array([1.0])
        # With one observation, Gini should be 0 (no inequality).
        assert weighted_gini(values, weights) == pytest.approx(0.0, abs=0.01)

    def test_known_two_person(self):
        """Two people: incomes 0 and 100, equal weight → Gini = 0.5 (approx)."""
        values = np.array([0.0, 100.0])
        weights = np.array([1.0, 1.0])
        gini = weighted_gini(values, weights)
        assert 0.4 < gini < 0.6


class TestDecileShares:
    def test_equal_incomes(self):
        """Equal incomes → each decile gets ~10%."""
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
        """Equal incomes → Lorenz curve is the 45° line."""
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
        """With inequality, Lorenz curve is below the 45° line."""
        values = np.array([1, 1, 1, 1, 100])
        weights = np.ones(5)
        x, y = lorenz_curve(values, weights, n_points=50)

        # Interior points should be below diagonal
        interior = (x > 0.05) & (x < 0.95)
        assert np.all(y[interior] <= x[interior] + 0.01)
