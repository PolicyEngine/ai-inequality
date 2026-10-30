"""Unit tests for the AI scenario calibration and shock math.

No PolicyEngine dependency: everything here is the arithmetic that sits
between the published forecasts and the microsimulation inputs.
"""

import csv
import dataclasses
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from analysis.ai_scenarios import (
    BASELINE_LABOR_SHARE,
    CAPITAL_INCOME_VARS,
    CAPITAL_INCOME_VARS_EXCL_RETIREMENT,
    CBO_CUMULATIVE_GROWTH_FACTOR,
    INEQUALITY_VARIANTS,
    LABOR_INCOME_VARS,
    PASSTHROUGH_VAR,
    RETIREMENT_INCOME_VARS,
    SCENARIO_INPUTS,
    AIScenario,
    build_scenario,
    default_scenario_grid,
    rescale_labor_income,
)

# Published Table 1 from Iselin & Nunn, The Budget Lab, as revised 2026-10-09
# (AI-Fiscal v1.0.1): annual GDP growth, 2030 labor share, the three derived
# cumulative growth rates and the inequality parameter the report prints.
BUDGET_LAB_TABLE_1 = {
    "Slow": {
        "annual_gdp_growth": 0.020,
        "target_labor_share": 0.550,
        "gdp_growth": 0.0059,
        "capital_growth": 0.0172,
        "labor_growth": -0.0032,
        "lambda_compressive": 0.994,
        "lambda_expansive": 1.006,
    },
    "Moderate": {
        "annual_gdp_growth": 0.026,
        "target_labor_share": 0.540,
        "gdp_growth": 0.0358,
        "capital_growth": 0.0708,
        "labor_growth": 0.0078,
        "lambda_compressive": 0.964,
        "lambda_expansive": 1.036,
    },
    "Rapid": {
        "annual_gdp_growth": 0.033,
        "target_labor_share": 0.520,
        "gdp_growth": 0.0717,
        "capital_growth": 0.1560,
        "labor_growth": 0.0041,
        "lambda_compressive": 0.928,
        "lambda_expansive": 1.072,
    },
}

# The same table as first published on 2026-07-20 (AI-Fiscal v1.0.0), when the
# labor shares came from the Total column of Karger et al. Table 39. Kept so
# the calibration constants are pinned against both vintages: only the
# Moderate and Rapid labor shares, and what follows from them, differ.
BUDGET_LAB_TABLE_1_JULY = {
    "Slow": BUDGET_LAB_TABLE_1["Slow"],
    "Moderate": {
        **BUDGET_LAB_TABLE_1["Moderate"],
        "target_labor_share": 0.538,
        "capital_growth": 0.0754,
        "labor_growth": 0.0041,
    },
    "Rapid": {
        **BUDGET_LAB_TABLE_1["Rapid"],
        "target_labor_share": 0.513,
        "capital_growth": 0.1728,
        "labor_growth": -0.0094,
    },
}

VINTAGES = {"2026-10-09": BUDGET_LAB_TABLE_1, "2026-07-20": BUDGET_LAB_TABLE_1_JULY}

# The report rounds to two decimal places in percent, so agreement to half a
# basis point is as close as the published table can pin us.
TOLERANCE = 5e-5

#: Per-cell shock parameters The Budget Lab commits for both releases, from
#: AI-Fiscal (github.com/Budget-Lab-Yale/AI-Fiscal, MIT) at 1c25162c9aae,
#: results/erratum_v1.0.1/comparison/cell_params_2030.csv: columns A (v1.0.0
#: as published) and D (v1.0.1), metrics g_y, g_k, g_l, lambda and the factor
#: shares. These are their R code's own values at full precision.
AI_FISCAL_CELL_PARAMS = Path(__file__).parent / "fixtures" / "ai_fiscal_cell_params_2030.csv"
AI_FISCAL_VARIANTS = {"S": "Slow", "M": "Moderate", "R": "Rapid"}
AI_FISCAL_LABOR = {"S0": "proportional", "S2": "compressive", "S3": "expansive"}


