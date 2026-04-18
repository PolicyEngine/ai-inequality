"""Regression tests for analysis helpers that previously mis-modeled scenarios."""

import importlib
import sys
import types

import numpy as np
import pandas as pd
import pytest


def _import_with_policyengine_stubs(module_name):
    """Import an analysis module without requiring PolicyEngine to be installed."""
    policyengine_us = types.ModuleType("policyengine_us")
    policyengine_us.Microsimulation = object
    sys.modules["policyengine_us"] = policyengine_us

    policyengine_core = types.ModuleType("policyengine_core")
    reforms = types.ModuleType("policyengine_core.reforms")

    class DummyReform:
        @staticmethod
        def from_dict(*args, **kwargs):
            return {"args": args, "kwargs": kwargs}

    reforms.Reform = DummyReform
    sys.modules["policyengine_core"] = policyengine_core
    sys.modules["policyengine_core.reforms"] = reforms

    module = importlib.import_module(module_name)
    return importlib.reload(module)


class FakeSeries:
    """Small stand-in for PolicyEngine's weighted MicroSeries."""

    def __init__(self, values, weights):
        self.values = np.asarray(values, dtype=float)
        self.weights = np.asarray(weights, dtype=float)

    def __array__(self, dtype=None, copy=None):
        array = np.asarray(self.values, dtype=dtype)
        return array.copy() if copy else array

    def sum(self):
        return float((self.values * self.weights).sum())

    def __mul__(self, other):
        return FakeSeries(self.values * other, self.weights)

    __rmul__ = __mul__

    def __sub__(self, other):
        return FakeSeries(self.values - np.asarray(other, dtype=float), self.weights)

    def __rsub__(self, other):
        return FakeSeries(np.asarray(other, dtype=float) - self.values, self.weights)

    def __add__(self, other):
        return FakeSeries(self.values + np.asarray(other, dtype=float), self.weights)

    __radd__ = __add__


class FakeBranch:
    def __init__(self):
        self.inputs = {}

    def set_input(self, var, year, values):
        self.inputs[var] = np.asarray(values, dtype=float)


class FakeSimulation:
    def __init__(self, series_by_var):
        self.series_by_var = series_by_var
        self.branch = FakeBranch()

    def get_branch(self, branch_name):
        return self.branch

    def calculate(self, var, period=None, map_to=None):
        return self.series_by_var[var]


def _capital_series_by_var(weights, overrides=None):
    overrides = overrides or {}
    base = {
        "long_term_capital_gains": FakeSeries([0.0, 0.0, 0.0], weights),
        "short_term_capital_gains": FakeSeries([0.0, 0.0, 0.0], weights),
        "taxable_interest_income": FakeSeries([0.0, 0.0, 0.0], weights),
        "qualified_dividend_income": FakeSeries([0.0, 0.0, 0.0], weights),
        "non_qualified_dividend_income": FakeSeries([0.0, 0.0, 0.0], weights),
        "rental_income": FakeSeries([0.0, 0.0, 0.0], weights),
    }
    base.update(overrides)
    return base


def test_apply_shift_conserves_labor_income_without_payroll_uplift():
    labor_shift = _import_with_policyengine_stubs("analysis.labor_capital_shift")

    weights = np.array([1.0, 2.0, 1.0])
    series = {
        "employment_income": FakeSeries([100.0, 50.0, 0.0], weights),
        "self_employment_income": FakeSeries([20.0, -10.0, 10.0], weights),
        **_capital_series_by_var(
            weights,
            overrides={
                "long_term_capital_gains": FakeSeries([10.0, -5.0, 5.0], weights),
                "qualified_dividend_income": FakeSeries([3.0, 1.0, 0.0], weights),
            },
        ),
    }
    baseline = FakeSimulation(series)

    branch, total_freed = labor_shift._apply_shift(baseline, "shift_50", 0.5)

    expected_freed = float(
        (
            (
                np.maximum(np.array(series["employment_income"]), 0)
                + np.maximum(np.array(series["self_employment_income"]), 0)
            )
            * 0.5
            * weights
        ).sum()
    )
    assert total_freed == pytest.approx(expected_freed)
    assert branch.inputs["employment_income"].tolist() == pytest.approx([50.0, 25.0, 0.0])
    assert branch.inputs["self_employment_income"].tolist() == pytest.approx([10.0, -10.0, 5.0])

    total_added = 0.0
    for var in labor_shift.CAPITAL_INCOME_VARS:
        original = np.array(series[var])
        shifted = branch.inputs.get(var, original)
        total_added += float(((shifted - original) * weights).sum())
    assert total_added == pytest.approx(total_freed)


def test_capital_share_uses_actual_positive_only_totals():
    capital_sweep = _import_with_policyengine_stubs("analysis.capital_share_sweep")

    weights = np.array([1.0, 1.0, 1.0])
    sim = FakeSimulation(
        {
            "household_market_income": FakeSeries([150.0, 100.0, 100.0], weights),
            **_capital_series_by_var(
                weights,
                overrides={
                    "long_term_capital_gains": FakeSeries([100.0, -10.0, 0.0], weights),
                },
            ),
        }
    )

    share = capital_sweep._capital_share(sim)
    assert share == pytest.approx(90.0 / 350.0)


