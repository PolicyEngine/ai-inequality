"""Tests for analysis/revenue_lines.py and the src/data/revenueLines.json it writes.

Invariants:

* the committed file is what the script writes from the committed sweep, byte
  for byte, and the script runs as ``python3 -I`` with the standard library
  alone;
* at every shift the federal line, the states combined and the taxes outside
  both add up to all governments' change, counting health coverage and not
  counting it;
* each government's line counting health coverage is its line not counting it
  less its own health spending;
* the states combined equal the sweep's state_net_change_b added up;
* the taxes outside both lines are the Additional Medicare Tax, workers' state
  payroll taxes and local taxes on occupations;
* at a 10% shift the lines take the values the posts and the page quote;
* a sweep missing a field the lines read raises, rather than reading it as zero.
"""

import copy
import json
import os
import subprocess
import sys

import pytest

from analysis import revenue_lines as rl

SWEEP_PATH = os.path.join(rl.ROOT, rl.SWEEP)
OUTPUT_PATH = os.path.join(rl.ROOT, rl.OUTPUT)

#: Largest gap the two adding-up identities allow, in $B. The stored lines
#: miss all governments' change by the sweep's chart_identity_residual_b
#: (at most 1.1e-5, at 50%) plus the rounding of four stored values to six
#: decimals: 1.10e-5 counting health coverage and 1.20e-5 not counting it, both
#: at 50%. 1.2e-5 itself fails by float noise.
IDENTITY_TOLERANCE_B = 1.25e-5

#: Three stored values, each rounded to six decimals.
HEALTH_TOLERANCE_B = 1.5e-6

#: The tolerance compare_shift_sweeps.check_sweep holds the sweep's own
#: float64 identities to.
EXACT_B = 1e-6


def sweep_bytes():
    with open(SWEEP_PATH, "rb") as f:
        return f.read()


def sweep():
    return json.loads(sweep_bytes())


def stored():
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        return json.load(f)


def lines():
    return stored()["lines"]


def at(shift):
    return next(line for line in lines() if line["shift_pct"] == shift)


def test_the_committed_file_regenerates_byte_for_byte():
    with open(OUTPUT_PATH, "rb") as f:
        committed = f.read()
    assert rl.render(sweep_bytes()).encode("utf-8") == committed


def test_the_script_runs_isolated_and_finds_the_file_current():
    # -I keeps the user's site-packages and the script's folder off sys.path,
    # so this passes only on the standard library.
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            os.path.join("analysis", "revenue_lines.py"),
            "--check",
        ],
        cwd=rl.ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_the_file_records_which_sweep_it_came_from():
    provenance = stored()["provenance"]
    metadata = sweep()["metadata"]
    assert provenance["sweep_file"] == rl.SWEEP
    assert len(provenance["sweep_sha256"]) == 64
    for key in rl.PROVENANCE_FIELDS:
        assert provenance[key] == metadata[key]


def test_every_value_has_at_most_six_decimals():
    for line in lines():
        for key, value in line.items():
            assert value == round(value, rl.DECIMALS), (line["shift_pct"], key)


def test_the_file_covers_every_shift():
    assert [line["shift_pct"] for line in lines()] == rl.SHIFT_GRID


def test_the_baseline_row_is_all_zero():
    baseline = at(0)
    assert {key: value for key, value in baseline.items() if key != "shift_pct"} == {
        key: 0.0 for key in baseline if key != "shift_pct"
    }


@pytest.mark.parametrize("shift", rl.SHIFT_GRID)
def test_the_lines_add_up_to_all_governments(shift):
    line = at(shift)
    outside = line["taxes_outside_charts_change_b"]
    counting = (
        line["federal_counting_health_change_b"]
        + line["states_counting_health_change_b"]
        + outside
    )
    not_counting = (
        line["federal_not_counting_health_change_b"]
        + line["states_not_counting_health_change_b"]
        + outside
    )
    assert counting == pytest.approx(
        line["total_rev_change_b"], abs=IDENTITY_TOLERANCE_B
    )
    assert not_counting == pytest.approx(
        line["total_rev_change_excluding_health_b"], abs=IDENTITY_TOLERANCE_B
    )


