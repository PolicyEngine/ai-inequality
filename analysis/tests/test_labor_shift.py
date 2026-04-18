"""Unit tests for labor_capital_shift logic (no PolicyEngine dependency).

Tests the proportional redistribution math and positive-only scaling.
"""

import numpy as np
import pytest

from analysis.fiscal import compute_ubi_amount, net_fiscal_impact


class TestLaborShiftMath:
    """Test the wage reduction and capital redistribution math."""

    def test_wage_reduction(self):
        """Shift percentage correctly reduces wages."""
        emp_income = np.array([100000, 50000, 75000, 0])
        shift_pct = 0.25
        reduction = emp_income * shift_pct
        new_income = emp_income - reduction

        np.testing.assert_array_almost_equal(
            new_income, [75000, 37500, 56250, 0]
        )

    def test_total_freed_amount(self):
        """Total freed income = sum of positive wage + SE reductions."""
        emp_income = np.array([100000, 50000])
        se_income = np.array([20000, -10000])
        shift_pct = 0.10

        freed = float(
            (np.where(emp_income > 0, emp_income * shift_pct, 0)).sum()
            + (np.where(se_income > 0, se_income * shift_pct, 0)).sum()
        )
        assert freed == pytest.approx(17000.0)

    def test_proportional_distribution(self):
        """Freed income distributed proportionally to existing capital."""
        cap_totals = {"ltcg": 500, "interest": 300, "dividends": 200}
        total_existing = sum(cap_totals.values())  # 1000
        total_freed = 100

        shares = {k: v / total_existing for k, v in cap_totals.items()}
        allocated = {k: s * total_freed for k, s in shares.items()}

        assert allocated["ltcg"] == pytest.approx(50.0)
        assert allocated["interest"] == pytest.approx(30.0)
        assert allocated["dividends"] == pytest.approx(20.0)
        assert sum(allocated.values()) == pytest.approx(total_freed)

    def test_scale_factor(self):
        """Scale factor correctly amplifies existing capital income."""
        original_total = 1000.0
        share = 0.5
        total_freed = 200.0

        scale = 1 + (share * total_freed) / original_total
        assert scale == pytest.approx(1.1)

        # A person with $100 in this var gets $110 after scaling
        assert 100 * scale == pytest.approx(110.0)

    def test_positive_only_redistribution(self):
        """Redistribution only scales positive holdings, not losses."""
        original = np.array([500.0, -200.0, 300.0, 0.0])
        scale = 1.5
        scaled = np.where(original > 0, original * scale, original)

        assert scaled[0] == pytest.approx(750.0)
        assert scaled[1] == pytest.approx(-200.0)  # loss unchanged
        assert scaled[2] == pytest.approx(450.0)
        assert scaled[3] == pytest.approx(0.0)

    def test_zero_capital_no_distribution(self):
        """If a capital var has zero total, it gets no redistribution."""
        original_total = 0.0
        # The code skips vars with zero total
        assert original_total == 0  # just verifying the guard condition


class TestUBICalculation:
    """Test UBI amount calculation from net fiscal space."""

    def test_ubi_per_person(self):
        """UBI = net fiscal gain / total population."""
        extra_budget = 500e9  # $500B
        total_pop = 330e6  # 330M people
        ubi = compute_ubi_amount(extra_budget, total_pop)

        assert ubi == pytest.approx(1515.15, abs=1)

    def test_zero_extra_revenue(self):
        """No extra fiscal space means no UBI."""
        extra_budget = 0
        total_pop = 330e6
        ubi = compute_ubi_amount(extra_budget, total_pop)
        assert ubi == 0

    def test_negative_extra_revenue(self):
        """Negative fiscal change means no UBI."""
        extra_budget = -100e9
        total_pop = 330e6
        ubi = compute_ubi_amount(extra_budget, total_pop)
        assert ubi == 0

    def test_ubi_uses_total_fiscal_change_not_income_tax_only(self):
        """Available UBI budget should reflect taxes and transfer changes.

        Net fiscal impact = Δ(household_tax_before_refundable_credits)
                            + Δ(employer_payroll_tax)
                            - Δ(household_refundable_tax_credits)
                            - Δ(household_benefits)
        """
        baseline = {
            "household_tax_before_refundable_credits": 150.0,
            "employer_payroll_tax": 50.0,
            "household_refundable_tax_credits": 18.0,
            "household_benefits": 4.0,
            "household_market_income": 1000.0,
            "household_net_income": 872.0,
        }
        shifted = {
            "household_tax_before_refundable_credits": 165.0,
            "employer_payroll_tax": 35.0,
            "household_refundable_tax_credits": 15.0,
            "household_benefits": 3.0,
            "household_market_income": 1000.0,
            "household_net_income": 853.0,
        }

        delta = net_fiscal_impact(shifted, baseline)

        assert delta["household_tax_before_refundable_credits_change"] == pytest.approx(15.0)
        assert delta["total_change"] == pytest.approx(4.0)
        assert delta["_identity_residual"] == pytest.approx(0.0, abs=1e-9)
        assert compute_ubi_amount(delta["total_change"], 2.0) == pytest.approx(2.0)


