"""Tests for the health and TANF accounting the income-shift sweep uses.

Covers ``analysis.health_tanf``, the health and TANF totals in
``analysis.fiscal``, the sweep's rows in ``analysis.compute_shift_sweep`` and
``analysis.labor_inputs``. The invariants, checked over generated inputs:

- each household's federal and state health spending add up to every program
  ``healthcare_benefit_value`` prices, less the Healthier Oregon overlap, the
  excluded programs and the coverage no government pays for, and each state's
  TANF charge is its TANF less what its state benefits hold;
- each state's totals add up to the national totals;
- the all-government total with health and TANF is the published total plus
  the TANF it counted twice, less health spending;
- the site's federal chart, its state charts and the taxes outside every chart
  add up to that total whenever the aggregates hold the parts policyengine-us
  builds them from;
- a state's net change with health and TANF is its net change without them,
  less its health spending and the TANF its state benefits don't already hold;
- the shift sets each stored labor input to the values it sets the variable
  to, and refuses under a labor supply response.

The classification of health programs follows the lists policyengine-us 1.764.6
and 2.2.1 declare, and refuses any list it would get wrong. The checks against
policyengine-us run when it is installed: the classification and the state TANF
programs match the installed engine, and over a small multi-state dataset the
chart identity holds to the dollar, the shift reaches TANF's earned income, and
a two-level sweep's rows add up.
"""

import importlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from analysis import compare_shift_sweeps as cmp
from analysis import health_tanf
from analysis.fiscal import (
    HEALTH_TANF_KEYS,
    OUTSIDE_CHART_TAXES,
    federal_chart_change,
    net_fiscal_impact,
    revenue_components,
    state_revenue_components,
    states_chart_change,
)
from analysis.health_tanf import (
    EXCLUDED_HEALTH,
    FEDERAL_HEALTH,
    FEDERAL_SHARE_COSTS,
    FMAP_SPLIT_HEALTH,
    STATE_HEALTH,
    STATE_SHARE_COSTS,
    TOTAL_KEYS,
    check_frame,
    classify_health_programs,
    national_totals,
    state_totals,
    with_derived,
)
from analysis.labor_inputs import set_labor_income


def _import_sweep():
    """Import ``compute_shift_sweep`` whether or not policyengine-us is installed.

    It imports policyengine-us and policyengine-core at module level (through
    ``labor_capital_shift``). Stand-ins replace only modules that fail to
    import, and leave ``sys.modules`` once the import is done.
    """
    stubs = {
        "policyengine_us": {"Microsimulation": object},
        "policyengine_core": {},
        "policyengine_core.reforms": {"Reform": object},
    }
    added = []
    for name, attrs in stubs.items():
        try:
            importlib.import_module(name)
        except ImportError:
            module = types.ModuleType(name)
            module.__dict__.update(attrs)
            sys.modules[name] = module
            added.append(name)
    try:
        return importlib.import_module("analysis.compute_shift_sweep")
    finally:
        for name in added:
            sys.modules.pop(name, None)


sweep = _import_sweep()

# --- Classifying health programs ---------------------------------------------

#: What policyengine-us 1.764.6 declares: ``healthcare_benefit_value`` adds
#: these, and ``household_health_benefits`` lists Medicaid and the premium tax
#: credit under other names.
ADDS_1764 = [
    "medicaid_cost",
    "msp_cost",
    "chip",
    "assigned_aca_ptc",
    "basic_health_program",
    "co_omnisalud",
    "or_healthier_oregon_cost",
]
LISTED_1764 = ["medicaid", "msp_cost", "chip", "premium_tax_credit", "basic_health_program"]
#: What policyengine-us 2.2.1 declares (as #49's California script read it):
#: ``healthcare_benefit_value`` prices every state program, and
#: ``household_health_benefits`` leaves out Connecticut's, Massachusetts's, New
#: Jersey's, Vermont's and Washington's premium subsidies.
ADDS_221 = (
    list(FMAP_SPLIT_HEALTH) + list(FEDERAL_HEALTH) + list(STATE_HEALTH) + list(EXCLUDED_HEALTH)
)
LISTED_221 = (
    list(FMAP_SPLIT_HEALTH)
    + list(FEDERAL_HEALTH)
    + [
        "assigned_ca_premium_subsidy",
        "co_omnisalud",
        "assigned_co_premium_assistance",
        "md_premium_assistance",
        "assigned_nm_premium_assistance",
        "or_healthier_oregon_cost",
    ]
)
BENEFITS = ["snap", "ssi", "tanf", "ca_capi", "ma_tafdc"]


def _classify(adds=ADDS_1764, listed=LISTED_1764, federal=FEDERAL_SHARE_COSTS,
              state=STATE_SHARE_COSTS, benefits=BENEFITS, flag=False):
    return classify_health_programs(adds, listed, federal, state, benefits, flag)


def test_classification_at_policyengine_us_1764():
    fmap, federal, state, excluded = _classify()
    assert fmap == FMAP_SPLIT_HEALTH
    assert federal == FEDERAL_HEALTH
    assert state == ("or_healthier_oregon_cost",)
    # policyengine-us prices OmniSalud for people it doesn't cover, so the
    # totals leave it out.
    assert excluded == ("co_omnisalud",)


def test_classification_at_policyengine_us_221():
    classified = _classify(adds=ADDS_221, listed=LISTED_221)
    assert classified == (FMAP_SPLIT_HEALTH, FEDERAL_HEALTH, STATE_HEALTH, EXCLUDED_HEALTH)
    # Later releases list the other state subsidies too; nothing changes.
    assert _classify(adds=ADDS_221, listed=ADDS_221) == classified