def _scenario_for(name, table, **overrides):
    """A scenario with the given vintage's inputs."""
    inputs = table[name]
    return build_scenario(
        name,
        annual_gdp_growth=inputs["annual_gdp_growth"],
        target_labor_share=inputs["target_labor_share"],
        **overrides,
    )


def _ai_fiscal_cells():
    with open(AI_FISCAL_CELL_PARAMS, newline="") as handle:
        rows = list(csv.DictReader(handle))
    cells = {}
    for row in rows:
        key = (row["variant"], row["share_mode"], row["labor_scenario"])
        for release in ("v1_0_0", "v1_0_1"):
            value = row[release]
            cells.setdefault((release, *key), {})[row["metric"]] = (
                float(value) if value else None
            )
    return cells


class TestCalibration:
    """The calibration constants must reproduce both published vintages."""

    def test_scenario_inputs_match_the_revised_survey_values(self):
        for name, expected in BUDGET_LAB_TABLE_1.items():
            scenario = build_scenario(name)
            assert scenario.annual_gdp_growth == expected["annual_gdp_growth"]
            assert scenario.target_labor_share == expected["target_labor_share"]

    def test_cbo_growth_factor_is_the_stated_cbo_path(self):
        """2.2% in 2026, 1.8% a year after: the path the report states."""
        assert CBO_CUMULATIVE_GROWTH_FACTOR == pytest.approx(
            1.022 * 1.018**4, abs=1e-15
        )

    @pytest.mark.parametrize("vintage", sorted(VINTAGES))
    def test_calibration_reproduces_budget_lab_table_1(self, vintage):
        """All nine derived growth rates, in each vintage of the table."""
        table = VINTAGES[vintage]
        for name, expected in table.items():
            scenario = _scenario_for(name, table)
            assert scenario.gdp_growth == pytest.approx(
                expected["gdp_growth"], abs=TOLERANCE
            ), f"{vintage} {name} GDP growth"
            assert scenario.capital_growth == pytest.approx(
                expected["capital_growth"], abs=TOLERANCE
            ), f"{vintage} {name} capital growth"
            assert scenario.labor_growth == pytest.approx(
                expected["labor_growth"], abs=TOLERANCE
            ), f"{vintage} {name} labor growth"

    @pytest.mark.parametrize("vintage", sorted(VINTAGES))
    def test_inequality_lambda_reproduces_published_values(self, vintage):
        table = VINTAGES[vintage]
        for name, expected in table.items():
            compressive = _scenario_for(name, table, inequality="compressive")
            expansive = _scenario_for(name, table, inequality="expansive")
            assert compressive.inequality_lambda == pytest.approx(
                expected["lambda_compressive"], abs=1e-3
            ), f"{vintage} {name} compressive lambda"
            assert expansive.inequality_lambda == pytest.approx(
                expected["lambda_expansive"], abs=1e-3
            ), f"{vintage} {name} expansive lambda"

    def test_matches_ai_fiscal_cell_params_to_machine_precision(self):
        """Differential test against The Budget Lab's own R implementation.

        Every one of their 18 cells in both releases: Slow, Moderate and Rapid,
        reallocated (R) and fixed-share (F), under each labor scenario.
        """
        cells = _ai_fiscal_cells()
        assert len(cells) == 2 * 3 * 2 * 3
        for (release, variant, mode, labor), expected in cells.items():
            scenario = AIScenario(
                name=AI_FISCAL_VARIANTS[variant],
                annual_gdp_growth=SCENARIO_INPUTS[AI_FISCAL_VARIANTS[variant]][
                    "annual_gdp_growth"
                ],
                # Fixed-share cells record theta_1_L = theta_0_L; the module
                # ignores the target there, so either value is fine.
                target_labor_share=expected["theta_1_L"],
                inequality=AI_FISCAL_LABOR[labor],
                hold_shares_fixed=mode == "F",
            )
            label = (release, variant, mode, labor)
            assert scenario.baseline_labor_share == expected["theta_0_L"], label
            assert scenario.gdp_growth == pytest.approx(expected["g_y"], abs=1e-12), label
            assert scenario.capital_growth == pytest.approx(
                expected["g_k"], abs=1e-12
            ), label
            assert scenario.labor_growth == pytest.approx(
                expected["g_l"], abs=1e-12
            ), label
            if expected["lambda"] is None:
                assert scenario.inequality_lambda == 1.0, label
            else:
                assert scenario.inequality_lambda == pytest.approx(
                    expected["lambda"], abs=1e-12
                ), label

    def test_ai_fiscal_v1_0_1_targets_are_our_scenario_inputs(self):
        """Their reallocated-cell labor shares are the ones this module runs."""
        cells = _ai_fiscal_cells()
        for variant, name in AI_FISCAL_VARIANTS.items():
            committed = cells[("v1_0_1", variant, "R", "S0")]["theta_1_L"]
            assert SCENARIO_INPUTS[name]["target_labor_share"] == pytest.approx(
                committed, abs=1e-12
            ), name

    @pytest.mark.parametrize("vintage", sorted(VINTAGES))
    def test_recovered_constants_are_the_least_squares_fit(self, vintage):
        """Guard against someone nudging the constants to fix one scenario.

        Re-derives the CBO growth factor from the published GDP growth rates,
        and the pre-shock labor share from the published capital and labor
        growth rates, and checks the module constants are the best fit.
        """
        table = VINTAGES[vintage]

        def sse_growth(factor):
            return sum(
                ((1 + e["annual_gdp_growth"]) ** 5 / factor - 1 - e["gdp_growth"]) ** 2
                for e in table.values()
            )

        def sse_share(theta_l0):
            theta_k0 = 1 - theta_l0
            total = 0.0
            for expected in table.values():
                gy = (
                    1 + expected["annual_gdp_growth"]
                ) ** 5 / CBO_CUMULATIVE_GROWTH_FACTOR - 1
                theta_l1 = expected["target_labor_share"]
                gk = ((1 - theta_l1) * (1 + gy) - theta_k0) / theta_k0
                gl = (theta_l1 * (1 + gy) - theta_l0) / theta_l0
                total += (gk - expected["capital_growth"]) ** 2
                total += (gl - expected["labor_growth"]) ** 2
            return total

        factors = np.linspace(1.09, 1.11, 20001)
        best_factor = float(factors[int(np.argmin([sse_growth(f) for f in factors]))])
        assert best_factor == pytest.approx(CBO_CUMULATIVE_GROWTH_FACTOR, abs=1e-4)

        grid = np.linspace(0.50, 0.60, 10001)
        best = float(grid[int(np.argmin([sse_share(t) for t in grid]))])
        assert best == pytest.approx(BASELINE_LABOR_SHARE, abs=1e-4)

    def test_labor_and_capital_shares_sum_to_one(self):
        scenario = build_scenario("Rapid")
        assert scenario.baseline_labor_share + scenario.baseline_capital_share == 1
        assert scenario.target_labor_share + scenario.target_capital_share == 1

    def test_labor_income_falls_only_in_the_slow_scenario(self):
        """The revised report: labor income shrinks 0.3% in Slow and grows
        0.8% and 0.4% in Moderate and Rapid, where the labor share decline is
        small relative to GDP growth. Under the July inputs Rapid fell 0.9%.
        """
        assert build_scenario("Slow").labor_growth < 0
        assert build_scenario("Moderate").labor_growth > 0
        assert build_scenario("Rapid").labor_growth > 0
        july_rapid = _scenario_for("Rapid", BUDGET_LAB_TABLE_1_JULY)
        assert july_rapid.labor_growth < 0

    def test_capital_growth_exceeds_gdp_growth_in_every_scenario(self):
        for name in BUDGET_LAB_TABLE_1:
            scenario = build_scenario(name)
            assert scenario.capital_growth > scenario.gdp_growth