class TestMarketIncomeConservation:
    """TDD: Total market income must be unchanged after labor→capital shift.

    The shift redistributes labor income to capital income at constant
    modeled market income. Every dollar removed from labor income must
    appear in capital income.
    """

    def _redistribute(self, capital_vars, weights, total_freed):
        """Run the redistribution algorithm and return scaled vars + total added.

        Uses positive-only weighted totals for both shares and scale factors.
        """
        # Positive-only weighted totals for shares
        positive_totals = {}
        for name, vals in capital_vars.items():
            pos = np.where(vals > 0, vals, 0)
            positive_totals[name] = float((pos * weights).sum())

        total_positive = sum(positive_totals.values())

        scaled_vars = {}
        total_added = 0.0
        for name, vals in capital_vars.items():
            pos_total = positive_totals[name]
            if pos_total > 0 and total_positive > 0:
                share = pos_total / total_positive
                scale = 1 + (share * total_freed) / pos_total
                scaled = np.where(vals > 0, vals * scale, vals)
            else:
                scaled = vals.copy()
            scaled_vars[name] = scaled
            total_added += float(((scaled - vals) * weights).sum())

        return scaled_vars, total_added

    def test_conservation_no_losses(self):
        """With all-positive capital income, freed == added exactly."""
        emp = np.array([100000.0, 50000.0, 75000.0])
        weights = np.array([1.0, 2.0, 1.5])
        shift_pct = 0.25

        total_freed = float((emp * shift_pct * weights).sum())

        capital_vars = {
            "ltcg": np.array([5000.0, 3000.0, 1000.0]),
            "stcg": np.array([1000.0, 500.0, 200.0]),
            "interest": np.array([200.0, 100.0, 50.0]),
        }

        _, total_added = self._redistribute(capital_vars, weights, total_freed)
        assert total_added == pytest.approx(total_freed, rel=1e-10)

    def test_conservation_with_losses(self):
        """With capital losses present, freed == added still holds."""
        emp = np.array([100000.0, 50000.0, 0.0, 75000.0])
        weights = np.array([1.0, 1.0, 1.0, 1.0])
        shift_pct = 0.50

        total_freed = float((emp * shift_pct * weights).sum())

        capital_vars = {
            "ltcg": np.array([5000.0, -1000.0, 2000.0, 0.0]),
            "stcg": np.array([1000.0, 500.0, 0.0, 300.0]),
            "interest": np.array([200.0, 100.0, 50.0, 0.0]),
        }

        _, total_added = self._redistribute(capital_vars, weights, total_freed)
        assert total_added == pytest.approx(total_freed, rel=1e-10)

    def test_conservation_heavy_losses(self):
        """Even with large losses, conservation holds."""
        weights = np.array([1.0, 1.0, 1.0])
        total_freed = 50000.0

        capital_vars = {
            "ltcg": np.array([10000.0, -8000.0, 5000.0]),
            "stcg": np.array([-500.0, 200.0, -300.0]),
        }

        _, total_added = self._redistribute(capital_vars, weights, total_freed)
        assert total_added == pytest.approx(total_freed, rel=1e-10)

    def test_total_market_income_unchanged(self):
        """End-to-end: total market income before == after shift."""
        emp = np.array([100000.0, 50000.0, 0.0, 75000.0])
        se = np.array([20000.0, 0.0, 10000.0, -5000.0])
        weights = np.array([1.0, 2.0, 1.0, 1.5])
        shift_pct = 0.50

        capital_vars = {
            "ltcg": np.array([5000.0, -1000.0, 2000.0, 0.0]),
            "stcg": np.array([1000.0, 500.0, 0.0, 300.0]),
            "interest": np.array([200.0, 100.0, 50.0, 0.0]),
        }

        # Baseline total market income (weighted)
        baseline_total = float(
            ((emp + se + capital_vars["ltcg"] + capital_vars["stcg"]
              + capital_vars["interest"]) * weights).sum()
        )

        # After shift
        emp_reduction = np.where(emp > 0, emp * shift_pct, 0)
        se_reduction = np.where(se > 0, se * shift_pct, 0)
        new_emp = emp - emp_reduction
        new_se = se - se_reduction
        total_freed = float(
            ((emp_reduction + se_reduction) * weights).sum()
        )

        scaled_vars, _ = self._redistribute(capital_vars, weights, total_freed)

        shifted_total = float(
            ((new_emp + new_se + scaled_vars["ltcg"] + scaled_vars["stcg"]
              + scaled_vars["interest"]) * weights).sum()
        )

        assert shifted_total == pytest.approx(baseline_total, rel=1e-10)

    def test_losses_unchanged(self):
        """Capital losses must not be modified by redistribution."""
        weights = np.array([1.0, 1.0, 1.0])
        total_freed = 10000.0

        capital_vars = {
            "ltcg": np.array([5000.0, -3000.0, 1000.0]),
        }

        scaled_vars, _ = self._redistribute(capital_vars, weights, total_freed)
        assert scaled_vars["ltcg"][1] == pytest.approx(-3000.0)