def test_classification_refuses_what_it_would_get_wrong():
    with pytest.raises(ValueError, match="twice"):
        _classify(flag=True)
    with pytest.raises(ValueError, match="doesn't classify.*new_subsidy"):
        _classify(adds=ADDS_1764 + ["new_subsidy"])
    with pytest.raises(ValueError, match="no longer adds.*msp_cost"):
        _classify(adds=[p for p in ADDS_1764 if p != "msp_cost"])
    with pytest.raises(ValueError, match="lists.*ma_connector_care"):
        _classify(listed=LISTED_1764 + ["ma_connector_care"])
    with pytest.raises(ValueError, match="state_benefit_cost"):
        _classify(state=["medicaid_state_cost"])
    with pytest.raises(ValueError, match="federal_benefit_cost.*new_federal_cost"):
        _classify(federal=list(FEDERAL_SHARE_COSTS) + ["new_federal_cost"])
    # A health program the benefit lists already net would count twice, under
    # either of its names.
    for netted in ("co_omnisalud", "medicaid"):
        with pytest.raises(ValueError, match=netted):
            _classify(benefits=BENEFITS + [netted])


# --- Household frames ---------------------------------------------------------

STATES = ["CA", "MA", "OR", "TX"]
SPENDING = st.floats(0, 5e4, allow_nan=False, allow_infinity=False)
SHARES = st.floats(0, 1, allow_nan=False)
WEIGHTS = st.floats(0.5, 5_000, allow_nan=False, allow_infinity=False)


@st.composite
def frames(draw, n=None):
    """A household frame as ``health_tanf.household_frame`` builds one."""
    n = n or draw(st.integers(1, 30))
    state = np.asarray(draw(st.lists(st.sampled_from(STATES), min_size=n, max_size=n)))

    def spending():
        return np.asarray(draw(st.lists(SPENDING, min_size=n, max_size=n)))

    frame = {
        "state": state,
        "weight": np.asarray(draw(st.lists(WEIGHTS, min_size=n, max_size=n))),
        "federal_health_split": spending(),
        "state_health_split": spending(),
        "federal_health_other": spending(),
        "state_health_programs": spending(),
        "healthier_oregon_overlap": np.where(state == "OR", spending(), 0.0),
        "excluded_health_programs": spending(),
        "tanf": spending(),
    }

    def shares():
        return np.asarray(draw(st.lists(SHARES, min_size=n, max_size=n)))

    # The state-only move and the unfunded coverage take disjoint parts of the
    # federal share, and the unfunded coverage takes part of the state share.
    moved, unfunded = shares(), shares()
    frame["state_only_coverage"] = frame["federal_health_split"] * moved
    frame["unfunded_federal"] = frame["federal_health_split"] * (1 - moved) * unfunded
    frame["unfunded_state"] = frame["state_health_split"] * shares()
    frame["fmap_split_cost"] = frame["federal_health_split"] + frame["state_health_split"]
    # household_state_benefits holds Massachusetts's TAFDC at its full amount
    # for every eligible family; tanf holds it only for families that take
    # TANF up.
    takes_up = np.asarray(draw(st.lists(st.booleans(), min_size=n, max_size=n)))
    copy = spending()
    frame["tanf_in_state_benefits"] = np.where(state == "MA", copy, 0.0)
    frame["tanf"] = np.where(state == "MA", np.where(takes_up, copy, 0.0), frame["tanf"])
    # healthcare_benefit_value prices the overlap and the excluded programs
    # too; the frame's state programs leave them out.
    frame["health_value"] = (
        frame["fmap_split_cost"]
        + frame["federal_health_other"]
        + frame["state_health_programs"]
        + frame["healthier_oregon_overlap"]
        + frame["excluded_health_programs"]
    )
    return with_derived(frame)


@settings(max_examples=300, deadline=None)
@given(frames())
def test_health_spending_is_conserved(frame):
    every_program = (
        frame["federal_health_split"]
        + frame["state_health_split"]
        + frame["federal_health_other"]
        + frame["state_health_programs"]
        - frame["unfunded_federal"]
        - frame["unfunded_state"]
    )
    np.testing.assert_allclose(
        frame["state_health"] + frame["federal_health"], every_program, rtol=1e-12, atol=1e-6
    )
    np.testing.assert_allclose(
        frame["health_total"],
        frame["health_value"]
        - frame["healthier_oregon_overlap"]
        - frame["excluded_health_programs"]
        - frame["unfunded_federal"]
        - frame["unfunded_state"],
        rtol=1e-12,
        atol=1e-6,
    )
    # Neither government's line pays for the unfunded coverage, and the
    # state's line never falls below zero.
    assert (frame["state_health"] >= -1e-6).all()
    # A Massachusetts family that takes TANF up owes nothing beyond the copy in
    # its state's line, one that doesn't takes that copy back out, and every
    # other state pays all of its TANF.
    expected = np.where(
        frame["state"] == "MA",
        np.where(frame["tanf"] > 0, 0.0, -frame["tanf_in_state_benefits"]),
        frame["tanf"],
    )
    np.testing.assert_allclose(frame["tanf_charge"], expected, atol=1e-9)
    # Moving state-only coverage moves spending from the federal line to the
    # state's and never below zero.
    assert (frame["federal_health"] >= -1e-6).all()
    check_frame(frame)


def _frame_example():
    """Households whose pieces add up: one in California and two in Massachusetts.

    Both Massachusetts families qualify for TAFDC; the first takes TANF up and
    the second doesn't.
    """
    frame = {
        "state": np.asarray(["CA", "MA", "MA"]),
        "weight": np.asarray([100.0, 200.0, 50.0]),
        "federal_health_split": np.asarray([600.0, 500.0, 0.0]),
        "state_health_split": np.asarray([400.0, 500.0, 0.0]),
        "federal_health_other": np.asarray([0.0, 2_000.0, 0.0]),
        "state_health_programs": np.asarray([50.0, 0.0, 0.0]),
        "healthier_oregon_overlap": np.zeros(3),
        "state_only_coverage": np.asarray([600.0, 0.0, 0.0]),
        "tanf": np.asarray([3_000.0, 9_536.0, 0.0]),
    }
    frame["fmap_split_cost"] = frame["federal_health_split"] + frame["state_health_split"]
    frame["tanf_in_state_benefits"] = np.asarray([0.0, 9_536.0, 9_536.0])
    frame["health_value"] = np.asarray([1_050.0, 3_000.0, 0.0])
    return with_derived(frame)