SHARES = st.floats(min_value=0.30, max_value=0.80, allow_nan=False)
GROWTH = st.floats(min_value=-0.02, max_value=0.08, allow_nan=False)


class TestCalibrationProperties:
    """Identities the factor split must satisfy for any inputs."""

    @given(annual=GROWTH, theta_l0=SHARES, theta_l1=SHARES)
    def test_factor_growth_rates_add_up_to_gdp_growth(self, annual, theta_l0, theta_l1):
        """Factor income is conserved: theta0_K g_K + theta0_L g_L = g_Y."""
        scenario = AIScenario(
            name="Rapid",
            annual_gdp_growth=annual,
            target_labor_share=theta_l1,
            baseline_labor_share=theta_l0,
        )
        weighted = (
            scenario.baseline_capital_share * scenario.capital_growth
            + scenario.baseline_labor_share * scenario.labor_growth
        )
        assert weighted == pytest.approx(scenario.gdp_growth, abs=1e-12)

    @given(annual=GROWTH, theta_l0=SHARES, theta_l1=SHARES)
    def test_post_shock_shares_are_the_targets(self, annual, theta_l0, theta_l1):
        """Labor's post-shock share of grown factor income is theta1_L."""
        scenario = AIScenario(
            name="Rapid",
            annual_gdp_growth=annual,
            target_labor_share=theta_l1,
            baseline_labor_share=theta_l0,
        )
        labor = theta_l0 * (1 + scenario.labor_growth)
        total = 1 + scenario.gdp_growth
        assert labor / total == pytest.approx(theta_l1, abs=1e-12)

    @given(annual=GROWTH, low=SHARES, high=SHARES)
    def test_a_lower_labor_share_moves_growth_from_labor_to_capital(
        self, annual, low, high
    ):
        if low >= high:
            low, high = high, low
        if high - low < 1e-6:
            return
        lower = AIScenario("Rapid", annual, target_labor_share=low)
        higher = AIScenario("Rapid", annual, target_labor_share=high)
        assert lower.capital_growth > higher.capital_growth
        assert lower.labor_growth < higher.labor_growth
        assert lower.gdp_growth == higher.gdp_growth

    @given(annual=GROWTH, theta_l1=SHARES)
    def test_fixed_shares_ignore_the_target_labor_share(self, annual, theta_l1):
        scenario = AIScenario(
            "Rapid", annual, target_labor_share=theta_l1, hold_shares_fixed=True
        )
        assert scenario.capital_growth == scenario.gdp_growth
        assert scenario.labor_growth == scenario.gdp_growth

    @given(annual=GROWTH, theta_l1=SHARES)
    def test_compressive_and_expansive_lambdas_are_symmetric(self, annual, theta_l1):
        compressive = AIScenario(
            "Rapid", annual, target_labor_share=theta_l1, inequality="compressive"
        )
        expansive = AIScenario(
            "Rapid", annual, target_labor_share=theta_l1, inequality="expansive"
        )
        assert compressive.inequality_lambda + expansive.inequality_lambda == (
            pytest.approx(2.0, abs=1e-15)
        )


