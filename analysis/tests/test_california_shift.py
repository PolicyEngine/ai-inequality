"""Tests for the California accounting in ``analysis.california_shift``.

The invariants, checked over generated household frames:

- ``_weighted_rank`` puts every household strictly inside (0, 1), and a
  household with a higher value always ranks higher;
- the four market-income groups partition California's households, so each
  field's group changes add up to the state total, and the groups' shares of
  labor and capital income each add up to one;
- households outside California never move California's rows;
- the change including SDI equals the net change plus the SDI change;
- the within-state shift conserves every state's market income: each state's
  capital income rises by exactly the labor income its residents give up, only
  positive capital income moves, and the national labor cut matches the
  published sweep's;
- with every record in one state, the within-state shift sets the same inputs
  as the published sweep's national shift (a differential check, run when
  policyengine_us is installed, plus a closed-form check that always runs).

Only the differential check against ``_apply_shift`` loads PolicyEngine.
"""

import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from analysis.california_shift import (
    CAPITAL_INCOME_VARS,
    GROUPS,
    LABOR_VARS,
    STATE,
    _apply_within_state_shift,
    _baseline_concentration,
    _california_rows,
    _freed_labor,
    _scale_by_state,
    _weighted_rank,
    _weighted_sum_by,
    _within_state_scales,
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


def test_chart_draws_california_only(tmp_path):
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    from analysis.california_chart import draw

    out = tmp_path / "chart.png"
    draw([0, 10, 50], [0.0, 5.0, 33.0], [0.0, 3.0, 22.0], None, str(out), "policyengine-us 9.9.9, 2026")
    fig = plt.gcf()
    labels = [line.get_label() for line in fig.axes[0].get_lines() if not line.get_label().startswith("_")]
    plt.close(fig)
    assert out.stat().st_size > 0
    assert labels == ["California", "California, including SDI contributions"]


COMPONENT_KEYS = (
    "household_tax_before_refundable_credits",
    "household_refundable_tax_credits",
    "household_benefits",
    "employer_payroll_tax",
    "fed_income_tax_before_refundable_credits",
    "employee_social_security_tax",
    "employee_medicare_tax",
    "employer_social_security_tax",
    "employer_medicare_tax",
    "self_employment_tax",
    "state_tax_before_refundable_credits",
    "state_refundable_credits",
    "state_benefits",
    "income_tax_refundable_credits",
    "household_market_income",
    "household_net_income",
)


@settings(max_examples=200, deadline=None)
@given(
    st.lists(FLOATS, min_size=len(COMPONENT_KEYS), max_size=len(COMPONENT_KEYS)),
    st.lists(FLOATS, min_size=len(COMPONENT_KEYS), max_size=len(COMPONENT_KEYS)),
)
def test_federal_and_state_parts_add_up_to_the_total(scenario, baseline):
    # Differential check: the summary's federal split, built from components,
    # plus the national state lines must equal fiscal.net_fiscal_impact's total.
    from analysis.california_summary import federal_split
    from analysis.fiscal import net_fiscal_impact

    delta = net_fiscal_impact(
        dict(zip(COMPONENT_KEYS, scenario)), dict(zip(COMPONENT_KEYS, baseline))
    )
    split = federal_split(delta)
    assert split["federal_net"] + split["states_net_national"] == pytest.approx(
        delta["total_change"], rel=1e-9, abs=1e-3
    )
    assert split["payroll"] == pytest.approx(
        split["employee_payroll"] + split["employer_payroll"], rel=1e-12, abs=1e-9
    )


def test_summary_reads_a_run():
    from analysis.california_summary import summarize

    ca = {
        "labor_income_change_b": -150.0,
        "capital_income_change_b": 170.0,
        "market_income_change_b": 20.0,
        "state_tax_before_refundable_credits_change_b": 5.5,
        "state_refundable_credits_change_b": 0.2,
        "state_benefits_change_b": 0.3,
        "state_net_change_b": 5.0,
        "sdi_change_b": -2.0,
        "state_net_including_sdi_change_b": 3.0,
    }
    group = dict(ca, group="Top 1%")
    run = {
        "year": 2026,
        "metadata": {"policyengine_version": "6.16.0", "policyengine_us_version": "2.2.1"},
        "baseline_california": {
            "households_m": 14.0,
            "labor_income_b": 1500.0,
            "capital_income_b": 400.0,
            "state_net_revenue_b": 120.0,
            "sdi_b": 20.0,
            "groups": [
                {
                    "group": "Top 1%",
                    "households_m": 0.14,
                    "labor_income_share": 0.15,
                    "capital_income_share": 0.5,
                    "mean_market_income": 3e6,
                }
            ],
        },
        "levels": [
            {
                "shift_pct": 10,
                "labor_income_moved_b": 1200.0,
                "all_government_change_b": -135.0,
                "all_states_net_change_b": 3.0,
                "federal_net_change_b": -138.0,
                "other_states_net_change_b": -2.0,
                "states_gaining": ["CA", "NY"],
                "states_losing_count": 40,
                "state_net_change_b": {"CA": 5.0, "NY": 2.0, "TX": -4.0},
                "national_components_b": {"total_change": -135.0},
                "california": ca,
                "california_by_group": [group],
            }
        ],
    }
    published = {10: {"california": 5.0, "other_states": -2.1, "federal": -138.2, "total": -135.3}}
    text = summarize(run, published)
    assert "California net +5.00B; with SDI +3.00B" in text
    assert "Published: California +5.00B (+0.0%)" in text
    assert "Within-state variant" not in text

    within_ca = dict(ca, state_net_change_b=3.5, market_income_change_b=0.0)
    run["within_state_levels"] = [
        dict(
            run["levels"][0],
            allocation="within_state",
            california=within_ca,
            california_by_group=[dict(within_ca, group="Top 1%")],
        )
    ]
    text = summarize(run, published)
    assert "Within-state variant" in text
    assert "+3.50B from income moving within the state and +1.50B from income moving in" in text
    assert "Five lowest changes: TX -4.00B" in text


# --- Within-state shift -------------------------------------------------------

INCOME_VARS = tuple(LABOR_VARS) + tuple(CAPITAL_INCOME_VARS)


class _Result:
    """Stands in for a MicroSeries: array values plus ``weights``."""

    def __init__(self, values, weights):
        self.values = np.asarray(values)
        self.weights = np.asarray(weights, dtype=float)

    def __array__(self, dtype=None, copy=None):
        return self.values if dtype is None else self.values.astype(dtype)


class _Branch:
    def __init__(self):
        self.inputs = {}

    def set_input(self, variable, period, values):
        self.inputs[variable] = np.array(values, dtype=float)


class _Sim:
    """A person-level microsimulation with the calls the shift functions make."""

    def __init__(self, state, weight, columns):
        self.state = np.asarray(state).astype(str)
        self.weight = np.asarray(weight, dtype=float)
        self.columns = {k: np.asarray(v, dtype=float) for k, v in columns.items()}
        person = SimpleNamespace(entity=SimpleNamespace(key="person"))
        self.tax_benefit_system = SimpleNamespace(variables={v: person for v in INCOME_VARS})
        self.branches = []

    def get_branch(self, name):
        branch = _Branch()
        self.branches.append(branch)
        return branch

    def calculate(self, variable, period=None, map_to=None):
        if variable == "state_code_str":
            assert map_to == "person"
            return _Result(self.state, self.weight)
        return _Result(self.columns[variable], self.weight)


INCOMES = st.floats(-2e5, 2e6, allow_nan=False, allow_infinity=False)
SHIFTS = st.floats(0.0, 1.0, allow_nan=False)


@st.composite
def person_sims(draw, states=("CA", "NY", "TX")):
    n = draw(st.integers(1, 25))
    state = draw(st.lists(st.sampled_from(list(states)), min_size=n, max_size=n))
    weight = draw(st.lists(WEIGHTS, min_size=n, max_size=n))
    columns = {v: draw(st.lists(INCOMES, min_size=n, max_size=n)) for v in INCOME_VARS}
    return _Sim(state, weight, columns)


def _by_state(sim, values):
    return _weighted_sum_by(sim.state, values, sim.weight)


def _positive_capital(sim):
    return sum(np.clip(sim.columns[v], 0, None) for v in CAPITAL_INCOME_VARS)


@settings(max_examples=300, deadline=None)
@given(person_sims(), SHIFTS)
def test_within_state_shift_conserves_each_state(sim, pct):
    freed = sum(_freed_labor(sim.columns[v], pct) for v in LABOR_VARS)
    freed_by_state = _by_state(sim, freed)
    capital_by_state = _by_state(sim, _positive_capital(sim))
    if any(f > 0 and capital_by_state.get(s, 0.0) <= 0 for s, f in freed_by_state.items()):
        with pytest.raises(ValueError):
            _apply_within_state_shift(sim, "t", pct)
        return

    branch, total, reported = _apply_within_state_shift(sim, "t", pct)
    out = branch.inputs
    assert set(out) == set(INCOME_VARS)
    assert total == pytest.approx(float((freed * sim.weight).sum()), rel=1e-12, abs=1e-6)
    assert reported == pytest.approx(freed_by_state, rel=1e-12, abs=1e-6)

    labor_change = sum(out[v] - sim.columns[v] for v in LABOR_VARS)
    capital_change = sum(out[v] - sim.columns[v] for v in CAPITAL_INCOME_VARS)
    held = _positive_capital(sim)
    for state in np.unique(sim.state):
        m = sim.state == state
        lost = float((labor_change[m] * sim.weight[m]).sum())
        gained = float((capital_change[m] * sim.weight[m]).sum())
        # Rounding scales with the dollars involved, capital included.
        size = float(((np.abs(labor_change[m]) + held[m]) * sim.weight[m]).sum())
        assert lost + gained == pytest.approx(0.0, abs=1e-9 * size + 1e-6)

    for v in CAPITAL_INCOME_VARS:
        before, after = sim.columns[v], out[v]
        # Zero and negative values stay put; positive ones never fall.
        np.testing.assert_array_equal(after[before <= 0], before[before <= 0])
        assert np.all(after[before > 0] >= before[before > 0])


@settings(max_examples=300, deadline=None)
@given(person_sims(), SHIFTS)
def test_within_state_scales_are_shared_across_capital_types(sim, pct):
    freed = _by_state(sim, sum(_freed_labor(sim.columns[v], pct) for v in LABOR_VARS))
    capital = _by_state(sim, _positive_capital(sim))
    assume(all(f <= 0 or capital.get(s, 0.0) > 0 for s, f in freed.items()))
    scales = _within_state_scales(freed, capital)
    assert all(s >= 1.0 for s in scales.values())
    for v in CAPITAL_INCOME_VARS:
        raw = sim.columns[v]
        scaled = _scale_by_state(raw, sim.state, scales)
        for state, scale in scales.items():
            m = (sim.state == state) & (raw > 0)
            np.testing.assert_allclose(scaled[m], raw[m] * scale, rtol=1e-12)


def test_within_state_scales_refuse_a_state_without_capital():
    with pytest.raises(ValueError, match="NY"):
        _within_state_scales({"CA": 10.0, "NY": 5.0}, {"CA": 100.0})
    assert _within_state_scales({"CA": 0.0}, {}) == {"CA": 1.0}


def test_within_state_shift_example():
    # A California worker gives up $100 of a $1,000 wage; the two California
    # capital holders split it 3:1 by holdings. New York's worker frees $50,
    # which goes to New York's only holder, not to California.
    sim = _Sim(
        ["CA", "CA", "CA", "NY", "NY"],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        {
            "employment_income": [1000, 0, 0, 500, 0],
            "self_employment_income": [0, 0, 0, 0, 0],
            "long_term_capital_gains": [0, 300, 100, 0, 40],
            "short_term_capital_gains": [0, 0, 0, 0, 0],
            "taxable_interest_income": [0, 0, 0, 0, 10],
            "qualified_dividend_income": [0, 0, 0, 0, 0],
            "non_qualified_dividend_income": [0, 0, 0, 0, 0],
            "rental_income": [0, 0, -50, 0, 0],
        },
    )
    branch, total, by_state = _apply_within_state_shift(sim, "t", 0.1)
    assert total == pytest.approx(150)
    assert by_state == pytest.approx({"CA": 100, "NY": 50})
    np.testing.assert_allclose(branch.inputs["employment_income"], [900, 0, 0, 450, 0])
    np.testing.assert_allclose(branch.inputs["long_term_capital_gains"], [0, 375, 125, 0, 80])
    np.testing.assert_allclose(branch.inputs["taxable_interest_income"], [0, 0, 0, 0, 20])
    np.testing.assert_allclose(branch.inputs["rental_income"], [0, 0, -50, 0, 0])


def _national_closed_form(sim, pct):
    """The published sweep's shift in closed form: one factor on all positive capital."""
    freed = sum(_freed_labor(sim.columns[v], pct) for v in LABOR_VARS)
    total_freed = float((freed * sim.weight).sum())
    total_capital = float((_positive_capital(sim) * sim.weight).sum())
    scale = 1.0 + total_freed / total_capital
    out = {v: sim.columns[v] - _freed_labor(sim.columns[v], pct) for v in LABOR_VARS}
    for v in CAPITAL_INCOME_VARS:
        raw = sim.columns[v]
        out[v] = np.where(raw > 0, raw * scale, raw)
    return out


@settings(max_examples=200, deadline=None)
@given(person_sims(states=("CA",)), SHIFTS)
def test_one_state_matches_the_national_shift_in_closed_form(sim, pct):
    assume(float((_positive_capital(sim) * sim.weight).sum()) > 0)
    branch, _, _ = _apply_within_state_shift(sim, "t", pct)
    expected = _national_closed_form(sim, pct)
    for v in INCOME_VARS:
        np.testing.assert_allclose(branch.inputs[v], expected[v], rtol=1e-12, atol=1e-9)


@settings(max_examples=100, deadline=None)
@given(person_sims(states=("CA",)), SHIFTS)
def test_one_state_matches_the_published_apply_shift(sim, pct):
    # Differential check against the code that produced the published sweep.
    pytest.importorskip("policyengine_us")
    from analysis.labor_capital_shift import _apply_shift

    assume(float((_positive_capital(sim) * sim.weight).sum()) > 0)
    within, total_w, _ = _apply_within_state_shift(sim, "w", pct)
    national, total_n = _apply_shift(sim, "n", pct)
    assert total_w == pytest.approx(total_n, rel=1e-12, abs=1e-9)
    for v in INCOME_VARS:
        expected = national.inputs.get(v, sim.columns[v])
        np.testing.assert_allclose(within.inputs[v], expected, rtol=1e-12, atol=1e-9)


def test_run_records_both_allocations(monkeypatch):
    # Wiring check for run(): fake every PolicyEngine call and confirm the output
    # carries national and within-state rows with the accounting fields.
    import analysis.california_shift as cs

    frame = _frame([STATE, "NY"], [1e9, 1e9], market_income=[10, 20], labor=[5, 5], capital=[2, 3])

    def fake_national(sim, name, pct):
        return _Branch(), 100e9 * pct

    def fake_within(sim, name, pct):
        return _Branch(), 100e9 * pct, {STATE: 60e9 * pct, "NY": 40e9 * pct}

    monkeypatch.setitem(
        sys.modules, "analysis.labor_capital_shift", SimpleNamespace(_apply_shift=fake_national)
    )
    monkeypatch.setattr(cs, "_apply_within_state_shift", fake_within)
    monkeypatch.setattr(cs, "policyengine_bundle", lambda sim: {"policyengine_version": "test"})
    monkeypatch.setattr(cs, "revenue_components", lambda sim: {"total": 1.0})
    monkeypatch.setattr(cs, "net_fiscal_impact", lambda rev, base: {"total_change": -5e9})
    monkeypatch.setattr(cs, "state_revenue_components", lambda sim: {})
    monkeypatch.setattr(
        cs,
        "state_revenue_delta",
        lambda scen, base: {STATE: {"state_net_change": 2e9}, "NY": {"state_net_change": -1e9}},
    )
    monkeypatch.setattr(cs, "_household_frame", lambda sim: frame)

    # One California household leaves three of the four groups empty, so their
    # mean income divides by zero; the real data fills every group.
    with np.errstate(invalid="ignore", divide="ignore"):
        out = cs.run([0.1, 0.5], microsim_factory=lambda: object(), verbose=True,
                     within_state_levels=[0.1])
    assert [r["shift_pct"] for r in out["levels"]] == [10, 50]
    assert [r["allocation"] for r in out["levels"]] == ["national", "national"]
    (row,) = out["within_state_levels"]
    assert row["allocation"] == "within_state" and row["shift_pct"] == 10
    assert row["labor_income_moved_b"] == pytest.approx(10.0)
    assert row["labor_income_moved_by_state_b"] == pytest.approx({STATE: 6.0, "NY": 4.0})
    assert row["federal_net_change_b"] == pytest.approx(-5.0 - 1.0)
    assert row["other_states_net_change_b"] == pytest.approx(-1.0)
    assert row["states_gaining"] == [STATE]
    assert out["metadata"]["policyengine_version"] == "test"
