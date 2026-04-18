"""Tests for analysis.metrics.extract_results."""

import numpy as np
import pytest

from analysis.metrics import extract_results


def _weighted_gini(values, weights):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cumw = np.cumsum(weights)
    cumxw = np.cumsum(values * weights)
    total_w = cumw[-1]
    total_xw = cumxw[-1]
    if total_xw == 0:
        return 0.0
    pop = np.concatenate([[0.0], cumw / total_w])
    inc = np.concatenate([[0.0], cumxw / total_xw])
    area = np.trapezoid(inc, pop)
    return 1 - 2 * area


class FakeSeries:
    def __init__(self, values, weights):
        self.values = np.asarray(values, dtype=float)
        self.weights = np.asarray(weights, dtype=float)

    def __array__(self, dtype=None, copy=None):
        array = np.asarray(self.values, dtype=dtype)
        return array.copy() if copy else array

    def mean(self):
        return float((self.values * self.weights).sum() / self.weights.sum())

    def gini(self):
        return float(_weighted_gini(self.values, self.weights))

    def sum(self):
        return float((self.values * self.weights).sum())


class FakeSimulation:
    def __init__(self, series_by_var):
        self.series_by_var = series_by_var

    def calculate(self, var, period=None, map_to=None):
        return self.series_by_var[var]


def test_extract_results_includes_health_inclusive_resources():
    weights = np.ones(10)
    sim = FakeSimulation(
        {
            "household_net_income": FakeSeries(
                [100.0] * 9 + [300.0], weights
            ),
            "household_net_income_including_health_benefits": FakeSeries(
                [200.0] * 9 + [300.0], weights
            ),
            "household_market_income": FakeSeries([150.0] * 9 + [350.0], weights),
            "income_tax": FakeSeries([10.0] * 9 + [30.0], weights),
            "state_income_tax": FakeSeries([2.0] * 9 + [5.0], weights),
            "healthcare_benefit_value": FakeSeries([100.0] * 9 + [0.0], weights),
            "medicaid_cost": FakeSeries([70.0] * 9 + [0.0], weights),
            "per_capita_chip": FakeSeries([20.0] * 9 + [0.0], weights),
            "assigned_aca_ptc": FakeSeries([10.0] * 9 + [0.0], weights),
            "spm_unit_is_in_spm_poverty": FakeSeries([1.0] * 5 + [0.0] * 5, weights),
        }
    )

    results = extract_results(sim, "Test")

    assert results["mean_net_income"] == pytest.approx(120.0)
    assert results["mean_net_income_including_health_benefits"] == pytest.approx(
        210.0
    )
    assert results["top_10_share"] == pytest.approx(0.25)
    assert results["top_10_share_including_health_benefits"] == pytest.approx(
        300.0 / 2100.0
    )
    assert results["healthcare_benefit_value_total"] == pytest.approx(900.0)
    assert results["medicaid_cost_total"] == pytest.approx(630.0)
    assert results["chip_benefit_total"] == pytest.approx(180.0)
    assert results["aca_ptc_total"] == pytest.approx(90.0)


def test_extract_results_falls_back_to_aca_ptc_when_assigned_variant_missing():
    weights = np.ones(2)
    sim = FakeSimulation(
        {
            "household_net_income": FakeSeries([100.0, 200.0], weights),
            "household_net_income_including_health_benefits": FakeSeries(
                [110.0, 210.0], weights
            ),
            "household_market_income": FakeSeries([120.0, 220.0], weights),
            "income_tax": FakeSeries([10.0, 20.0], weights),
            "state_income_tax": FakeSeries([2.0, 4.0], weights),
            "healthcare_benefit_value": FakeSeries([10.0, 10.0], weights),
            "medicaid_cost": FakeSeries([7.0, 7.0], weights),
            "per_capita_chip": FakeSeries([2.0, 2.0], weights),
            "aca_ptc": FakeSeries([1.0, 1.0], weights),
            "spm_unit_is_in_spm_poverty": FakeSeries([0.0, 0.0], weights),
        }
    )

    results = extract_results(sim, "Fallback")

    assert results["aca_ptc_total"] == pytest.approx(2.0)