class TestScenarioVariants:
    def test_hold_shares_fixed_grows_both_factors_at_gdp_rate(self):
        scenario = build_scenario("Rapid", hold_shares_fixed=True)
        assert scenario.labor_growth == pytest.approx(scenario.gdp_growth)
        assert scenario.capital_growth == pytest.approx(scenario.gdp_growth)

    def test_hold_shares_fixed_raises_labor_growth(self):
        """The counterfactual exists to show what the tilt costs labor."""
        tilted = build_scenario("Rapid")
        fixed = build_scenario("Rapid", hold_shares_fixed=True)
        assert fixed.labor_growth > tilted.labor_growth
        assert fixed.capital_growth < tilted.capital_growth

    def test_realization_rate_scales_capital_growth_only(self):
        full = build_scenario("Rapid", realization_rate=1.0)
        half = build_scenario("Rapid", realization_rate=0.5)
        assert half.capital_growth == pytest.approx(full.capital_growth)
        assert half.effective_capital_growth == pytest.approx(
            full.effective_capital_growth / 2
        )
        assert half.labor_growth == pytest.approx(full.labor_growth)

    def test_zero_realization_removes_the_capital_shock(self):
        scenario = build_scenario("Rapid", realization_rate=0.0)
        assert scenario.effective_capital_growth == 0.0

    def test_proportional_and_none_have_unit_lambda(self):
        assert build_scenario("Rapid", inequality="proportional").inequality_lambda == 1
        assert build_scenario("Rapid", inequality="none").inequality_lambda == 1

    def test_invalid_inequality_variant_raises(self):
        with pytest.raises(ValueError, match="inequality must be one of"):
            build_scenario("Rapid", inequality="sideways")

    def test_out_of_range_realization_rate_raises(self):
        with pytest.raises(ValueError, match="realization_rate"):
            build_scenario("Rapid", realization_rate=-0.5)

    def test_unknown_scenario_name_raises(self):
        with pytest.raises(KeyError, match="Unknown scenario"):
            build_scenario("Instantaneous")

    def test_default_grid_covers_every_scenario_and_variant(self):
        grid = default_scenario_grid()
        assert len(grid) == len(BUDGET_LAB_TABLE_1) * (len(INEQUALITY_VARIANTS) + 1)
        for name in BUDGET_LAB_TABLE_1:
            variants = {s.inequality for s in grid if s.name == name}
            assert variants == set(INEQUALITY_VARIANTS) | {"none"}
            assert sum(1 for s in grid if s.name == name and s.hold_shares_fixed) == 1

    def test_labels_are_unique_within_the_grid(self):
        labels = [s.label for s in default_scenario_grid()]
        assert len(labels) == len(set(labels))

    def test_to_dict_round_trips_derived_values(self):
        scenario = build_scenario("Moderate", inequality="expansive")
        payload = scenario.to_dict()
        assert payload["gdp_growth"] == pytest.approx(scenario.gdp_growth)
        assert payload["inequality_lambda"] == pytest.approx(scenario.inequality_lambda)
        assert payload["label"] == scenario.label