def test_frame_example_by_hand():
    frame = _frame_example()
    check_frame(frame)
    # California pays its share and all of the undocumented enrollee's federal
    # share. Massachusetts's state benefits hold TAFDC for both of its
    # families, so the charge adds nothing for the family that takes TANF up
    # and takes the copy back out for the one that doesn't.
    assert frame["state_health"].tolist() == [1_050.0, 500.0, 0.0]
    assert frame["federal_health"].tolist() == [0.0, 2_500.0, 0.0]
    assert frame["tanf_charge"].tolist() == [3_000.0, 0.0, -9_536.0]
    assert national_totals(frame)["health_total"] == 100 * 1_050.0 + 200 * 3_000.0
    # Massachusetts's line holds both families' TAFDC; with the charge it
    # holds the TAFDC tanf pays, the first family's.
    massachusetts = state_totals(frame)["MA"]
    assert massachusetts["tanf_in_state_benefits"] == 250 * 9_536.0
    assert massachusetts["tanf_in_state_benefits"] + massachusetts["tanf_charge"] == 200 * 9_536.0


def test_check_frame_refuses_a_gap():
    frame = _frame_example()
    gap = dict(frame, health_value=frame["health_value"] + 10.0)
    with pytest.raises(AssertionError, match="healthcare_benefit_value"):
        check_frame(gap)
    split = dict(frame, fmap_split_cost=frame["fmap_split_cost"] + 10.0)
    with pytest.raises(AssertionError, match="federal_benefit_cost"):
        check_frame(split)
    moved = dict(frame, state_only_coverage=frame["federal_health_split"] + 10.0)
    with pytest.raises(AssertionError, match="moves more"):
        check_frame(moved)
    # The move and the unfunded federal share together can't pass the federal
    # share, the unfunded state share can't pass the state share, and neither
    # can fall below zero.
    both = dict(frame, unfunded_federal=frame["federal_health_split"] - frame["state_only_coverage"] + 10.0)
    with pytest.raises(AssertionError, match="moves more"):
        check_frame(with_derived(both))
    state = dict(frame, unfunded_state=frame["state_health_split"] + 10.0)
    with pytest.raises(AssertionError, match="drops more"):
        check_frame(with_derived(state))
    negative = dict(frame, unfunded_state=frame["state_health_split"] * 0 - 1.0)
    with pytest.raises(AssertionError, match="negative"):
        check_frame(with_derived(negative))


def test_unfunded_coverage_leaves_both_lines():
    # policyengine-us books $1,000 of Medicare Savings Program benefits for an
    # undocumented Texas senior: $600 federal and $400 state. No government
    # pays for it, so neither line counts it, though healthcare_benefit_value
    # prices it. OmniSalud's $300 is priced and left out too.
    frame = {
        "state": np.asarray(["TX", "CO"]),
        "weight": np.asarray([10.0, 10.0]),
        "federal_health_split": np.asarray([600.0, 0.0]),
        "state_health_split": np.asarray([400.0, 0.0]),
        "fmap_split_cost": np.asarray([1_000.0, 0.0]),
        "federal_health_other": np.zeros(2),
        "state_health_programs": np.zeros(2),
        "healthier_oregon_overlap": np.zeros(2),
        "excluded_health_programs": np.asarray([0.0, 300.0]),
        "state_only_coverage": np.zeros(2),
        "unfunded_federal": np.asarray([600.0, 0.0]),
        "unfunded_state": np.asarray([400.0, 0.0]),
        "health_value": np.asarray([1_000.0, 300.0]),
        "tanf": np.zeros(2),
        "tanf_in_state_benefits": np.zeros(2),
    }
    frame = with_derived(frame)
    check_frame(frame)
    assert frame["federal_health"].tolist() == [0.0, 0.0]
    assert frame["state_health"].tolist() == [0.0, 0.0]
    assert national_totals(frame)["unfunded_federal"] == 6_000.0
    assert national_totals(frame)["excluded_health_programs"] == 3_000.0


def test_check_frame_allows_float32_rounding_of_large_amounts():
    # On the small dataset at the end of this file, California's fixed
    # Medi-Cal spending spread over two enrollees costs $124 million a
    # household, and float32 rounding leaves healthcare_benefit_value $4 off
    # the sum of its programs. A millionth of the amount passes; more doesn't.
    frame = _frame_example()
    big = {k: v if k in ("state", "weight") else v * 1e5 for k, v in frame.items()}
    covered = big["health_value"] > 0
    check_frame(dict(big, health_value=big["health_value"] + 4.0 * covered))
    with pytest.raises(AssertionError, match="healthcare_benefit_value"):
        check_frame(dict(big, health_value=big["health_value"] + 200.0 * covered))
    # A household with no coverage gets no such allowance.
    with pytest.raises(AssertionError, match="healthcare_benefit_value"):
        check_frame(dict(big, health_value=big["health_value"] + 4.0 * ~covered))


@settings(max_examples=200, deadline=None)
@given(frames())
def test_state_totals_add_up_to_national_totals(frame):
    national = national_totals(frame)
    states = state_totals(frame)
    assert set(states) == set(np.unique(frame["state"]))
    for key in TOTAL_KEYS:
        total = sum(row[key] for row in states.values())
        assert total == pytest.approx(national[key], rel=1e-9, abs=1e-6)


# --- Revenue totals and the site's charts ------------------------------------