def test_major_exposure_uses_detailed_employment_weights():
    occupation = _import_with_policyengine_stubs("analysis.compute_occupation_shock")

    tasks = pd.DataFrame(
        {
            "Task": ["High exposure task", "Low exposure task"],
            "O*NET-SOC Code": ["11-1011.00", "11-1021.00"],
            "pct": [1.0, 1.0],
        }
    )
    exposure = pd.DataFrame(
        {
            "task_name": ["High exposure task", "Low exposure task"],
            "directive": [0.7, 0.0],
            "feedback_loop": [0.2, 0.1],
        }
    )
    oes = pd.DataFrame(
        {
            "O_GROUP": ["detailed", "detailed", "major"],
            "OCC_CODE": ["11-1011", "11-1021", "11-0000"],
            "TOT_EMP": [10.0, 90.0, 100.0],
        }
    )

    exposures = occupation._build_major_exposure_from_frames(tasks, exposure, oes)
    assert exposures[11] == pytest.approx(0.18)


def test_shift_sweep_uses_fresh_simulation_for_each_shift_level():
    sweep = _import_with_policyengine_stubs("analysis.compute_shift_sweep")

    created = []

    class DummySim:
        def __init__(self):
            self.shift_pct = 0.0
            self.kind = "baseline"

    def factory():
        sim = DummySim()
        created.append(sim)
        return sim

    def fake_apply_shift(sim, branch_name, pct):
        sim.shift_pct = pct
        sim.kind = branch_name
        return sim, pct * 1_000

    def fake_extract_results(sim, label):
        pct = sim.shift_pct
        return {
            "net_gini": 0.60 + pct,
            "net_gini_including_health_benefits": 0.55 + pct,
            "market_gini": 0.70 + pct,
            "top_10_share": 0.45 + pct / 10,
            "top_1_share": 0.20 + pct / 20,
            "top_0_1_share": 0.10 + pct / 50,
            "market_top_10_share": 0.55 + pct / 10,
            "market_top_1_share": 0.30 + pct / 20,
            "market_top_0_1_share": 0.15 + pct / 50,
            "spm_poverty_rate": 0.20 + pct / 10,
            "fed_revenue": 2_000_000_000 + pct * 100_000_000,
        }

    def fake_revenue_components(sim):
        pct = sim.shift_pct
        # Minimal stub matching the new aggregate-based schema.
        return {
            "household_tax_before_refundable_credits": 2_000 + pct * 100,
            "household_refundable_tax_credits": 300 + pct * 20,
            "household_benefits": 800 + pct * 20,
            "employer_payroll_tax": 500 - pct * 50,
        }

    def fake_net_fiscal_impact(rev, base_rev):
        delta = {
            f"{k}_change": rev.get(k, 0) - base_rev.get(k, 0) for k in rev
        }
        delta["total_change"] = (
            delta["household_tax_before_refundable_credits_change"]
            + delta["employer_payroll_tax_change"]
            - delta["household_refundable_tax_credits_change"]
            - delta["household_benefits_change"]
        )
        delta["_identity_residual"] = 0.0
        return delta

    def fake_state_revenue_components(sim):
        return {}

    sweep._apply_shift = fake_apply_shift
    sweep._extract_results = fake_extract_results
    sweep.revenue_components = fake_revenue_components
    sweep.net_fiscal_impact = fake_net_fiscal_impact
    sweep.state_revenue_components = fake_state_revenue_components

    result = sweep.run_shift_sweep(
        shift_levels=[0.0, 0.1, 0.2],
        microsim_factory=factory,
        microdata_output_dir=None,
    )

    assert len(created) == 3
    assert [scenario["shift_pct"] for scenario in result["scenarios"]] == [0, 10, 20]
    assert [scenario["label"] for scenario in result["scenarios"]] == [
        "Baseline",
        "10% shift",
        "20% shift",
    ]
    assert result["scenarios"][0]["net_gini_including_health_benefits"] == pytest.approx(
        0.55
    )
    assert result["metadata"]["year"] == sweep.YEAR
    assert result["metadata"]["model_url"] == sweep.MODEL_URL
    assert result["metadata"]["policyengine_version"]
    assert result["metadata"]["policyengine_us_version"]
    assert result["scenarios"][0]["total_rev_change_b"] == pytest.approx(0.0)
    # At pct=0.1: Δtax=+10, Δrefundable=+2, Δbenefits=+2, Δemployer=-5
    # total = 10 + (-5) - 2 - 2 = +1
    assert result["scenarios"][1]["household_tax_change_b"] == pytest.approx(10 / 1e9)
    assert result["scenarios"][1]["total_rev_change_b"] == pytest.approx(1 / 1e9)
    # At pct=0.2: Δtax=+20, Δrefundable=+4, Δbenefits=+4, Δemployer=-10
    # total = 20 + (-10) - 4 - 4 = +2
    assert result["scenarios"][2]["total_rev_change_b"] == pytest.approx(2 / 1e9)
    # Legacy aliases still populated.
    assert result["scenarios"][1]["revenue_change_b"] == pytest.approx(
        result["scenarios"][1]["total_rev_change_b"]
    )
    assert created[0].kind == "baseline"
    assert created[1].kind == "sweep_10"
    assert created[2].kind == "sweep_20"
