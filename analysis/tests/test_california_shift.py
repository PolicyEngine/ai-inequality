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
  policyengine_us is installed, plus a closed-form check that always runs);
- the health accounting conserves health spending: each household's state and
  federal health spending add up to every health program it counts, and moving
  state-only coverage changes who pays, not how much;
- the federal line with health and TANF, every state's line, and the state
  payroll and local taxes add up to the all-government total with health;
  TANF moves dollar for dollar from the federal line to the state's, and TANF
  a state's line already holds is charged once;
- the federal line, every state's line, and the state payroll and local taxes
  add up to the all-government total, and the summary's federal split adds up
  to the same total, with no residual when the aggregates hold only the parts
  policyengine-us builds them from;
- the state-only adjustment moves nothing for people whose status allows
  federal matching, never moves more than the federal share policyengine-us
  books, and never moves CHIP's unborn-child (FCEP) match;
- a shifted branch prices Medicaid at the baseline's cost per enrollee, so new
  enrollees add cost, and the pricing refuses a branch that already
  calculated its own;
- the federal immigration-status test matches policyengine-us's
  ``is_medicaid_immigration_status_eligible`` where no state coverage applies,
  the state-only adjustment moves exactly the federal share policyengine-us
  books for a California child covered without satisfactory status, it
  leaves the federal CHIP match for an undocumented pregnant woman's FCEP
  coverage in place, Medicaid priced at the baseline rises with enrollment
  over a four-household dataset where policyengine-us alone holds the state's
  total fixed, and the household frame drops Healthier Oregon's cost for an
  adult policyengine-us also enrolls in Medicaid (all run when
  policyengine_us is installed).

The differential checks against ``_apply_shift``, the immigration rules,
Medicaid pricing, the household frame and the tax aggregates are the only tests
that load PolicyEngine.
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
    FEDERAL_HEALTH,
    FEDERAL_SHARE_COSTS,
    FMAP_SPLIT_HEALTH,
    GROUPS,
    LABOR_VARS,
    LOCAL_TAXES,
    MEDICAID_DENOMINATOR,
    OTHER_TAX_VARIABLES,
    STATE,
    STATE_HEALTH,
    STATE_HEALTH_UNLISTED,
    STATE_PAYROLL_TAXES,
    STATE_SHARE_COSTS,
    _apply_within_state_shift,
    _baseline_concentration,
    _california_rows,
    _check_health_lists,
    _check_health_split,
    _federally_eligible_status,
    _freed_labor,
    _health_tanf_accounting,
    _outside_state_measure,
    _price_medicaid_at_baseline,
    _scale_by_state,
    _state_only_federal_share,
    _tanf_states_in_state_benefits,
    _weighted_rank,
    _weighted_sum_by,
    _with_derived,
    _within_state_scales,
)

VALUE_KEYS = (
    "market_income",
    "state_tax",
    "state_use_tax",
    "mental_health_services_tax",
    "state_credits",
    "state_benefits",
    "labor",
    "capital",
    "sdi",
    "federal_health_split",
    "state_health_split",
    "fmap_split_cost",
    "federal_health_other",
    "state_health_programs",
    "state_only_coverage",
    "healthier_oregon_overlap",
    "tanf",
    "tanf_in_state_benefits",
) + OTHER_TAX_VARIABLES


def _frame(state, weight, **columns):
    n = len(weight)
    frame = {
        "state": np.asarray(state).astype(str),
        "weight": np.asarray(weight, dtype=float),
    }
    for key in VALUE_KEYS:
        frame[key] = np.asarray(columns.get(key, np.zeros(n)), dtype=float)
    return _with_derived(frame)


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
                "other_states_net_with_health_tanf_change_b": -2.5,
                "california": {
                    "state_net_change_b": 5.0,
                    "state_net_including_sdi_change_b": 3.0,
                    "state_net_with_health_tanf_change_b": 4.0,
                    "state_net_with_health_tanf_including_sdi_change_b": 2.0,
                },
            }
        ],
    }
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run))
    xs, ca, ca_sdi, other, note = series_from_run(str(path), measure="study")
    assert xs == [0, 10] and ca == [0.0, 5.0] and ca_sdi == [0.0, 3.0] and other == [0.0, -2.0]
    assert "9.9.9" in note
    xs, ca, ca_sdi, other, _ = series_from_run(str(path))
    assert xs == [0, 10] and ca == [0.0, 4.0] and ca_sdi == [0.0, 2.0] and other == [0.0, -2.5]


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


def test_chart_titles_subtitles_and_formats():
    pytest.importorskip("matplotlib")
    from analysis.california_chart import (
        dollar_format,
        legend_location,
        subtitle_for,
        title_for,
    )

    assert title_for([0.0, 1.0, 5.0]) == "California gains as labor income shifts to capital"
    assert title_for([0.0, -1.0, -5.0]) == "California loses as labor income shifts to capital"
    assert title_for([0.0, 1.0, -5.0]) == "California's revenue as labor income shifts to capital"
    assert "Medi-Cal" in subtitle_for("with_health_tanf", True)
    assert "Medicaid and TANF" in subtitle_for("with_health_tanf", False)
    assert subtitle_for("study", False) == subtitle_for("study", True)
    assert dollar_format([0.0, 1.2, 3.4])(1.25) == "$1.2B"
    assert dollar_format([0.0, 12.0, 40.0])(12.4) == "$12B"
    assert dollar_format([0.0, -243.2, 47.2])(-243.2) == "−$243B"
    assert dollar_format([-1.0, 1.0])(-0.04) == "$0.0B"
    assert legend_location([0.0, -243.2, 47.2]) == "lower left"
    assert legend_location([0.0, -0.15, 47.2]) == "upper left"