class TestLaborRescaling:
    """The log-spread transform that carries the inequality channel."""

    incomes = np.array([15_000.0, 42_000.0, 68_000.0, 150_000.0, 900_000.0])
    weights = np.array([3.0, 5.0, 4.0, 2.0, 1.0])

    def _aggregate(self, values):
        return float((values * self.weights).sum())

    def test_proportional_hits_target_aggregate(self):
        out = rescale_labor_income(self.incomes, self.weights, 0.05, 1.0)
        assert self._aggregate(out) == pytest.approx(
            self._aggregate(self.incomes) * 1.05
        )

    def test_proportional_scales_every_record_equally(self):
        out = rescale_labor_income(self.incomes, self.weights, 0.05, 1.0)
        np.testing.assert_allclose(out / self.incomes, 1.05)

    @pytest.mark.parametrize("lam", [0.90, 0.97, 1.03, 1.10])
    def test_spread_transform_hits_target_aggregate(self, lam):
        """mu1 must be pinned so the aggregate lands on target for any lambda."""
        out = rescale_labor_income(self.incomes, self.weights, -0.01, lam)
        assert self._aggregate(out) == pytest.approx(
            self._aggregate(self.incomes) * 0.99
        )

    def test_expansive_lambda_widens_the_log_distribution(self):
        out = rescale_labor_income(self.incomes, self.weights, 0.0, 1.10)
        before = np.std(np.log(self.incomes))
        after = np.std(np.log(out))
        assert after > before
        assert after == pytest.approx(before * 1.10)

    def test_compressive_lambda_narrows_the_log_distribution(self):
        out = rescale_labor_income(self.incomes, self.weights, 0.0, 0.90)
        before = np.std(np.log(self.incomes))
        after = np.std(np.log(out))
        assert after < before
        assert after == pytest.approx(before * 0.90)

    def test_expansive_lambda_raises_the_top_share(self):
        out = rescale_labor_income(self.incomes, self.weights, 0.0, 1.10)
        top_before = self.incomes[-1] * self.weights[-1] / self._aggregate(self.incomes)
        top_after = out[-1] * self.weights[-1] / self._aggregate(out)
        assert top_after > top_before

    def test_ordering_is_preserved(self):
        for lam in (0.90, 1.0, 1.10):
            out = rescale_labor_income(self.incomes, self.weights, 0.03, lam)
            assert np.all(np.diff(out) > 0)

    def test_nonpositive_values_pass_through_unchanged(self):
        values = np.array([-5_000.0, 0.0, 50_000.0])
        weights = np.array([1.0, 1.0, 1.0])
        out = rescale_labor_income(values, weights, 0.10, 1.05)
        assert out[0] == -5_000.0
        assert out[1] == 0.0
        assert out[2] != 50_000.0

    def test_target_aggregate_ignores_nonpositive_records(self):
        values = np.array([-5_000.0, 0.0, 50_000.0])
        weights = np.array([1.0, 1.0, 1.0])
        out = rescale_labor_income(values, weights, 0.10, 1.0)
        assert out[2] == pytest.approx(55_000.0)

    def test_all_nonpositive_input_is_a_no_op(self):
        values = np.array([-1_000.0, 0.0])
        weights = np.array([1.0, 1.0])
        out = rescale_labor_income(values, weights, 0.10, 1.05)
        np.testing.assert_array_equal(out, values)

    def test_input_array_is_not_mutated(self):
        original = self.incomes.copy()
        rescale_labor_income(self.incomes, self.weights, 0.05, 1.05)
        np.testing.assert_array_equal(self.incomes, original)

    def test_weights_affect_the_scale_factor(self):
        """Reweighting the top earner changes where the aggregate lands."""
        heavy = np.array([3.0, 5.0, 4.0, 2.0, 50.0])
        out_light = rescale_labor_income(self.incomes, self.weights, 0.0, 1.10)
        out_heavy = rescale_labor_income(self.incomes, heavy, 0.0, 1.10)
        assert not np.allclose(out_light, out_heavy)


