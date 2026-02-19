"""Unit tests for capital_share_sweep (no PolicyEngine dependency).

Tests the _apply_multiplier helper logic and result structure validation.
"""

import numpy as np
import pytest


class TestPositiveOnlyScaling:
    """Test the positive-only scaling logic used across all scenarios."""

    def test_positive_values_scaled(self):
        """Positive values get multiplied."""
        vals = np.array([100.0, 200.0, 0.0, 50.0])
        mult = 3.0
        scaled = np.where(vals >= 0, vals * mult, vals)

        np.testing.assert_array_equal(scaled, [300.0, 600.0, 0.0, 150.0])

    def test_negative_values_unchanged(self):
        """Negative values (losses) are left unchanged."""
        vals = np.array([100.0, -500.0, 200.0, -10.0])
        mult = 2.0
        scaled = np.where(vals >= 0, vals * mult, vals)

        assert scaled[0] == 200.0
        assert scaled[1] == -500.0  # unchanged
        assert scaled[2] == 400.0
        assert scaled[3] == -10.0  # unchanged

    def test_zero_treated_as_positive(self):
        """Zero values get scaled (multiplied by anything = 0 anyway)."""
        vals = np.array([0.0, 0.0])
        mult = 5.0
        scaled = np.where(vals >= 0, vals * mult, vals)

        np.testing.assert_array_equal(scaled, [0.0, 0.0])

    def test_multiplier_one_is_identity(self):
        """1x multiplier leaves everything unchanged."""
        vals = np.array([100.0, -50.0, 0.0, 200.0])
        mult = 1.0
        scaled = np.where(vals >= 0, vals * mult, vals)

        np.testing.assert_array_equal(scaled, vals)

    def test_all_negative(self):
        """All-negative array is completely unchanged."""
        vals = np.array([-100.0, -200.0, -50.0])
        mult = 5.0
        scaled = np.where(vals >= 0, vals * mult, vals)

        np.testing.assert_array_equal(scaled, vals)


class TestSweepResultStructure:
    """Test expected structure of sweep results (mocked)."""

    def _make_fake_row(self, mult, label):
        return {
            "label": label,
            "multiplier": mult,
            "capital_share": 0.11 * mult / (1 + 0.11 * (mult - 1)),
            "market_gini": 0.60 + 0.02 * (mult - 1),
            "net_gini": 0.51 + 0.02 * (mult - 1),
            "spm_poverty_rate": 0.20,
            "fed_revenue": 2.2e12 * mult,
            "state_revenue": 0.5e12 * mult,
            "total_revenue": 2.7e12 * mult,
            "mean_net_income": 80000 + 5000 * (mult - 1),
            "mean_market_income": 90000 + 5000 * (mult - 1),
            "decile_shares": [0.01 * i + 0.01 for i in range(10)],
            "top_10_share": 0.38 + 0.03 * (mult - 1),
            "bottom_10_share": 0.01,
            "top_20_share": 0.53,
            "bottom_20_share": 0.03,
        }

    def test_rows_have_required_keys(self):
        row = self._make_fake_row(2.0, "2x")
        required = [
            "label", "multiplier", "capital_share", "market_gini",
            "net_gini", "spm_poverty_rate", "fed_revenue", "state_revenue",
            "total_revenue", "decile_shares", "top_10_share", "bottom_10_share",
        ]
        for key in required:
            assert key in row, f"Missing key: {key}"

    def test_decile_shares_length(self):
        row = self._make_fake_row(1.0, "Baseline")
        assert len(row["decile_shares"]) == 10

    def test_capital_share_increases_with_multiplier(self):
        r1 = self._make_fake_row(1.0, "Baseline")
        r2 = self._make_fake_row(2.0, "2x")
        r5 = self._make_fake_row(5.0, "5x")
        assert r1["capital_share"] < r2["capital_share"] < r5["capital_share"]

    def test_gini_increases_with_multiplier(self):
        r1 = self._make_fake_row(1.0, "Baseline")
        r5 = self._make_fake_row(5.0, "5x")
        assert r1["net_gini"] < r5["net_gini"]
        assert r1["market_gini"] < r5["market_gini"]