@settings(max_examples=200, deadline=None)
@given(
    st.lists(st.floats(-1e4, 1e4), min_size=1, max_size=8),
    st.floats(-1e4, 1e4),
)
def test_dollar_format_signs_only_a_nonzero_amount_and_puts_the_sign_first(values, value):
    pytest.importorskip("matplotlib")
    from analysis.california_chart import dollar_format

    text = dollar_format(values)(value)
    amount = float(text.removeprefix("−").removeprefix("$").removesuffix("B").replace(",", ""))
    assert "-" not in text
    assert text.startswith("−") == (value < 0 and amount > 0)


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
    "additional_medicare_tax",
    "employer_federal_unemployment_tax",
    "employee_state_payroll_tax",
    "employer_state_payroll_tax",
    "employer_local_payroll_tax",
    "local_income_tax_before_refundable_credits",
    "local_occupational_tax",
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
    assert split["federal_net"] + split["states_net_national"] + split["state_payroll"] + split[
        "local"
    ] == pytest.approx(delta["total_change"], rel=1e-9, abs=1e-3)
    assert split["payroll"] == pytest.approx(
        split["employee_payroll"] + split["employer_payroll"], rel=1e-12, abs=1e-9
    )


#: The parts of household tax and employer payroll tax, as policyengine-us
#: builds them (``test_federal_split_parts_match_policyengine`` checks this).
HOUSEHOLD_TAX_PARTS = (
    "fed_income_tax_before_refundable_credits",
    "employee_social_security_tax",
    "employee_medicare_tax",
    "additional_medicare_tax",
    "employee_state_payroll_tax",
    "self_employment_tax",
    "state_tax_before_refundable_credits",
    "local_income_tax_before_refundable_credits",
    "local_occupational_tax",
)
EMPLOYER_TAX_PARTS = (
    "employer_social_security_tax",
    "employer_medicare_tax",
    "employer_federal_unemployment_tax",
    "employer_state_payroll_tax",
    "employer_local_payroll_tax",
)


@settings(max_examples=200, deadline=None)
@given(
    st.lists(FLOATS, min_size=len(HOUSEHOLD_TAX_PARTS + EMPLOYER_TAX_PARTS),
             max_size=len(HOUSEHOLD_TAX_PARTS + EMPLOYER_TAX_PARTS)),
    st.lists(FLOATS, min_size=4, max_size=4),
)
def test_federal_split_leaves_no_residual(parts, transfers):
    # When household tax and employer payroll tax hold only their parts, the
    # split puts every dollar in a named line, and the federal line is the
    # all-government total less the states, state payroll and local taxes.
    from analysis.california_summary import federal_split

    c = {f"{k}_change": v for k, v in zip(HOUSEHOLD_TAX_PARTS + EMPLOYER_TAX_PARTS, parts)}
    c["household_tax_before_refundable_credits_change"] = sum(
        c[f"{k}_change"] for k in HOUSEHOLD_TAX_PARTS
    )
    c["employer_payroll_tax_change"] = sum(c[f"{k}_change"] for k in EMPLOYER_TAX_PARTS)
    credits, state_credits, benefits, state_benefits = transfers
    c.update(
        household_refundable_tax_credits_change=credits,
        state_refundable_credits_change=state_credits,
        household_benefits_change=benefits,
        state_benefits_change=state_benefits,
    )
    total = (
        c["household_tax_before_refundable_credits_change"]
        + c["employer_payroll_tax_change"]
        - credits
        - benefits
    )
    split = federal_split(c)
    scale = 1e-9 * (sum(abs(v) for v in parts) + sum(abs(v) for v in transfers)) + 1e-6
    assert abs(split["residual"]) <= scale and abs(split["employer_residual"]) <= scale
    federal = total - split["states_net_national"] - split["state_payroll"] - split["local"]
    assert split["federal_net"] == pytest.approx(federal, rel=1e-9, abs=scale)