@pytest.mark.parametrize("shift", rl.SHIFT_GRID)
def test_counting_is_not_counting_less_health(shift):
    line = at(shift)
    for government, health in (
        ("federal", "federal_health_change_b"),
        ("states", "state_health_change_b"),
    ):
        assert line[f"{government}_counting_health_change_b"] == pytest.approx(
            line[f"{government}_not_counting_health_change_b"] - line[health],
            abs=HEALTH_TOLERANCE_B,
        ), government


@pytest.mark.parametrize("shift", rl.SHIFT_GRID)
def test_the_states_combined_add_up_the_state_rows(shift):
    row = next(r for r in sweep()["scenarios"] if r["shift_pct"] == shift)
    states = (row["state_deltas"] or {}).values()
    summed = sum(d["state_net_change_b"] for d in states)
    assert at(shift)["states_counting_health_change_b"] == pytest.approx(
        summed, abs=EXACT_B
    )


@pytest.mark.parametrize("shift", rl.SHIFT_GRID)
def test_the_taxes_outside_both_lines_are_their_three_parts(shift):
    line = at(shift)
    parts = (
        line["additional_medicare_tax_change_b"]
        + line["employee_state_payroll_tax_change_b"]
        + line["local_occupational_tax_change_b"]
    )
    assert parts == pytest.approx(line["taxes_outside_charts_change_b"], abs=2e-6)


def test_the_ten_percent_values_the_page_quotes():
    line = at(10)
    expected = {
        "total_rev_change_b": -195.19,
        "total_rev_change_excluding_health_b": -129.01,
        "federal_counting_health_change_b": -172.10,
        "federal_not_counting_health_change_b": -124.15,
        "states_counting_health_change_b": -16.15,
        "states_not_counting_health_change_b": 2.08,
        "federal_health_change_b": 47.95,
        "state_health_change_b": 18.23,
        "taxes_outside_charts_change_b": -6.94,
        "california_income_and_use_tax_change_b": 5.12,
        "california_net_counting_health_change_b": 2.19,
    }
    assert {key: round(line[key], 2) for key in expected} == expected


def test_not_counting_health_leaves_tanf_in():
    # federalRow(_, false) and state_net_excluding_health_tanf_change_b also
    # move TANF, so they give -124.96 and +2.71 at 10%.
    line = at(10)
    row = next(r for r in sweep()["scenarios"] if r["shift_pct"] == 10)
    without_tanf = sum(
        d["state_net_excluding_health_tanf_change_b"]
        for d in row["state_deltas"].values()
    )
    assert round(without_tanf, 2) == 2.71
    assert round(line["states_not_counting_health_change_b"], 2) == 2.08
    federal_without_tanf = (
        line["federal_not_counting_health_change_b"] - row["tanf_change_b"]
    )
    assert round(federal_without_tanf, 2) == -124.96


def _without(path):
    """The committed sweep with the field at ``path`` removed, as bytes."""
    payload = copy.deepcopy(sweep())
    target = payload
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return json.dumps(payload).encode("utf-8")


@pytest.mark.parametrize(
    "path",
    [
        ("scenarios", 1, "federal_health_change_b"),
        ("scenarios", 1, "tanf_change_b"),
        ("scenarios", 5, "taxes_outside_charts_change_b"),
        ("scenarios", 0, "total_rev_change_b"),
        ("scenarios", 3, "state_deltas", "TX", "state_health_change_b"),
        ("scenarios", 3, "state_deltas", "WY", "tanf_in_state_benefits_change_b"),
        ("scenarios", 2, "state_deltas", "CA"),
        ("scenarios", 7, "state_deltas"),
        ("metadata", "code_commit"),
    ],
)
def test_a_sweep_missing_a_field_raises(path):
    with pytest.raises(rl.SweepError):
        rl.build(_without(path))


def test_a_null_field_raises():
    payload = copy.deepcopy(sweep())
    payload["scenarios"][4]["state_deltas"]["NY"]["state_health_change_b"] = None
    with pytest.raises(rl.SweepError):
        rl.build(json.dumps(payload).encode("utf-8"))


def test_a_baseline_row_with_changes_raises():
    payload = copy.deepcopy(sweep())
    payload["scenarios"][0]["federal_health_change_b"] = 1.0
    with pytest.raises(rl.SweepError):
        rl.build(json.dumps(payload).encode("utf-8"))


def test_a_sweep_off_the_shift_grid_raises():
    payload = copy.deepcopy(sweep())
    del payload["scenarios"][-1]
    with pytest.raises(rl.SweepError):
        rl.build(json.dumps(payload).encode("utf-8"))
