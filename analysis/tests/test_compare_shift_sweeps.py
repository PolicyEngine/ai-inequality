"""Tests for analysis/compare_shift_sweeps.py.

Invariants:

* a sweep built the way analysis/compute_shift_sweep.py builds one passes
  check_sweep, and each identity check catches a row that breaks it;
* decompose's parts add up to the change in the total for any pair of runs,
  and decompose_state's to the change in a state's chart total;
* comparing a run with itself leaves nothing in ``same_definition``;
* once the site's sweep counts health coverage and TANF, it passes check_sweep.
"""

import copy
import json
import os
import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from analysis import compare_shift_sweeps as cmp

CODES = ("CA", "MA", "NY", "TX")


def _state_row(draw, code):
    tanf = draw(1)
    in_state_benefits = tanf if code == "MA" else 0.0
    d = {
        "state_tax_before_refundable_credits_change_b": draw(10),
        "state_refundable_credits_change_b": draw(2),
        "state_benefits_change_b": draw(2) + in_state_benefits,
        "tanf_change_b": tanf,
        "tanf_in_state_benefits_change_b": in_state_benefits,
        "state_health_change_b": draw(3),
    }
    d["tanf_state_charge_change_b"] = tanf - in_state_benefits
    d["state_net_excluding_health_tanf_change_b"] = (
        d["state_tax_before_refundable_credits_change_b"]
        - d["state_refundable_credits_change_b"]
        - d["state_benefits_change_b"]
    )
    d["state_net_change_b"] = (
        d["state_net_excluding_health_tanf_change_b"]
        - d["tanf_state_charge_change_b"]
        - d["state_health_change_b"]
    )
    return d


def synthetic_sweep(seed):
    """A sweep built the way compute_shift_sweep builds one, from seeded draws."""
    rng = random.Random(seed)
    rows = []
    for pct in cmp.SHIFT_GRID:
        scale = pct / 100

        def draw(size, scale=scale):
            return scale * rng.uniform(-size, size)

        states = {code: _state_row(draw, code) for code in CODES} if pct else {}
        row = {"shift_pct": pct, "state_deltas": states}
        for national, state_field in cmp.STATE_SUMS:
            row[national] = sum(d[state_field] for d in states.values())
        row["health_federal_change_b"] = draw(5)
        row["health_change_b"] = (
            row["health_federal_change_b"] + row["health_state_change_b"]
        )
        row["taxes_outside_charts_change_b"] = draw(1)
        row["chart_identity_residual_b"] = draw(0.05)
        row["total_rev_change_published_definition_b"] = draw(200)
        row["total_rev_change_excluding_health_b"] = (
            row["total_rev_change_published_definition_b"]
            + row["tanf_counted_twice_change_b"]
        )
        row["total_rev_change_b"] = (
            row["total_rev_change_excluding_health_b"] - row["health_change_b"]
        )
        row["revenue_change_b"] = row["total_rev_change_b"]
        rows.append(row)
    return {
        "metadata": {
            "code_commit": "9face79abc",
            "policyengine_bundle": {
                "model_version": "1.764.6",
                "net_income_excluded_benefits": ["early_head_start", "head_start"],
            },
            "baseline_facts": {"decile_impacts": [{"decile": 1}]},
            "health_tanf_programs": {"medicaid": {}},
        },
        "scenarios": rows,
    }


def earlier_sweep(seed):
    """A run in the earlier format, which counted neither health coverage nor TANF once."""
    rng = random.Random(seed)
    rows = []
    for pct in cmp.SHIFT_GRID:
        scale = pct / 100
        states = {}
        for code in CODES if pct else ():
            d = {
                "state_tax_before_refundable_credits_change_b": scale
                * rng.uniform(-10, 10),
                "state_refundable_credits_change_b": scale * rng.uniform(-2, 2),
                "state_benefits_change_b": scale * rng.uniform(-2, 2),
            }
            d["state_net_change_b"] = (
                d["state_tax_before_refundable_credits_change_b"]
                - d["state_refundable_credits_change_b"]
                - d["state_benefits_change_b"]
            )
            states[code] = d
        total = scale * rng.uniform(-200, 50)
        rows.append(
            {
                "shift_pct": pct,
                "revenue_change_b": total,
                "total_rev_change_b": total,
                "state_deltas": states,
            }
        )
    return {
        "metadata": {"policyengine_bundle": {"model_version": "1.764.6"}},
        "scenarios": rows,
    }


def test_a_well_built_sweep_passes():
    assert cmp.check_sweep(synthetic_sweep(1)) == []
    assert cmp.check_sweep(synthetic_sweep(1), expect_commit="9face79") == []


def _row(sweep, pct):
    return next(row for row in sweep["scenarios"] if row["shift_pct"] == pct)


def _drop_health(s):
    del _row(s, 50)["health_federal_change_b"]


def _skew_state_net(s):
    _row(s, 50)["state_deltas"]["CA"]["state_net_change_b"] += 0.5


def _skew_national_state_tax(s):
    _row(s, 50)["state_tax_before_refundable_credits_change_b"] += 0.01