def test_federal_split_parts_match_policyengine():
    # Differential check: the parts the summary's federal split assumes are
    # exactly those policyengine-us adds into its tax aggregates.
    pytest.importorskip("policyengine_us")
    from policyengine_us.variables.gov.irs.tax.payroll.employee_payroll_tax import (
        EMPLOYEE_PAYROLL_TAX_COMPONENTS,
    )
    from policyengine_us.variables.gov.irs.tax.payroll.employer_payroll_tax import (
        EMPLOYER_PAYROLL_TAX_COMPONENTS,
    )
    from policyengine_us.variables.household.income.household.household_tax_before_refundable_credits import (
        household_tax_before_refundable_credits,
    )

    assert set(household_tax_before_refundable_credits.adds) == {
        "employee_payroll_tax",
        "self_employment_tax",
        "income_tax_before_refundable_credits",
        "flat_tax",  # zero under current law; the split's residual holds it
        "household_state_tax_before_refundable_credits",
        "local_income_tax_before_refundable_credits",
        "local_occupational_tax",
    }
    assert set(EMPLOYEE_PAYROLL_TAX_COMPONENTS) == {
        "employee_social_security_tax",
        "employee_medicare_tax",
        "additional_medicare_tax",
        "employee_state_payroll_tax",
    }
    assert set(EMPLOYER_PAYROLL_TAX_COMPONENTS) == set(EMPLOYER_TAX_PARTS)
    assert set(STATE_PAYROLL_TAXES) | set(LOCAL_TAXES) <= set(HOUSEHOLD_TAX_PARTS) | set(
        EMPLOYER_TAX_PARTS
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
        "state_health_change_b": 0.6,
        "state_health_split_change_b": 0.4,
        "state_only_coverage_change_b": 0.15,
        "state_health_programs_change_b": 0.05,
        "tanf_change_b": 0.4,
        "state_net_with_health_tanf_change_b": 4.0,
        "state_net_with_health_tanf_including_sdi_change_b": 2.0,
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
                "other_states_net_with_health_tanf_change_b": -3.0,
                "states_losing_with_health_tanf_count": 42,
                "federal_net_with_health_tanf_change_b": -140.0,
                "all_government_with_health_change_b": -139.0,
                "health_federal_change_b": 3.0,
                "health_state_change_b": 1.0,
                "tanf_change_b": 1.0,
            }
        ],
    }
    published = {10: {"california": 5.0, "other_states": -2.1, "federal": -138.2, "total": -135.3}}
    text = summarize(run, published)
    assert "California net +5.00B; with SDI +3.00B" in text
    assert "California with health and TANF +4.00B; with SDI +2.00B" in text
    assert "state-only coverage +0.15B" in text and "CalWORKs +0.40B" in text
    assert "With health and TANF: other states -3.00B (42 losing); federal -140.0B" in text
    assert "(with health and TANF +4.00B)" in text
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
    assert "+3.50B from income moving within the state and +1.50B from income moving between states" in text
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

    def get_holder(self, variable):
        known = [period for period in ["2026"] if variable in self.inputs]
        return SimpleNamespace(get_known_periods=lambda: known)


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
    branches = []

    def fake_national(sim, name, pct):
        branches.append(_Branch())
        return branches[-1], 100e9 * pct

    def fake_within(sim, name, pct):
        branches.append(_Branch())
        return branches[-1], 100e9 * pct, {STATE: 60e9 * pct, "NY": 40e9 * pct}

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
    monkeypatch.setattr(cs, "_medicaid_denominator", lambda sim: np.array([7.0, 8.0, 9.0]))

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
    # The fake changes no health spending or TANF, so those fields match the sweep's.
    assert row["federal_net_with_health_tanf_change_b"] == pytest.approx(row["federal_net_change_b"])
    assert row["other_states_net_with_health_tanf_change_b"] == pytest.approx(-1.0)
    assert row["california"]["state_net_with_health_tanf_change_b"] == pytest.approx(0.0)
    assert "state_net_with_health_tanf_b" in out["baseline_california"]
    # Every shifted branch, national and within-state, prices Medicaid at the baseline.
    assert len(branches) == 3
    for branch in branches:
        np.testing.assert_array_equal(branch.inputs[MEDICAID_DENOMINATOR], [7.0, 8.0, 9.0])


def test_level_row_keeps_state_payroll_and_local_taxes_off_the_federal_line(monkeypatch):
    # California's employer UI tax rises $1B, a New York city wage tax $0.5B and
    # the additional Medicare tax $0.25B. The all-government total counts all
    # three, no state's line holds the first two, and only the last is federal.
    import analysis.california_shift as cs

    base = _frame([STATE, "NY"], [1e9, 1e9])
    scen = _frame(
        [STATE, "NY"],
        [1e9, 1e9],
        employer_state_payroll_tax=[1.0, 0.0],
        local_income_tax_before_refundable_credits=[0.0, 0.5],
        additional_medicare_tax=[0.25, 0.0],
    )
    monkeypatch.setattr(cs, "revenue_components", lambda sim: {})
    monkeypatch.setattr(cs, "net_fiscal_impact", lambda rev, base: {"total_change": 1.75e9})
    monkeypatch.setattr(cs, "state_revenue_components", lambda sim: {})
    monkeypatch.setattr(
        cs,
        "state_revenue_delta",
        lambda scen_states, base_states: {
            STATE: {"state_net_change": 0.0},
            "NY": {"state_net_change": 0.0},
        },
    )
    monkeypatch.setattr(cs, "_household_frame", lambda sim: scen)
    with np.errstate(invalid="ignore", divide="ignore"):
        row = cs._level_row(object(), 0.0, 0.1, base, {}, {}, "national")
    assert row["state_payroll_tax_change_b"] == pytest.approx(1.0)
    assert row["local_tax_change_b"] == pytest.approx(0.5)
    assert row["federal_net_change_b"] == pytest.approx(0.25)
    assert row["federal_net_published_definition_change_b"] == pytest.approx(1.75)
    assert row["federal_net_with_health_tanf_change_b"] == pytest.approx(0.25)
    assert row["national_components_b"]["additional_medicare_tax_change"] == pytest.approx(0.25)
    assert row["california"]["state_payroll_tax_change_b"] == pytest.approx(1.0)
    assert row["california"]["local_tax_change_b"] == pytest.approx(0.0)


