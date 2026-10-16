"""The committed scenario run is the current inputs on the published runtime.

``analysis/outputs/ai_scenarios.json`` is the scenario grid on the Budget Lab's
revised (2026-10-09, AI-Fiscal v1.0.1) inputs.
``analysis/outputs/ai_scenarios_v1_0_0_inputs.json`` is the same grid on their
July inputs, with the same runtime, data and net-income accounting. Between
the two, only two inputs changed: the Moderate and Rapid 2030 labor shares, and
the CBO growth factor (1.0976 before, (1.022)(1.018)^4 after). So:

- the baseline is byte-for-byte the same;
- every row of the current run carries exactly the scenario this module builds
  today, so the file cannot be a stale run under current labels;
- every row of the July run carries the July labor shares and growth factor;
- cells the labor-share revision does not touch (Slow, and every shares-fixed
  counterfactual) move only by what a 5e-6 change in the growth factor can
  move them.
"""

import json
import math
from pathlib import Path

import pytest

from analysis.ai_scenarios import (
    CAPITAL_INCOME_VARS,
    CAPITAL_INCOME_VARS_EXCL_RETIREMENT,
    INEQUALITY_VARIANTS,
    AIScenario,
    build_scenario,
    default_scenario_grid,
)
from analysis.compare_scenario_vintages import (
    JULY_CBO_GROWTH_FACTOR,
    JULY_TARGET_LABOR_SHARES,
    labor_share_moved,
    vintage_rows,
)
from analysis.compute_ai_scenarios import REALIZATION_SWEEP

OUTPUTS = Path(__file__).resolve().parents[1] / "outputs"

#: $B. The growth factor moved by 5e-6 of itself, which moves g_Y by about
#: 5e-6 and so a cell of a few hundred billion dollars by well under a cent of
#: a billion per basis point of growth; 0.1 leaves room for float noise in
#: weighted totals without hiding a labor-share change, which moves Moderate
#: and Rapid cells by billions.
UNTOUCHED_TOL_B = 0.1


def _load(name):
    return json.loads((OUTPUTS / name).read_text())


@pytest.fixture(scope="module")
def before():
    return _load("ai_scenarios_v1_0_0_inputs.json")


@pytest.fixture(scope="module")
def after():
    return _load("ai_scenarios.json")


def _expected_current_scenarios():
    """What compute_ai_scenarios runs today, in the order it writes rows."""
    expected = [scenario.to_dict() for scenario in default_scenario_grid()]
    expected += [
        build_scenario("Rapid", inequality="proportional", realization_rate=rate).to_dict()
        for rate in REALIZATION_SWEEP
    ]
    expected += [
        build_scenario(name, inequality="proportional").to_dict()
        for name in ("Slow", "Moderate", "Rapid")
    ]
    return expected


def _scenario_rows(doc):
    rows = list(doc["scenarios"])
    for group in ("realization", "capital_scope_excluding_retirement"):
        rows += list(doc["sensitivities"][group])
    return rows


def test_same_runtime_data_and_accounting(before, after):
    for key in (
        "policyengine_version",
        "country_model_version",
        "certified_data_build_id",
        "certified_data_artifact_sha256",
        "net_income_excluded_benefits",
        "capital_income_vars",
    ):
        assert before["metadata"][key] == after["metadata"][key], key
    assert (
        before["metadata"]["runtime_fingerprint"]["digest"]
        == after["metadata"]["runtime_fingerprint"]["digest"]
    )


def test_baseline_is_identical(before, after):
    assert json.dumps(before["baseline"], sort_keys=True) == json.dumps(
        after["baseline"], sort_keys=True
    )


def test_rows_pair_one_to_one(before, after):
    pairs = vintage_rows(before, after)
    assert len(pairs) == 1 + len(_expected_current_scenarios())


def test_current_run_carries_the_scenarios_this_module_builds(after):
    rows = _scenario_rows(after)
    expected = _expected_current_scenarios()
    assert len(rows) == len(expected)
    for row, scenario in zip(rows, expected):
        # Exact: both sides are AIScenario.to_dict() from the same code, and
        # JSON round-trips a float's repr.
        assert row["scenario"] == scenario, row["scenario"]["label"]


def test_capital_scope_rows_used_the_narrower_capital_set(after):
    for row in after["sensitivities"]["capital_scope_excluding_retirement"]:
        assert row["diagnostics"]["capital_income_vars"] == list(
            CAPITAL_INCOME_VARS_EXCL_RETIREMENT
        )
    for row in after["scenarios"]:
        assert row["diagnostics"]["capital_income_vars"] == list(CAPITAL_INCOME_VARS)


def test_july_run_carries_the_july_inputs(before):
    for row in _scenario_rows(before):
        scenario = row["scenario"]
        assert scenario["target_labor_share"] == JULY_TARGET_LABOR_SHARES[
            scenario["name"]
        ]
        july = AIScenario(
            name=scenario["name"],
            annual_gdp_growth=scenario["annual_gdp_growth"],
            target_labor_share=scenario["target_labor_share"],
            inequality=scenario["inequality"],
            realization_rate=scenario["realization_rate"],
            hold_shares_fixed=scenario["hold_shares_fixed"],
            cbo_growth_factor=JULY_CBO_GROWTH_FACTOR,
        )
        assert math.isclose(scenario["gdp_growth"], july.gdp_growth, abs_tol=1e-15)
        assert math.isclose(
            scenario["capital_growth"], july.capital_growth, abs_tol=1e-15
        )


def test_only_the_reallocated_moderate_and_rapid_inputs_moved(before, after):
    for key, old, new in vintage_rows(before, after):
        if key == "baseline":
            continue
        s_old, s_new = old["scenario"], new["scenario"]
        for field in (
            "name",
            "label",
            "annual_gdp_growth",
            "inequality",
            "realization_rate",
            "hold_shares_fixed",
            "baseline_labor_share",
        ):
            assert s_old[field] == s_new[field], (key, field)
        if s_new["name"] == "Slow":
            assert s_old["target_labor_share"] == s_new["target_labor_share"], key
        else:
            assert s_old["target_labor_share"] != s_new["target_labor_share"], key


def test_cells_the_labor_share_revision_does_not_touch_barely_move(before, after):
    untouched = 0
    for key, old, new in vintage_rows(before, after):
        if key == "baseline" or labor_share_moved(new):
            continue
        untouched += 1
        assert abs(new["total_rev_change_b"] - old["total_rev_change_b"]) < (
            UNTOUCHED_TOL_B
        ), key
        assert abs(new["spm_poverty_rate"] - old["spm_poverty_rate"]) < 1e-4, key
    # Slow's three variants, its capital-scope row and the three shares-fixed
    # counterfactuals.
    assert untouched == 7


def test_the_revision_moves_every_reallocated_moderate_and_rapid_cell(before, after):
    moved = 0
    for key, old, new in vintage_rows(before, after):
        if key == "baseline" or not labor_share_moved(new):
            continue
        moved += 1
        assert abs(new["total_rev_change_b"] - old["total_rev_change_b"]) > 1.0, key
    # Moderate and Rapid in three variants, the five realization points and
    # two capital-scope rows.
    assert moved == 2 * len(INEQUALITY_VARIANTS) + len(REALIZATION_SWEEP) + 2