#: Taxes inside household_tax_before_refundable_credits at policyengine-us
#: 1.764.6, as fiscal names them: its seven adds, with employee_payroll_tax
#: split into its four components.
HOUSEHOLD_TAX_PARTS = (
    "employee_social_security_tax",
    "employee_medicare_tax",
    "additional_medicare_tax",
    "employee_state_payroll_tax",
    "self_employment_tax",
    "fed_income_tax_before_refundable_credits",
    "flat_tax",
    "state_tax_before_refundable_credits",
    "local_income_tax_before_refundable_credits",
    "local_occupational_tax",
)
AMOUNTS = st.floats(-1e9, 1e10, allow_nan=False, allow_infinity=False)


@st.composite
def components(draw):
    """Revenue components whose aggregates hold the parts policyengine-us adds."""
    c = {key: draw(AMOUNTS) for key in HOUSEHOLD_TAX_PARTS}
    for key in (
        "employer_payroll_tax",
        "income_tax_refundable_credits",
        "state_refundable_credits",
        "federal_benefits_outside_state_lists",
        "state_benefits",
        "household_market_income",
        "federal_health",
        "state_health",
    ):
        c[key] = draw(AMOUNTS)
    c["tanf"] = draw(st.floats(0, 1e10, allow_nan=False))
    # Massachusetts's TAFDC: part of TANF that household_state_benefits holds.
    c["tanf_in_state_benefits"] = c["tanf"] * draw(SHARES)
    c["household_tax_before_refundable_credits"] = sum(c[k] for k in HOUSEHOLD_TAX_PARTS)
    c["household_refundable_tax_credits"] = (
        c["income_tax_refundable_credits"] + c["state_refundable_credits"]
    )
    # household_benefits holds TAFDC twice: in tanf and in state_benefits.
    c["household_benefits"] = (
        c["federal_benefits_outside_state_lists"] + c["tanf"] + c["state_benefits"]
    )
    c["household_net_income"] = (
        c["household_market_income"]
        + c["household_benefits"]
        + c["household_refundable_tax_credits"]
        - c["household_tax_before_refundable_credits"]
    )
    c["health_total"] = c["federal_health"] + c["state_health"]
    c["tanf_charge"] = c["tanf"] - c["tanf_in_state_benefits"]
    for key in HEALTH_TANF_KEYS:
        c.setdefault(key, 0.0)
    return c


def _scale(*values):
    return sum(abs(v) for v in values) + 1.0


@settings(max_examples=500, deadline=None)
@given(components(), components())
def test_totals_and_chart_identity(scenario, baseline):
    delta = net_fiscal_impact(scenario, baseline)

    def change(key):
        return scenario[key] - baseline[key]

    size = _scale(*scenario.values(), *baseline.values())
    tol = 1e-9 * size
    # TANF counted once, then health paid for.
    assert delta["total_change_excluding_health"] == pytest.approx(
        delta["total_change"] + change("tanf_in_state_benefits"), abs=tol
    )
    assert delta["total_change_with_health_tanf"] == pytest.approx(
        delta["total_change"] + change("tanf_in_state_benefits") - change("health_total"),
        abs=tol,
    )
    # The federal chart, the state charts and the taxes outside them hold
    # every dollar of that total.
    assert delta["_chart_identity_residual"] == pytest.approx(0.0, abs=tol)
    assert delta["taxes_outside_charts_change"] == pytest.approx(
        sum(change(v) for v in OUTSIDE_CHART_TAXES), abs=tol
    )
    # The federal chart in closed form: TANF and state benefits sit in the
    # state charts, every refundable state credit too.
    assert federal_chart_change(delta) == pytest.approx(
        change("fed_income_tax_before_refundable_credits")
        - change("income_tax_refundable_credits")
        + change("employer_payroll_tax")
        + change("employee_social_security_tax")
        + change("employee_medicare_tax")
        + change("self_employment_tax")
        - change("federal_benefits_outside_state_lists")
        - change("federal_health"),
        abs=tol,
    )
    assert states_chart_change(delta) == pytest.approx(
        change("state_tax_before_refundable_credits")
        - change("state_refundable_credits")
        - change("state_benefits")
        - change("tanf_charge")
        - change("state_health"),
        abs=tol,
    )
    # Health spending changes nothing in the household net-income identity.
    assert delta["_identity_residual"] == pytest.approx(0.0, abs=tol)


def test_totals_without_health_keep_the_published_keys():
    base = {k: 0.0 for k in ("household_tax_before_refundable_credits",
                             "household_refundable_tax_credits", "household_benefits",
                             "employer_payroll_tax", "household_market_income",
                             "household_net_income", *OUTSIDE_CHART_TAXES)}
    scen = dict(base, household_tax_before_refundable_credits=5.0, flat_tax=2.0,
                local_occupational_tax=1.0, household_net_income=-5.0)
    delta = net_fiscal_impact(scen, base)
    assert delta["total_change"] == 5.0
    assert delta["taxes_outside_charts_change"] == 3.0
    assert "total_change_with_health_tanf" not in delta


class _Weighted(np.ndarray):
    """A weighted array: ``sum`` weights, like PolicyEngine's MicroSeries."""

    def __new__(cls, values, weights):
        obj = np.asarray(values, dtype=float).view(cls)
        obj.weights = np.asarray(weights, dtype=float)
        return obj

    def __array_finalize__(self, obj):
        self.weights = getattr(obj, "weights", None)

    def sum(self, *args, **kwargs):
        return float((np.asarray(self) * self.weights).sum())


def _household_sim(frame):
    """A stand-in simulation over a frame's households, with every variable zero."""
    weight = np.asarray(frame["weight"], dtype=float)

    def calculate(variable, map_to=None, period=None):
        if variable == "state_code_str":
            return np.asarray(frame["state"])
        if variable == "household_weight":
            return _Weighted(weight, np.ones_like(weight))
        return _Weighted(np.zeros_like(weight), weight)

    return SimpleNamespace(calculate=calculate)