# --- Health spending and TANF -------------------------------------------------

HEALTH_KEYS = (
    "federal_health_split",
    "state_health_split",
    "federal_health_other",
    "state_health_programs",
    "tanf",
)
SPENDING = st.floats(0, 5e4, allow_nan=False, allow_infinity=False)
SHARES = st.floats(0, 1, allow_nan=False)


@st.composite
def health_pair(draw):
    """Baseline and scenario frames with non-negative health spending, at least one in CA."""
    n = draw(st.integers(1, 30))
    # Massachusetts's state benefits already hold its TAFDC.
    state = draw(st.lists(st.sampled_from([STATE, "NY", "TX", "MA"]), min_size=n, max_size=n))
    state[0] = STATE
    weight = draw(st.lists(WEIGHTS, min_size=n, max_size=n))

    def columns():
        cols = {
            key: np.asarray(draw(st.lists(SPENDING, min_size=n, max_size=n))) for key in HEALTH_KEYS
        }
        # State-only coverage moves part of the federal share, never more.
        share = np.asarray(draw(st.lists(SHARES, min_size=n, max_size=n)))
        cols["state_only_coverage"] = cols["federal_health_split"] * share
        cols["fmap_split_cost"] = cols["federal_health_split"] + cols["state_health_split"]
        cols["state_tax"] = draw(st.lists(FLOATS, min_size=n, max_size=n))
        cols["tanf_in_state_benefits"] = np.where(np.asarray(state) == "MA", cols["tanf"], 0.0)
        for key in OTHER_TAX_VARIABLES:
            cols[key] = draw(st.lists(FLOATS, min_size=n, max_size=n))
        return cols

    return _frame(state, weight, **columns()), _frame(state, weight, **columns())


@settings(max_examples=300, deadline=None)
@given(health_pair())
def test_health_spending_is_conserved(pair):
    for frame in pair:
        every_program = (
            frame["federal_health_split"]
            + frame["state_health_split"]
            + frame["federal_health_other"]
            + frame["state_health_programs"]
        )
        np.testing.assert_allclose(
            frame["state_health"] + frame["federal_health"], every_program, rtol=1e-12, atol=1e-6
        )
        # A state's line pays the TANF it doesn't already hold, and only that.
        np.testing.assert_allclose(
            frame["state_net_with_health_tanf"],
            frame["state_net"]
            - frame["state_health"]
            - np.where(frame["state"] == "MA", 0.0, frame["tanf"]),
            rtol=1e-12,
            atol=1e-6,
        )
        # Generated frames satisfy the run's own checks.
        _check_health_split(frame)


@settings(max_examples=300, deadline=None)
@given(
    health_pair(),
    st.floats(-50, 50, allow_nan=False),
    st.floats(-500, 500, allow_nan=False),
    st.floats(-50, 50, allow_nan=False),
)
def test_health_tanf_accounting_adds_up(pair, ca_net, all_government, ny_net):
    base, scen = pair
    out = _health_tanf_accounting(base, scen, {STATE: ca_net, "NY": ny_net}, all_government)
    states = out["state_net_with_health_tanf_change_b"]
    outside = _outside_state_measure(base, scen)
    assert out["federal_net_with_health_tanf_change_b"] + sum(states.values()) + outside[
        "state_payroll_tax_change_b"
    ] + outside["local_tax_change_b"] == pytest.approx(
        out["all_government_with_health_change_b"], rel=1e-9, abs=1e-6
    )
    assert out["all_states_net_with_health_tanf_change_b"] == pytest.approx(
        sum(states.values()), rel=1e-12, abs=1e-12
    )
    # California's line is the sweep's net less California's health and TANF
    # changes, as its household rows count them.
    total, _ = _california_rows(base, scen)
    assert states[STATE] == pytest.approx(
        ca_net - total["state_health_change_b"] - total["tanf_change_b"], rel=1e-9, abs=1e-9
    )
    # Every health dollar leaves the all-government total; TANF already sits in
    # it, twice where a state's line also holds it, and once here.
    w = base["weight"]
    health = lambda f: f["state_health"] + f["federal_health"]  # noqa: E731
    health_change = float(((health(scen) - health(base)) * w).sum()) / 1e9
    twice = float(((scen["tanf_in_state_benefits"] - base["tanf_in_state_benefits"]) * w).sum()) / 1e9
    assert out["all_government_with_health_change_b"] == pytest.approx(
        all_government - health_change + twice, rel=1e-9, abs=1e-6
    )
    assert out["tanf_counted_twice_change_b"] == pytest.approx(twice, rel=1e-9, abs=1e-9)