class TestIncomeVariableSets:
    def test_labor_and_capital_sets_do_not_overlap(self):
        assert not set(LABOR_INCOME_VARS) & set(CAPITAL_INCOME_VARS)

    def test_passthrough_is_in_the_capital_set(self):
        """Its labor portion is handled inside the capital loop, not the labor one."""
        assert PASSTHROUGH_VAR in CAPITAL_INCOME_VARS
        assert PASSTHROUGH_VAR not in LABOR_INCOME_VARS

    def test_retirement_exclusion_removes_exactly_the_retirement_vars(self):
        assert set(CAPITAL_INCOME_VARS) - set(
            CAPITAL_INCOME_VARS_EXCL_RETIREMENT
        ) == set(RETIREMENT_INCOME_VARS)

    def test_capital_set_has_no_duplicates(self):
        assert len(CAPITAL_INCOME_VARS) == len(set(CAPITAL_INCOME_VARS))


class TestScenarioConstruction:
    def test_scenario_is_hashable_and_frozen(self):
        scenario = build_scenario("Rapid")
        assert hash(scenario) is not None
        with pytest.raises(dataclasses.FrozenInstanceError):
            scenario.name = "Other"

    def test_custom_baseline_share_changes_derived_growth(self):
        default = build_scenario("Rapid")
        alternative = AIScenario(
            name="Rapid",
            annual_gdp_growth=0.033,
            target_labor_share=0.520,
            baseline_labor_share=0.60,
        )
        assert alternative.capital_growth != pytest.approx(default.capital_growth)