@settings(max_examples=50, deadline=None)
@given(frames())
def test_revenue_components_carry_the_frame(frame):
    sim = _household_sim(frame)
    national = revenue_components(sim, health_frame=frame)
    totals = national_totals(frame)
    for key in HEALTH_TANF_KEYS:
        assert national[key] == pytest.approx(totals[key], rel=1e-12, abs=1e-9)
    for key in OUTSIDE_CHART_TAXES:
        assert key in national
    # Without a frame the components hold no health spending.
    assert "health_total" not in revenue_components(sim)

    states = state_revenue_components(sim, health_frame=frame)
    by_state = state_totals(frame)
    for code, row in by_state.items():
        for key in (*HEALTH_TANF_KEYS, "tanf"):
            assert states[code][key] == pytest.approx(row[key], rel=1e-12, abs=1e-9)


def test_state_components_refuse_a_frame_in_another_order():
    frame = with_derived({
        "state": np.asarray(["CA", "TX"]),
        "weight": np.asarray([1.0, 1.0]),
        **{k: np.zeros(2) for k in ("federal_health_split", "state_health_split",
                                     "federal_health_other", "state_health_programs",
                                     "healthier_oregon_overlap", "tanf",
                                     "state_only_coverage", "fmap_split_cost",
                                     "tanf_in_state_benefits", "health_value")},
    })
    sim = _household_sim(dict(frame, state=np.asarray(["TX", "CA"])))
    with pytest.raises(ValueError, match="households differ"):
        state_revenue_components(sim, health_frame=frame)


# --- The sweep's rows -----------------------------------------------------------

STATE_LINES = (
    "household_state_tax_before_refundable_credits",
    "household_refundable_state_tax_credits",
    "household_state_benefits",
)


#: Each health or TANF field of a state's row and the component it differences.
#: The test writes them out so that it doesn't read the sweep's own table.
STATE_ROW_COMPONENTS = {
    "state_health_change_b": "state_health",
    "federal_health_change_b": "federal_health",
    "health_change_b": "health_total",
    "state_only_coverage_change_b": "state_only_coverage",
    "healthier_oregon_overlap_change_b": "healthier_oregon_overlap",
    "unfunded_federal_coverage_change_b": "unfunded_federal",
    "unfunded_state_coverage_change_b": "unfunded_state",
    "excluded_health_programs_change_b": "excluded_health_programs",
    "tanf_change_b": "tanf",
    "tanf_state_charge_change_b": "tanf_charge",
    "tanf_in_state_benefits_change_b": "tanf_in_state_benefits",
}


@st.composite
def state_components(draw):
    codes = draw(st.lists(st.sampled_from(STATES + ["NY", "WA"]), min_size=1, max_size=6,
                          unique=True))
    out = {}
    for code in codes:
        row = {key: draw(AMOUNTS) for key in STATE_LINES}
        for key in (*HEALTH_TANF_KEYS, "tanf"):
            row[key] = draw(st.floats(0, 1e10, allow_nan=False))
        row["household_weight"] = 1e6
        out[code] = row
    return out


@settings(max_examples=300, deadline=None)
@given(state_components(), state_components())
def test_state_rows_net_health_and_tanf(scenario, baseline):
    rows = sweep._state_delta_rows(scenario, baseline)
    assert list(rows) == sorted(set(scenario) | set(baseline))
    for code, row in rows.items():
        scen, base = scenario.get(code, {}), baseline.get(code, {})

        def change(key, scen=scen, base=base):
            return (scen.get(key, 0.0) - base.get(key, 0.0)) / 1e9

        excluding = (
            change("household_state_tax_before_refundable_credits")
            - change("household_refundable_state_tax_credits")
            - change("household_state_benefits")
        )
        assert row["state_net_excluding_health_tanf_change_b"] == pytest.approx(
            excluding, rel=1e-12, abs=1e-9
        )
        assert row["state_net_change_b"] == pytest.approx(
            excluding - change("tanf_charge") - change("state_health"), rel=1e-12, abs=1e-6
        )
        assert row["tanf_state_charge_change_b"] == pytest.approx(change("tanf_charge"))
        assert row["state_health_change_b"] == pytest.approx(change("state_health"))
        # Each row carries every field compare's checker reads, and each health
        # or TANF field differences its own component.
        assert set(cmp.STATE_FIELDS) <= set(row)
        for field, key in STATE_ROW_COMPONENTS.items():
            assert row[field] == pytest.approx(change(key), rel=1e-12, abs=1e-9), field


def test_state_rows_refuse_components_without_health():
    plain = {"CA": {key: 1.0 for key in STATE_LINES}}
    with pytest.raises(KeyError, match="health_frame"):
        sweep._state_delta_rows(plain, plain)


def test_fiscal_row_refuses_a_missing_total():
    delta = dict.fromkeys((key for _, key in sweep._FISCAL_FIELDS), 1e9)
    row = sweep._fiscal_row(delta)
    assert row["revenue_change_b"] == row["total_rev_change_b"] == 1.0
    del delta["total_change_with_health_tanf"]
    with pytest.raises(KeyError, match="total_change_with_health_tanf"):
        sweep._fiscal_row(delta)


# --- Readers of the sweep payload ---------------------------------------------


def _sweep_payload(counts_health):
    """One shift level for California and New York, in either sweep format.

    Both formats hold the same results: on the study measure, California +$5B,
    New York -$1B and all governments -$120B. A sweep that counts health
    spending and TANF puts the measure with them in ``state_net_change_b``
    (California +$2B, New York -$3B) and ``total_rev_change_b`` (-$100B).
    """
    if counts_health:
        states = {
            "CA": {"state_net_change_b": 2.0, "state_net_excluding_health_tanf_change_b": 5.0,
                   "state_health_change_b": 2.5},
            "NY": {"state_net_change_b": -3.0, "state_net_excluding_health_tanf_change_b": -1.0,
                   "state_health_change_b": 1.5},
        }
        level = {"total_rev_change_b": -100.0, "total_rev_change_published_definition_b": -120.0}
    else:
        states = {"CA": {"state_net_change_b": 5.0}, "NY": {"state_net_change_b": -1.0}}
        level = {"total_rev_change_b": -120.0}
    return {
        "year": 2026,
        "metadata": {"country_model_version": "1.764.6"},
        "scenarios": [
            {"shift_pct": 0, "total_rev_change_b": 0.0, "state_deltas": {}},
            {"shift_pct": 10, "state_deltas": states, **level},
        ],
    }