def test_tanf_moves_from_the_federal_line_to_the_state():
    # CalWORKs rises $1B and nothing else changes. The sweep counts the $1B in
    # all-government benefits but in no state's line, so its federal line falls
    # $1B; here California pays it and the federal line does not move.
    base = _frame([STATE, "NY"], [1e9, 1e9])
    scen = _frame([STATE, "NY"], [1e9, 1e9], tanf=[1.0, 0.0])
    out = _health_tanf_accounting(base, scen, {STATE: 0.0, "NY": 0.0}, -1.0)
    assert out["state_net_with_health_tanf_change_b"][STATE] == pytest.approx(-1.0)
    assert out["federal_net_with_health_tanf_change_b"] == pytest.approx(0.0)
    assert out["tanf_change_b"] == pytest.approx(1.0)


def test_tanf_a_state_line_already_holds_is_charged_once():
    # Massachusetts's TAFDC rises $1B. Its state benefits hold TAFDC, so the
    # sweep's Massachusetts line already falls $1B, and the all-government total
    # counts the $1B twice (in tanf and in state benefits). Here Massachusetts
    # pays it once, the all-government total counts it once, and the federal
    # line does not move.
    base = _frame(["MA", STATE], [1e9, 1e9])
    scen = _frame(["MA", STATE], [1e9, 1e9], tanf=[1.0, 0.0], tanf_in_state_benefits=[1.0, 0.0])
    out = _health_tanf_accounting(base, scen, {"MA": -1.0, STATE: 0.0}, -2.0)
    assert out["state_net_with_health_tanf_change_b"]["MA"] == pytest.approx(-1.0)
    assert out["all_government_with_health_change_b"] == pytest.approx(-1.0)
    assert out["federal_net_with_health_tanf_change_b"] == pytest.approx(0.0)
    assert out["tanf_change_b"] == pytest.approx(1.0)
    assert out["tanf_counted_twice_change_b"] == pytest.approx(1.0)


def test_tanf_states_in_state_benefits():
    programs = ["ca_tanf", "ma_tafdc", "ny_tanf", "vt_reach_up"]
    assert _tanf_states_in_state_benefits(programs, ["ma_tafdc", "ca_capi", "ma_eaedc"]) == ["MA"]
    assert _tanf_states_in_state_benefits(programs, ["ca_capi"]) == []
    assert _tanf_states_in_state_benefits(programs, ["vt_reach_up", "ma_tafdc"]) == ["MA", "VT"]


def test_state_only_coverage_moves_to_the_state():
    # A California child newly covered by state-funded Medi-Cal costs $1,000.
    # policyengine-us books $500 federal and $500 state at the 50% matching
    # rate; the child's status rules out federal matching, so California pays
    # all of it and the federal line does not move.
    base = _frame([STATE], [1e9])
    scen = _frame(
        [STATE],
        [1e9],
        fmap_split_cost=[1000.0],
        federal_health_split=[500.0],
        state_health_split=[500.0],
        state_only_coverage=[500.0],
    )
    _check_health_split(scen)
    out = _health_tanf_accounting(base, scen, {STATE: 0.0}, 0.0)
    assert out["state_net_with_health_tanf_change_b"][STATE] == pytest.approx(-1000.0)
    assert out["health_federal_change_b"] == pytest.approx(0.0)
    assert out["federal_net_with_health_tanf_change_b"] == pytest.approx(0.0)
    assert out["all_government_with_health_change_b"] == pytest.approx(-1000.0)


def test_check_health_split_refuses_gaps():
    gap = _frame(
        [STATE], [1.0], fmap_split_cost=[100.0], federal_health_split=[50.0], state_health_split=[40.0]
    )
    with pytest.raises(AssertionError, match="differ"):
        _check_health_split(gap)
    overmoved = _frame(
        [STATE],
        [1.0],
        fmap_split_cost=[100.0],
        federal_health_split=[50.0],
        state_health_split=[50.0],
        state_only_coverage=[60.0],
    )
    with pytest.raises(AssertionError, match="moves more"):
        _check_health_split(overmoved)


LISTED_HEALTH = list(FMAP_SPLIT_HEALTH) + list(FEDERAL_HEALTH) + list(STATE_HEALTH)
EVERY_HEALTH = LISTED_HEALTH + list(STATE_HEALTH_UNLISTED)


def _health_parameters(flag=False, health=None, federal=None, state=None, state_benefits=None):
    household = SimpleNamespace(
        household_health_benefits=health or LISTED_HEALTH,
        federal_benefit_cost=federal or list(FEDERAL_SHARE_COSTS),
        state_benefit_cost=state or list(STATE_SHARE_COSTS),
        household_state_benefits=state_benefits or ["ca_capi", "ma_tafdc"],
    )
    simulation = SimpleNamespace(include_health_benefits_in_net_income=flag)
    return SimpleNamespace(gov=SimpleNamespace(household=household, simulation=simulation))


