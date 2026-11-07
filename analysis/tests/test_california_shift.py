"""Tests for the California accounting in ``analysis.california_shift``.

The invariants, checked over generated household frames:

- ``_weighted_rank`` puts every household strictly inside (0, 1), and a
  household with a higher value always ranks higher;
- the four market-income groups partition California's households, so each
  field's group changes add up to the state total, and the groups' shares of
  labor and capital income each add up to one;
- households outside California never move California's rows;
- the change including SDI equals the net change plus the SDI change.

None of these tests load PolicyEngine.
"""

import json

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from analysis.california_shift import (
    GROUPS,
    STATE,
    _baseline_concentration,
    _california_rows,
    _weighted_rank,
)

VALUE_KEYS = (
    "market_income",
    "state_tax",
    "state_credits",
    "state_benefits",
    "labor",
    "capital",
    "sdi",
)


def _frame(state, weight, **columns):
    n = len(weight)
    frame = {
        "state": np.asarray(state).astype(str),
        "weight": np.asarray(weight, dtype=float),
    }
    for key in VALUE_KEYS:
        frame[key] = np.asarray(columns.get(key, np.zeros(n)), dtype=float)
    frame["state_net"] = frame["state_tax"] - frame["state_credits"] - frame["state_benefits"]
    return frame


FLOATS = st.floats(-1e6, 1e7, allow_nan=False, allow_infinity=False)
WEIGHTS = st.floats(0.5, 5_000, allow_nan=False, allow_infinity=False)


@st.composite
def household_pair(draw):
    """A baseline and scenario frame over the same households, at least one in CA."""
    n = draw(st.integers(1, 30))
    state = draw(st.lists(st.sampled_from([STATE, "NY", "TX"]), min_size=n, max_size=n))
    state[0] = STATE
    weight = draw(st.lists(WEIGHTS, min_size=n, max_size=n))

    def columns():
        return {key: draw(st.lists(FLOATS, min_size=n, max_size=n)) for key in VALUE_KEYS}

    return _frame(state, weight, **columns()), _frame(state, weight, **columns())


def test_weighted_rank_equal_weights_are_midpoints():
    ranks = _weighted_rank(np.array([30.0, 10.0, 40.0, 20.0]), np.ones(4))
    np.testing.assert_allclose(ranks, [0.625, 0.125, 0.875, 0.375])


@settings(max_examples=200, deadline=None)
@given(
    st.lists(st.tuples(FLOATS, WEIGHTS), min_size=1, max_size=40),
)
def test_weighted_rank_bounds_and_order(pairs):
    values = np.array([v for v, _ in pairs])
    weights = np.array([w for _, w in pairs])
    ranks = _weighted_rank(values, weights)
    assert np.all(ranks > 0) and np.all(ranks < 1)
    for i in range(len(values)):
        for j in range(len(values)):
            if values[i] < values[j]:
                assert ranks[i] < ranks[j]


def test_groups_cover_the_unit_interval():
    edges = [(lo, hi) for _, lo, hi in GROUPS]
    assert edges[0][0] == 0.0 and edges[-1][1] > 1.0
    for (_, hi), (lo, _) in zip(edges, edges[1:]):
        assert hi == lo


@settings(max_examples=200, deadline=None)
@given(household_pair())
def test_group_rows_add_up_to_the_state_total(pair):
    base, scen = pair
    total, groups = _california_rows(base, scen)
    assert [g["group"] for g in groups] == [label for label, _, _ in GROUPS]
    for key, value in total.items():
        parts = sum(g[key] for g in groups)
        assert parts == pytest.approx(value, rel=1e-9, abs=1e-12)
    assert total["state_net_including_sdi_change_b"] == pytest.approx(
        total["state_net_change_b"] + total["sdi_change_b"], rel=1e-12, abs=1e-15
    )


@settings(max_examples=200, deadline=None)
@given(household_pair(), st.floats(-1e6, 1e6, allow_nan=False))
def test_other_states_never_move_california(pair, shock):
    base, scen = pair
    total, groups = _california_rows(base, scen)
    shocked = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in scen.items()}
    outside = shocked["state"] != STATE
    for key in VALUE_KEYS + ("state_net",):
        shocked[key] = np.where(outside, shocked[key] + shock, shocked[key])
    total2, groups2 = _california_rows(base, shocked)
    assert total2 == total
    assert groups2 == groups


@settings(max_examples=200, deadline=None)
@given(household_pair())
def test_baseline_shares_add_up_to_one(pair):
    base, _ = pair
    mask = base["state"] == STATE
    labor = (np.clip(base["labor"][mask], 0, None) * base["weight"][mask]).sum()
    capital = (np.clip(base["capital"][mask], 0, None) * base["weight"][mask]).sum()
    with np.errstate(invalid="ignore", divide="ignore"):
        out = _baseline_concentration(base)
    groups = out["groups"]
    assert sum(g["households_m"] for g in groups) == pytest.approx(out["households_m"], rel=1e-9)
    if labor > 0:
        assert sum(g["labor_income_share"] for g in groups) == pytest.approx(1.0, rel=1e-9)
    if capital > 0:
        assert sum(g["capital_income_share"] for g in groups) == pytest.approx(1.0, rel=1e-9)


def test_california_rows_example():
    # Two California households and one in New York. The scenario moves $100
    # of labor income to $60 of capital income in the first household and
    # raises its state tax by $5; New York's changes must not count.
    base = _frame(
        [STATE, STATE, "NY"],
        [1e9, 1e9, 1e9],
        market_income=[100, 200, 300],
        labor=[100, 0, 50],
        capital=[0, 200, 0],
        state_tax=[1, 10, 3],
        sdi=[1.3, 0, 0],
    )
    scen = _frame(
        [STATE, STATE, "NY"],
        [1e9, 1e9, 1e9],
        market_income=[60, 200, 999],
        labor=[0, 0, 0],
        capital=[60, 200, 50],
        state_tax=[6, 10, 99],
        sdi=[0, 0, 0],
    )
    total, groups = _california_rows(base, scen)
    assert total["labor_income_change_b"] == pytest.approx(-100)
    assert total["capital_income_change_b"] == pytest.approx(60)
    assert total["state_net_change_b"] == pytest.approx(5)
    assert total["sdi_change_b"] == pytest.approx(-1.3)
    assert total["state_net_including_sdi_change_b"] == pytest.approx(3.7)


def test_household_order_change_is_refused():
    base = _frame([STATE, "NY"], [1.0, 1.0])
    scen = _frame(["NY", STATE], [1.0, 1.0])
    with pytest.raises(AssertionError):
        _california_rows(base, scen)


def test_chart_series_from_run(tmp_path):
    pytest.importorskip("matplotlib")
    from analysis.california_chart import series_from_run

    run = {
        "year": 2026,
        "metadata": {"policyengine_us_version": "9.9.9"},
        "levels": [
            {
                "shift_pct": 10,
                "other_states_net_change_b": -2.0,
                "california": {
                    "state_net_change_b": 5.0,
                    "state_net_including_sdi_change_b": 3.0,
                },
            }
        ],
    }
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run))
    xs, ca, ca_sdi, other, note = series_from_run(str(path))
    assert xs == [0, 10] and ca == [0.0, 5.0] and ca_sdi == [0.0, 3.0] and other == [0.0, -2.0]
    assert "9.9.9" in note