def _write(tmp_path, payload, name):
    import json

    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return str(path)


def test_summary_compares_the_study_measure_in_either_sweep_format(tmp_path):
    from analysis.california_summary import published_by_level

    expected = {10: {"california": 5.0, "other_states": -1.0, "federal": -124.0, "total": -120.0}}
    for counts_health in (True, False):
        path = _write(tmp_path, _sweep_payload(counts_health), f"sweep_{counts_health}.json")
        published, meta = published_by_level(path)
        assert published == expected
        assert meta["country_model_version"] == "1.764.6"


def test_chart_reads_either_measure_from_a_sweep(tmp_path):
    pytest.importorskip("matplotlib")
    from analysis.california_chart import series_from_sweep, sweep_measure

    new = _write(tmp_path, _sweep_payload(True), "new.json")
    old = _write(tmp_path, _sweep_payload(False), "old.json")
    assert sweep_measure(_sweep_payload(True)) == "with_health_tanf"
    assert sweep_measure(_sweep_payload(False)) == "study"

    xs, ca, ca_sdi, other, note = series_from_sweep(new)
    assert (xs, ca, ca_sdi, other) == ([0, 10], [0.0, 2.0], None, [0.0, -3.0])
    assert note == "policyengine-us 1.764.6, 2026"
    # The study measure reads the same from either format.
    for path in (new, old):
        assert series_from_sweep(path, measure="study")[1:4] == ([0.0, 5.0], None, [0.0, -1.0])
    with pytest.raises(ValueError, match="doesn't count health"):
        series_from_sweep(old, measure="with_health_tanf")


def test_california_note_names_the_premium_subsidy_only_where_counted():
    pytest.importorskip("matplotlib")
    from analysis.california_chart import (
        CALIFORNIA_HEALTH_TANF_NOTE,
        CALIFORNIA_HEALTH_TANF_NOTE_NO_SUBSIDY,
        CALIFORNIA_MEASURE_NOTE,
        california_note,
    )

    # policyengine-us 1.764.6 counts no Californian premium subsidy.
    at_1764 = california_note("with_health_tanf", ["or_healthier_oregon_cost"])
    assert at_1764 == CALIFORNIA_HEALTH_TANF_NOTE_NO_SUBSIDY
    assert "subsid" not in at_1764
    assert california_note("with_health_tanf", list(STATE_HEALTH)) == CALIFORNIA_HEALTH_TANF_NOTE
    assert "premium subsidy" in CALIFORNIA_HEALTH_TANF_NOTE
    # Runs from before the record existed (#49's, on 2.2.1) counted the subsidy.
    assert california_note("with_health_tanf") == CALIFORNIA_HEALTH_TANF_NOTE
    assert california_note("study", ["or_healthier_oregon_cost"]) == CALIFORNIA_MEASURE_NOTE


# --- Labor inputs ---------------------------------------------------------------


class _Branch:
    def __init__(self):
        self.inputs = {}

    def set_input(self, variable, period, values):
        self.inputs[variable] = np.asarray(values, dtype=float)


class _LaborSim:
    def __init__(self, columns, stored=True):
        self.columns = {k: np.asarray(v, dtype=float) for k, v in columns.items()}
        names = list(self.columns)
        if not stored:
            names = [n for n in names if not n.endswith("_before_lsr")]
        self.tax_benefit_system = SimpleNamespace(variables=dict.fromkeys(names))

    def calculate(self, variable, period=None):
        return self.columns[variable]


INCOMES = st.lists(st.floats(-1e5, 1e6, allow_nan=False, allow_infinity=False),
                   min_size=1, max_size=20)


@settings(max_examples=200, deadline=None)
@given(INCOMES, st.floats(0, 1, allow_nan=False))
def test_labor_income_reaches_the_stored_input(values, cut):
    baseline = _LaborSim({"employment_income": values, "employment_income_before_lsr": values})
    branch = _Branch()
    shifted = np.asarray(values) * (1 - cut)
    assert set_labor_income(baseline, branch, "employment_income", 2026, shifted) == (
        "employment_income_before_lsr"
    )
    np.testing.assert_array_equal(branch.inputs["employment_income"], shifted)
    np.testing.assert_array_equal(branch.inputs["employment_income_before_lsr"], shifted)

    # An engine without the stored input gets the variable alone.
    plain = _LaborSim({"employment_income": values}, stored=False)
    branch = _Branch()
    assert set_labor_income(plain, branch, "employment_income", 2026, shifted) is None
    assert set(branch.inputs) == {"employment_income"}


def test_labor_income_refuses_a_labor_supply_response():
    baseline = _LaborSim({"employment_income": [105.0], "employment_income_before_lsr": [100.0]})
    branch = _Branch()
    with pytest.raises(ValueError, match="labor supply response"):
        set_labor_income(baseline, branch, "employment_income", 2026, [50.0])
    assert branch.inputs == {}


def test_labor_income_leaves_an_unused_stored_input_alone():
    # A dataset that sets employment_income itself leaves the stored input at
    # zero, so the formulas that read it see zero in the baseline and should in
    # the branch too.
    baseline = _LaborSim(
        {"employment_income": [80.0, 0.0], "employment_income_before_lsr": [0.0, 0.0]}
    )
    branch = _Branch()
    assert set_labor_income(baseline, branch, "employment_income", 2026, [40.0, 0.0]) is None
    assert set(branch.inputs) == {"employment_income"}
    # Nobody earning anything is no evidence either way; both stay at zero.
    idle = _LaborSim({"employment_income": [0.0], "employment_income_before_lsr": [0.0]})
    branch = _Branch()
    assert set_labor_income(idle, branch, "employment_income", 2026, [0.0]) == (
        "employment_income_before_lsr"
    )