def test_check_health_lists():
    _check_health_lists(_health_parameters(), EVERY_HEALTH)
    # Releases after policyengine-us 2.2.1 list the five state subsidies in
    # household_health_benefits too; the classification is the same.
    _check_health_lists(_health_parameters(health=EVERY_HEALTH), EVERY_HEALTH)
    # That longer list gets the same checks.
    with pytest.raises(ValueError, match="new_program"):
        _check_health_lists(_health_parameters(health=EVERY_HEALTH + ["new_program"]), EVERY_HEALTH)
    dropped = LISTED_HEALTH[0]
    with pytest.raises(ValueError, match=f"missing.*{dropped}"):
        _check_health_lists(
            _health_parameters(health=[p for p in EVERY_HEALTH if p != dropped]), EVERY_HEALTH
        )
    with pytest.raises(ValueError, match="twice"):
        _check_health_lists(_health_parameters(flag=True), EVERY_HEALTH)
    with pytest.raises(ValueError, match="new_program"):
        _check_health_lists(_health_parameters(health=LISTED_HEALTH + ["new_program"]), EVERY_HEALTH)
    # A health program policyengine-us values but this module doesn't classify.
    with pytest.raises(ValueError, match="healthcare_benefit_value.*new_subsidy"):
        _check_health_lists(_health_parameters(), EVERY_HEALTH + ["new_subsidy"])
    with pytest.raises(ValueError, match="missing.*wa_cascade_care_savings"):
        _check_health_lists(_health_parameters(), EVERY_HEALTH[:-1])
    with pytest.raises(ValueError, match="state_benefit_cost"):
        _check_health_lists(_health_parameters(state=["medicaid_state_cost"]), EVERY_HEALTH)
    # A health program the state measure already nets would count twice.
    with pytest.raises(ValueError, match="ma_connector_care"):
        _check_health_lists(
            _health_parameters(state_benefits=["ca_capi", "ma_connector_care"]), EVERY_HEALTH
        )


def test_federally_eligible_status_examples():
    p = SimpleNamespace(
        eligible_immigration_statuses=["CITIZEN", "LEGAL_PERMANENT_RESIDENT", "REFUGEE"],
        bar_exempt_immigration_statuses=["REFUGEE"],
        five_year_bar_years=5,
    )
    statuses = [
        "CITIZEN",
        "LEGAL_PERMANENT_RESIDENT",
        "LEGAL_PERMANENT_RESIDENT",
        "REFUGEE",
        "UNDOCUMENTED",
        "DACA",
        "TPS",
    ]
    years = [0, 5, 2, 0, 20, 20, 20]
    got = _federally_eligible_status(statuses, years, p)
    assert got.tolist() == [True, True, False, True, False, False, False]


def _situation(state, people):
    return {
        "people": people,
        "households": {"household": {"members": list(people), "state_code": {2026: state}}},
    }


def test_federally_eligible_status_matches_policyengine():
    pytest.importorskip("policyengine_us")
    from policyengine_us import Simulation

    statuses = [
        "CITIZEN",
        "LEGAL_PERMANENT_RESIDENT",
        "LEGAL_PERMANENT_RESIDENT",
        "REFUGEE",
        "ASYLEE",
        "UNDOCUMENTED",
        "DACA",
        "TPS",
        "PAROLED_ONE_YEAR",
        "PAROLED_ONE_YEAR",
    ]
    years = [0, 7, 1, 0, 2, 12, 12, 12, 6, 2]
    people = {
        f"p{i}": {
            "age": {2026: 40},
            "immigration_status": {2026: s},
            "years_since_us_entry": {2026: y},
        }
        for i, (s, y) in enumerate(zip(statuses, years))
    }
    # Texas covers no one without satisfactory status, so policyengine-us's
    # variable reduces to its federal branch there.
    sim = Simulation(situation=_situation("TX", people))
    expected = np.asarray(sim.calculate("is_medicaid_immigration_status_eligible", 2026))
    p = sim.tax_benefit_system.parameters("2026-01-01").gov.hhs.medicaid.eligibility
    got = _federally_eligible_status(statuses, years, p)
    assert got.tolist() == expected.tolist()
    assert got.any() and not got.all()


def test_state_only_coverage_matches_policyengine():
    pytest.importorskip("policyengine_us")
    from policyengine_us import Simulation

    from analysis.california_shift import _state_only_coverage

    # A California household with no income: a citizen parent, a citizen child
    # and an undocumented child whom state-funded Medi-Cal covers. The
    # adjustment moves exactly the federal share policyengine-us books for the
    # undocumented child, and nothing for the citizens.
    people = {
        "parent": {"age": {2026: 30}, "immigration_status": {2026: "CITIZEN"}},
        "citizen_child": {"age": {2026: 5}, "immigration_status": {2026: "CITIZEN"}},
        "undocumented_child": {"age": {2026: 6}, "immigration_status": {2026: "UNDOCUMENTED"}},
    }
    for person in people.values():
        person["takes_up_medicaid_if_eligible"] = {2026: True}
    sim = Simulation(situation=_situation("CA", people))
    federal = sum(np.asarray(sim.calculate(v, 2026), dtype=float) for v in FEDERAL_SHARE_COSTS)
    assert federal[2] > 0, "the undocumented child should be enrolled with a federal share booked"
    assert federal[1] > 0, "the citizen child should be enrolled with a federal share booked"
    assert _state_only_coverage(sim).tolist() == pytest.approx([federal[2]])