def _large_residual(s):
    _row(s, 50)["chart_identity_residual_b"] = 0.2


def _skew_total(s):
    _row(s, 50)["total_rev_change_b"] += 1


def _skew_tanf_charge(s):
    _row(s, 50)["state_deltas"]["MA"]["tanf_state_charge_change_b"] += 0.1


def _drop_exclusion_record(s):
    del s["metadata"]["policyengine_bundle"]["net_income_excluded_benefits"]


def _drop_last_shift(s):
    s["scenarios"].pop()


def _nonzero_baseline(s):
    _row(s, 0)["health_federal_change_b"] = 0.5


def _drop_state_rows(s):
    _row(s, 50)["state_deltas"] = {}


def _drop_deciles(s):
    s["metadata"]["baseline_facts"] = {}


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (_drop_health, "no health_federal_change_b"),
        (_skew_state_net, "CA: state_net_change_b"),
        (
            _skew_national_state_tax,
            "the states' state_tax_before_refundable_credits_change_b",
        ),
        (_large_residual, "chart identity residual"),
        (_skew_total, "total_rev_change_b"),
        (_skew_tanf_charge, "MA: tanf_state_charge_change_b"),
        (_drop_exclusion_record, "net_income_excluded_benefits"),
        (_drop_last_shift, "shift grid"),
        (_nonzero_baseline, "0%: nonzero health_federal_change_b"),
        (_drop_state_rows, "50%: no state rows"),
        (_drop_deciles, "decile_impacts"),
    ],
)
def test_each_identity_check_catches_a_row_that_breaks_it(mutate, expected):
    sweep = synthetic_sweep(2)
    mutate(sweep)
    problems = cmp.check_sweep(sweep)
    assert any(expected in problem for problem in problems), problems


def test_a_mismatched_commit_fails():
    problems = cmp.check_sweep(synthetic_sweep(3), expect_commit="0000000")
    assert problems == ["metadata.code_commit 9face79abc doesn't match 0000000"]


@settings(max_examples=60, deadline=None)
@given(st.integers(0, 2**32 - 1), st.integers(0, 2**32 - 1))
def test_the_parts_add_up_to_the_change(new_seed, old_seed):
    new, old = synthetic_sweep(new_seed), earlier_sweep(old_seed)
    for part in cmp.decompose(new, old):
        assert abs(part["unexplained"]) < 1e-9
        assert part["total"] - part["earlier_total"] == pytest.approx(
            part["same_definition"] + part["tanf_counted_once"] + part["health"],
            abs=1e-9,
        )
    parts = cmp.decompose_state(new, old, "MA")
    assert [part["shift_pct"] for part in parts] == cmp.SHIFT_GRID[1:]
    for part in parts:
        assert abs(part["unexplained"]) < 1e-9


@settings(max_examples=30, deadline=None)
@given(st.integers(0, 2**32 - 1))
def test_a_run_compared_with_itself_moves_nothing_on_the_same_definition(seed):
    sweep = synthetic_sweep(seed)
    for part in cmp.decompose(sweep, sweep):
        assert part["same_definition"] == 0
    for part in cmp.decompose_state(sweep, sweep, "CA"):
        assert part["same_definition"] == 0


def test_chart_totals_and_the_residual_rebuild_the_total():
    for row in synthetic_sweep(4)["scenarios"]:
        charts = cmp.chart_totals(row)
        assert charts["federal"] + charts["states"] + charts["outside"] + row[
            "chart_identity_residual_b"
        ] == pytest.approx(row["total_rev_change_b"], abs=1e-9)


def test_report_and_main_run_on_a_pair_of_files(tmp_path, capsys):
    new_path, old_path = tmp_path / "new.json", tmp_path / "old.json"
    new_path.write_text(json.dumps(synthetic_sweep(5)))
    old_path.write_text(json.dumps(earlier_sweep(6)))
    assert (
        cmp.main([str(new_path), "--old", str(old_path), "--expect-commit", "9face79"])
        == 0
    )
    out = capsys.readouterr().out
    assert "Every identity holds." in out
    assert "| 100% |" in out and "CA chart" in out
    broken = synthetic_sweep(5)
    _skew_total(broken)
    new_path.write_text(json.dumps(broken))
    assert cmp.main([str(new_path), "--old", str(old_path)]) == 1


def test_metadata_differences_name_what_changed():
    new, old = synthetic_sweep(7), earlier_sweep(8)
    keys = [key for key, _, _ in cmp.metadata_differences(new, old)]
    assert "policyengine_bundle.net_income_excluded_benefits" in keys
    assert "policyengine_bundle.model_version" not in keys


SITE = os.path.join(cmp.ROOT, cmp.SITE_DATA)


def test_the_site_sweep_passes_once_it_counts_health_and_tanf():
    with open(SITE) as f:
        payload = json.load(f)
    if not any(
        row.get("health_federal_change_b") is not None for row in payload["scenarios"]
    ):
        pytest.skip("the site's sweep predates health coverage and TANF")
    assert cmp.check_sweep(copy.deepcopy(payload)) == []