# --- Against policyengine-us ------------------------------------------------------


def _people_dataset(people):
    """A flat dataset, one row per person, as a DataFrame.

    ``people`` holds (household, state FIPS, age, columns) for each person; each
    household is one tax unit, SPM unit, family and marital unit, and its first
    person heads the tax unit.
    """
    import pandas as pd

    rows = []
    heads = set()
    for i, (household, fips, age, columns) in enumerate(people):
        row = {
            "person_id__2026": i,
            "person_household_id__2026": household,
            "person_tax_unit_id__2026": household,
            "person_spm_unit_id__2026": household,
            "person_family_id__2026": household,
            "person_marital_unit_id__2026": household,
            "age__2026": age,
            "state_fips__2026": fips,
            "household_weight__2026": 1_000.0,
            "is_tax_unit_head__2026": household not in heads,
            "is_tax_unit_dependent__2026": household in heads and age < 18,
        }
        heads.add(household)
        row.update({f"{k}__2026": v for k, v in columns.items()})
        rows.append(row)
    return pd.DataFrame(rows).fillna(0.0)


TAKE_UP = {
    "takes_up_medicaid_if_eligible": True,
    "takes_up_aca_if_eligible": True,
    "takes_up_tanf_if_eligible": True,
    "takes_up_snap_if_eligible": True,
}
#: A low-income California parent and child, a Massachusetts parent and child
#: on TAFDC, a Texas earner buying ACA coverage, two capital holders who
#: receive the shifted income, and a Massachusetts family like the first that
#: doesn't take TANF up.
NO_TANF = {**TAKE_UP, "takes_up_tanf_if_eligible": False}
PEOPLE = [
    (0, 6, 30, {"employment_income_before_lsr": 9_000.0, **TAKE_UP}),
    (0, 6, 5, dict(TAKE_UP)),
    (1, 25, 28, {"employment_income_before_lsr": 6_000.0, **TAKE_UP}),
    (1, 25, 3, dict(TAKE_UP)),
    (2, 48, 45, {"employment_income_before_lsr": 30_000.0, **TAKE_UP}),
    (3, 36, 50, {"employment_income_before_lsr": 400_000.0,
                 "long_term_capital_gains": 100_000.0, **TAKE_UP}),
    (4, 6, 40, {"employment_income_before_lsr": 150_000.0,
                "qualified_dividend_income": 30_000.0, **TAKE_UP}),
    (5, 25, 28, {"employment_income_before_lsr": 6_000.0, **NO_TANF}),
    (5, 25, 3, dict(NO_TANF)),
]


def _microsimulation():
    pytest.importorskip("policyengine_us")
    from policyengine_us import Microsimulation

    return Microsimulation(dataset=_people_dataset(PEOPLE))


#: Aggregates whose float32 rounding bounds what the identities leave over.
_LEVELS = (
    "household_tax_before_refundable_credits",
    "household_refundable_tax_credits",
    "household_benefits",
    "employer_payroll_tax",
    "household_market_income",
    "household_net_income",
)


def _float32_slack(*components):
    """What float32 rounding can leave in an identity over these components.

    policyengine-us builds each aggregate from float32 values, so two
    aggregates that hold the same dollars can differ in the seventh
    significant digit: on this dataset, $38.68 of the net-income identity
    over $230 million of tax. Allows a millionth of the aggregates' size, and
    at least a dollar; a missing program or tax would leave at least its own
    change, over a million dollars here.
    """
    return max(1.0, 1e-6 * sum(abs(c[key]) for c in components for key in _LEVELS))


def test_classification_matches_the_installed_engine():
    pytest.importorskip("policyengine_us")
    from policyengine_us import Simulation

    sim = Simulation(situation={"people": {"p": {"age": {2026: 30}}}})
    fmap, federal, state, excluded = health_tanf.health_programs(sim, 2026)
    adds = set(health_tanf.adds(sim, health_tanf.HEALTH_VALUE_VARIABLE, 2026))
    assert set(fmap) | set(federal) | set(state) | set(excluded) == adds
    assert excluded == health_tanf.EXCLUDED_HEALTH
    tanf_programs = health_tanf.state_tanf_variables(sim)
    assert "ca_tanf" in tanf_programs
    listed = sim.tax_benefit_system.parameters("2026-01-01").gov.household.household_state_benefits
    # Massachusetts's TAFDC sits in household_state_benefits until
    # policyengine-us 2.4.4 drops it; no other state's TANF ever has.
    programs = health_tanf.tanf_programs_in_state_benefits(tanf_programs, listed)
    assert set(programs) <= {"ma_tafdc"}
    assert set(health_tanf.tanf_states_in_state_benefits(tanf_programs, listed)) <= {"MA"}
    record = health_tanf.programs_metadata(sim, 2026)
    assert record["split_by_federal_matching"] == list(fmap)
    assert record["federal"] == list(federal)
    assert record["state"] == list(state)
    assert record["excluded"] == list(excluded)
    assert record["tanf_programs_in_state_benefits"] == programs
    assert set(record["tanf_states_in_state_benefits"]) <= {"MA"}