def test_state_only_federal_share_examples():
    # A citizen on Medicaid, an undocumented woman covered through CHIP's
    # unborn-child option, a DACA child on CHIP and an undocumented adult on
    # state-funded Medicaid with a Medicare Savings Program share.
    federal = [True, False, False, False]
    shares = {
        "medicaid_federal_cost": [100.0, 0.0, 0.0, 900.0],
        "chip_federal_cost": [0.0, 300.0, 200.0, 0.0],
        "msp_federal_cost": [0.0, 0.0, 0.0, 10.0],
    }
    fcep = [False, True, False, False]
    got = _state_only_federal_share(federal, shares, fcep)
    assert got.tolist() == [0.0, 0.0, 200.0, 910.0]


@settings(max_examples=300, deadline=None)
@given(st.data())
def test_state_only_federal_share_bounds(data):
    n = data.draw(st.integers(1, 30))
    federal = np.asarray(data.draw(st.lists(st.booleans(), min_size=n, max_size=n)))
    shares = {
        v: np.asarray(data.draw(st.lists(SPENDING, min_size=n, max_size=n)))
        for v in FEDERAL_SHARE_COSTS
    }
    fcep = np.asarray(data.draw(st.lists(st.booleans(), min_size=n, max_size=n)))
    moved = _state_only_federal_share(federal, shares, fcep)
    total = sum(shares.values())
    assert (moved >= 0).all()
    assert (moved <= total + 1e-9).all()
    assert (moved[federal] == 0).all()
    np.testing.assert_allclose(
        moved[~federal & fcep],
        (shares["medicaid_federal_cost"] + shares["msp_federal_cost"])[~federal & fcep],
    )
    np.testing.assert_allclose(moved[~federal & ~fcep], total[~federal & ~fcep])


def test_state_only_coverage_keeps_fcep_match_federal():
    pytest.importorskip("policyengine_us")
    from policyengine_us import Simulation

    from analysis.california_shift import _state_only_coverage

    # Texas covers no undocumented adults in Medicaid, so an undocumented
    # pregnant woman with no income qualifies only through CHIP's unborn-child
    # option, which federal CHIP funds match whatever her status.
    people = {
        "mother": {
            "age": {2026: 28},
            "immigration_status": {2026: "UNDOCUMENTED"},
            "is_pregnant": {2026: True},
            "takes_up_medicaid_if_eligible": {2026: True},
            "takes_up_chip_if_eligible": {2026: True},
        }
    }
    sim = Simulation(situation=_situation("TX", people))
    assert np.asarray(sim.calculate("is_chip_fcep_eligible_person", 2026)).tolist() == [True]
    assert np.asarray(sim.calculate("chip_enrolled", 2026)).tolist() == [True]
    assert float(np.asarray(sim.calculate("chip_federal_cost", 2026))[0]) > 0
    assert _state_only_coverage(sim).tolist() == pytest.approx([0.0])


# --- Medicaid priced at the baseline ------------------------------------------


def test_price_medicaid_at_baseline_sets_the_baseline_denominator():
    branch = _Branch()
    _price_medicaid_at_baseline(branch, [3.0, 4.0])
    np.testing.assert_array_equal(branch.inputs[MEDICAID_DENOMINATOR], [3.0, 4.0])
    # A branch that already holds its own denominator has priced Medicaid
    # without the baseline's, so the pricing refuses it.
    with pytest.raises(RuntimeError, match="already calculated"):
        _price_medicaid_at_baseline(branch, [3.0, 4.0])


def _california_dataset(employment_income, weights):
    """A flat dataset of one-person California households, as a DataFrame."""
    import pandas as pd

    n = len(weights)
    columns = {
        f"person_{entity}_id__2026": np.arange(n)
        for entity in ("household", "tax_unit", "spm_unit", "family", "marital_unit")
    }
    columns.update(
        {
            "person_id__2026": np.arange(n),
            "age__2026": np.full(n, 35),
            "employment_income__2026": np.asarray(employment_income, dtype=float),
            "state_fips__2026": np.full(n, 6),
            "household_weight__2026": np.asarray(weights, dtype=float),
            "takes_up_medicaid_if_eligible__2026": np.ones(n, dtype=bool),
        }
    )
    return pd.DataFrame(columns)