def test_chart_identity_and_labor_inputs_on_policyengine():
    from analysis.labor_capital_shift import _apply_shift

    base = _microsimulation()
    branch, _ = _apply_shift(base, "shifted", 0.5)
    health_tanf.price_medicaid_at_baseline(
        branch, health_tanf.medicaid_denominator(base, 2026), 2026
    )

    # The shift reaches the stored input that TANF's default earned-income list reads.
    for sim in (base, branch):
        np.testing.assert_allclose(
            np.asarray(sim.calculate("employment_income_before_lsr", 2026)),
            np.asarray(sim.calculate("employment_income", 2026)),
        )
    before = np.asarray(base.calculate("tanf_gross_earned_income", 2026), dtype=float)
    after = np.asarray(branch.calculate("tanf_gross_earned_income", 2026), dtype=float)
    assert before.sum() > 0
    np.testing.assert_allclose(after, before * 0.5, rtol=1e-5)

    frames = {}
    deltas = {}
    for name, sim in (("base", base), ("branch", branch)):
        frames[name] = health_tanf.household_frame(sim, 2026)
        deltas[name] = revenue_components(sim, 2026, health_frame=frames[name])
    assert frames["base"]["health_total"].sum() > 0
    # Only Massachusetts's TANF sits in its state benefits (at 1.764.6), at
    # TAFDC's full twelve months for every eligible family, while tanf holds it
    # only for families that take TANF up: households 1 and 5 differ only in
    # that.
    frame = frames["base"]
    in_lists = frame["tanf_in_state_benefits"]
    assert (in_lists[frame["state"] != "MA"] == 0).all()
    listed = base.tax_benefit_system.parameters("2026-01-01").gov.household.household_state_benefits
    if "ma_tafdc" in health_tanf.tanf_programs_in_state_benefits(
        health_tanf.state_tanf_variables(base), listed
    ):
        months = sum(
            np.asarray(
                base.calculate("ma_tafdc", f"2026-{month:02d}", map_to="household"),
                dtype=float,
            )
            for month in range(1, 13)
        )
        np.testing.assert_allclose(in_lists, months, rtol=1e-6, atol=0.01)
        # The flat dataset leaves household_id unset, so find the two by input.
        takes_up = np.asarray(
            base.calculate("takes_up_tanf_if_eligible", 2026, map_to="household"), dtype=float
        )
        taker, skipper = (
            int(np.flatnonzero((frame["state"] == "MA") & (takes_up == flag))[0])
            for flag in (1.0, 0.0)
        )
        assert months[taker] > 1_000
        assert months[skipper] == pytest.approx(months[taker], rel=1e-6)
        assert frame["tanf"][taker] == pytest.approx(months[taker], rel=1e-6)
        assert frame["tanf"][skipper] == 0
        assert frame["tanf_charge"][taker] == pytest.approx(0.0, abs=0.01)
        assert frame["tanf_charge"][skipper] == pytest.approx(-months[skipper], rel=1e-6)
    else:
        assert (in_lists == 0).all()
    delta = net_fiscal_impact(deltas["branch"], deltas["base"])
    # The engine's aggregates hold exactly the parts the charts add, so the
    # charts and the taxes outside them account for every dollar, up to
    # float32 rounding.
    slack = _float32_slack(deltas["base"], deltas["branch"])
    assert abs(delta["_chart_identity_residual"]) < slack
    assert abs(delta["_identity_residual"]) < slack
    # The shift moves TANF, and health spending, by far more than that.
    assert abs(delta["tanf_change"]) > 100 * slack
    assert abs(delta["health_total_change"]) > 100 * slack
    assert delta["total_change_with_health_tanf"] != delta["total_change"]


def test_two_level_sweep_rows_add_up():
    pytest.importorskip("policyengine_us")

    result = sweep.run_shift_sweep(
        shift_levels=[0.0, 0.5],
        microsim_factory=_microsimulation,
        microdata_output_dir=None,
    )
    baseline, half = result["scenarios"]
    assert baseline["total_rev_change_b"] == 0.0
    assert result["metadata"]["branch_arrays"]["shared_until_first_read"]
    assert result["metadata"]["branch_arrays"]["sources_frozen"]
    states = half["state_deltas"]
    federal_chart = (
        half["fed_income_tax_before_refundable_credits_change_b"]
        - (half["refundable_credits_change_b"] - half["state_refundable_credits_change_b"])
        + half["employer_payroll_change_b"]
        + half["employee_ss_tax_change_b"]
        + half["employee_medicare_tax_change_b"]
        + half["self_employment_tax_change_b"]
        - (half["benefits_change_b"] - half["state_benefits_change_b"] - half["tanf_change_b"])
        - half["federal_health_change_b"]
    )
    all_states = sum(row["state_net_change_b"] for row in states.values())
    rows_total = federal_chart + all_states + half["taxes_outside_charts_change_b"]
    # The rows the site reads leave the residual the sweep reports, to the
    # dollar (in $B, so 1e-9 is a dollar): the per-state rows hold the
    # national state lines.
    assert half["total_rev_change_b"] - rows_total == pytest.approx(
        half["chart_identity_residual_b"], abs=1e-9
    )
    slack_b = _float32_slack(revenue_components(_microsimulation(), 2026)) / 1e9
    assert abs(half["chart_identity_residual_b"]) < slack_b
    assert abs(half["identity_residual_b"]) < slack_b
    assert half["total_rev_change_b"] == pytest.approx(
        half["total_rev_change_excluding_health_b"] - half["health_change_b"], abs=1e-12
    )
    assert half["revenue_change_b"] == half["total_rev_change_b"]
    assert sum(row["state_health_change_b"] for row in states.values()) == pytest.approx(
        half["state_health_change_b"], abs=1e-12
    )
    # The sweep's own rows carry every field compare's checker reads.
    assert all(set(cmp.STATE_FIELDS) <= set(row) for row in states.values())
    assert set(cmp.ROW_FIELDS) <= set(half)


#: The 50 states and DC.
US_STATE_CODES = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI "
    "WY".split()
)
STATE_HEALTH_FIXTURE = Path(__file__).parent / "fixtures" / "state_health_programs.json"


def test_the_shared_fixture_lists_every_state_health_program():
    # src/components/ShiftSweep.test.jsx reads this fixture to check which
    # state the page assigns each program to, so a program added to
    # STATE_HEALTH must reach the fixture with its state.
    programs = json.loads(STATE_HEALTH_FIXTURE.read_text())["programs"]
    assert [program["variable"] for program in programs] == list(health_tanf.STATE_HEALTH)
    assert {program["state"] for program in programs} <= US_STATE_CODES