def test_medicaid_at_the_baseline_price_rises_with_enrollment():
    # Two low-income Californians are on Medi-Cal and two higher-income ones are
    # not. The branch cuts the higher incomes so all four enroll. On its own,
    # policyengine-us spreads California's fixed Medicaid spending over the four,
    # so the state's total stays put; at the baseline's price the two new
    # enrollees add their cost and the two old ones cost what they did.
    pytest.importorskip("policyengine_us")
    from policyengine_us import Microsimulation

    weights = np.asarray([1_000.0, 2_000.0, 1_500.0, 500.0])
    dataset = _california_dataset([0.0, 5_000.0, 60_000.0, 90_000.0], weights)
    base = Microsimulation(dataset=dataset)
    assert base.is_over_dataset
    assert np.asarray(base.calculate("medicaid_enrolled", 2026)).tolist() == [True, True, False, False]
    base_cost = np.asarray(base.calculate("medicaid_cost", 2026), dtype=float)
    base_index = np.asarray(base.calculate("medicaid_slcsp_cost_index_filled", 2026), dtype=float)
    denominator = np.asarray(base.calculate(MEDICAID_DENOMINATOR, 2026), dtype=float)
    income = np.asarray(base.calculate("employment_income", 2026), dtype=float)
    cut = np.where(income > 50_000, 10_000.0, income)

    def shifted(name, price_at_baseline):
        branch = base.get_branch(name)
        branch.set_input("employment_income", 2026, cut)
        if price_at_baseline:
            _price_medicaid_at_baseline(branch, denominator)
        assert np.asarray(branch.calculate("medicaid_enrolled", 2026)).all()
        return branch

    # policyengine-us stores float32 values, so totals agree to about 1e-7.
    assert (base_cost[:2] > 0).all()
    alone = np.asarray(shifted("alone", False).calculate("medicaid_cost", 2026), dtype=float)
    assert (alone[2:] > 0).all()
    assert (alone * weights).sum() == pytest.approx((base_cost * weights).sum(), rel=1e-6)

    branch = shifted("priced", True)
    priced = np.asarray(branch.calculate("medicaid_cost", 2026), dtype=float)
    index = np.asarray(branch.calculate("medicaid_slcsp_cost_index_filled", 2026), dtype=float)
    np.testing.assert_allclose(priced[:2], base_cost[:2], rtol=1e-6)
    # Every enrollee costs the same amount per unit of cost index as in the baseline.
    np.testing.assert_allclose(priced / index, base_cost[0] / base_index[0], rtol=1e-6)
    expected_ratio = (index * weights).sum() / (base_index[:2] * weights[:2]).sum()
    assert expected_ratio > 1.5
    assert (priced * weights).sum() == pytest.approx(
        (base_cost * weights).sum() * expected_ratio, rel=1e-6
    )


def test_household_frame_drops_healthier_oregon_for_medicaid_enrollees():
    # policyengine-us enrolls an undocumented Oregon adult with no income in
    # Medicaid and also books the adult's Healthier Oregon cost. The frame keeps
    # the Medicaid cost and drops the Healthier Oregon one. Building the frame
    # also checks the health classification against policyengine-us's own lists.
    pytest.importorskip("policyengine_us")
    from policyengine_us import Simulation

    from analysis.california_shift import _household_frame

    people = {
        "adult": {
            "age": {2026: 35},
            "immigration_status": {2026: "UNDOCUMENTED"},
            "takes_up_medicaid_if_eligible": {2026: True},
        }
    }
    sim = Simulation(situation=_situation("OR", people))
    enrolled = bool(np.asarray(sim.calculate("medicaid_enrolled", 2026))[0])
    oregon = float(np.asarray(sim.calculate("or_healthier_oregon_cost", 2026))[0])
    assert enrolled and oregon > 0, "policyengine-us no longer prices this adult twice"
    frame = _household_frame(sim)
    assert frame["healthier_oregon_overlap"].tolist() == pytest.approx([oregon])
    programs = sum(
        np.asarray(sim.calculate(v, 2026, map_to="household"), dtype=float)
        for v in STATE_HEALTH + STATE_HEALTH_UNLISTED
    )
    assert frame["state_health_programs"].tolist() == pytest.approx((programs - oregon).tolist())
    assert frame["state_health"][0] > 0 and frame["tanf_in_state_benefits"].tolist() == [0.0]


def test_household_frame_carries_the_unlisted_state_subsidies():
    # ConnectorCare sits in STATE_HEALTH_UNLISTED. A Massachusetts adult at
    # $30,000 with ACA take-up draws it, and the frame's state spending must
    # hold it, or those dollars would leave every state's line.
    pytest.importorskip("policyengine_us")
    pd = pytest.importorskip("pandas")
    from policyengine_us import Microsimulation

    from analysis.california_shift import _household_frame

    dataset = pd.DataFrame(
        {
            "person_id__2026": [0],
            "person_household_id__2026": [0],
            "person_tax_unit_id__2026": [0],
            "person_spm_unit_id__2026": [0],
            "person_family_id__2026": [0],
            "person_marital_unit_id__2026": [0],
            "age__2026": [45],
            "state_fips__2026": [25],
            "household_weight__2026": [1_000.0],
            "employment_income__2026": [30_000.0],
            "takes_up_aca_if_eligible__2026": [True],
            "is_tax_unit_head__2026": [True],
            "is_tax_unit_dependent__2026": [False],
        }
    )
    sim = Microsimulation(dataset=dataset)
    subsidy = np.asarray(sim.calculate("ma_connector_care", 2026, map_to="household"), dtype=float)
    assert subsidy[0] > 0, "policyengine-us no longer pays this adult a ConnectorCare subsidy"
    frame = _household_frame(sim)
    assert frame["state_health_programs"].tolist() == pytest.approx(subsidy.tolist())
    assert frame["state_health"][0] >= subsidy[0]
