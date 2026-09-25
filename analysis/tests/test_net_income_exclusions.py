"""Tests for keeping Head Start out of household net income.

policyengine-us 1.764.x counts Head Start and Early Head Start in
``household_benefits``; 2.x does not by default. ``drop_excluded_benefits``
makes both engines count them the 2.x way. The invariants:

- every dated benefits list loses exactly the excluded names, keeping the
  order of the rest, and the names removed are exactly those it listed;
- applying it twice is the same as applying it once;
- a parameter tree without the benefits list is left alone;
- the managed wrapper always applies it and records what it removed.

The fakes run without policyengine installed; the engine test needs
policyengine-us and is skipped otherwise.
"""

import sys
import types
from types import SimpleNamespace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from analysis import policyengine_runtime as runtime

EXCLUDED = set(runtime.NET_INCOME_EXCLUDED_BENEFITS)
NAMES = st.sampled_from(
    ["snap", "wic", "ssi", "tanf", "head_start", "early_head_start", "acp"]
)
DATED_LISTS = st.lists(st.lists(NAMES, max_size=8), max_size=4)


def _parameters(dated_lists):
    return SimpleNamespace(
        gov=SimpleNamespace(
            household=SimpleNamespace(
                household_benefits=SimpleNamespace(
                    values_list=[
                        SimpleNamespace(value=list(names)) for names in dated_lists
                    ]
                )
            )
        )
    )


def _values(parameters):
    return [
        at_instant.value
        for at_instant in parameters.gov.household.household_benefits.values_list
    ]


@settings(max_examples=200, deadline=None)
@given(dated_lists=DATED_LISTS)
def test_drops_exactly_the_excluded_names_in_order(dated_lists):
    parameters = _parameters(dated_lists)
    removed = set()

    assert runtime.drop_excluded_benefits(parameters, removed) is parameters

    assert _values(parameters) == [
        [name for name in names if name not in EXCLUDED] for names in dated_lists
    ]
    assert removed == {name for names in dated_lists for name in names} & EXCLUDED


@settings(max_examples=100, deadline=None)
@given(dated_lists=DATED_LISTS)
def test_is_idempotent(dated_lists):
    once = runtime.drop_excluded_benefits(_parameters(dated_lists), set())
    removed_again = set()
    twice = runtime.drop_excluded_benefits(
        _parameters(_values(once)), removed_again
    )
    assert _values(twice) == _values(once)
    assert removed_again == set()


@pytest.mark.parametrize(
    "parameters",
    [
        SimpleNamespace(),
        SimpleNamespace(gov=SimpleNamespace()),
        SimpleNamespace(gov=SimpleNamespace(household=SimpleNamespace())),
    ],
    ids=["no-gov", "no-household", "no-benefits-list"],
)
def test_a_tree_without_the_benefits_list_is_unchanged(parameters):
    removed = set()
    assert runtime.drop_excluded_benefits(parameters, removed) is parameters
    assert removed == set()


class _FakeReform:
    """The slice of policyengine_core's Reform the wrapper's reform uses."""

    def __init__(self, parameters):
        self.parameters = parameters

    def modify_parameters(self, modifier):
        self.parameters = modifier(self.parameters)


@pytest.fixture
def fake_engine(monkeypatch):
    """A managed_microsimulation that applies the reform it is given."""

    reforms = types.ModuleType("policyengine_core.reforms")
    reforms.Reform = _FakeReform
    monkeypatch.setitem(sys.modules, "policyengine_core.reforms", reforms)
    calls = []

    def managed_microsimulation(**kwargs):
        calls.append(kwargs)
        reform = kwargs["reform"](
            _parameters([["snap", "head_start", "early_head_start"], ["wic"]])
        )
        reform.apply()
        return SimpleNamespace(
            policyengine_bundle={"model_version": "1.764.6"},
            reform=reform,
            tax_benefit_system=SimpleNamespace(variables={}),
        )

    us = types.ModuleType("policyengine.tax_benefit_models.us")
    us.managed_microsimulation = managed_microsimulation
    monkeypatch.setitem(sys.modules, "policyengine.tax_benefit_models.us", us)
    return calls


def test_managed_simulation_applies_and_records_the_exclusion(fake_engine):
    sim = runtime.managed_us_microsimulation()

    assert len(fake_engine) == 1
    assert _values(sim.reform.parameters) == [["snap"], ["wic"]]
    assert sim.policyengine_bundle["net_income_excluded_benefits"] == [
        "early_head_start",
        "head_start",
    ]


def test_managed_simulation_refuses_a_second_reform(fake_engine):
    with pytest.raises(ValueError, match="net-income reform"):
        runtime.managed_us_microsimulation(reform=object())
    assert fake_engine == []


def test_fingerprint_tracks_the_exclusion_list(monkeypatch):
    before = runtime.runtime_fingerprint()
    assert before["net_income_excluded_benefits"] == sorted(EXCLUDED)
    monkeypatch.setattr(runtime, "NET_INCOME_EXCLUDED_BENEFITS", ("head_start",))
    assert runtime.runtime_fingerprint()["digest"] != before["digest"]


def test_engine_moves_net_income_but_not_spm_resources(monkeypatch):
    """On a real engine, one low-income California household with an infant
    and a four-year-old in 2030: household benefits and net income fall by
    exactly the Head Start and Early Head Start value the engine counted, and
    SPM net income and poverty status do not move."""

    # Other test modules install stub ``policyengine_us`` and
    # ``policyengine_core`` modules in sys.modules at collection. Set every
    # stub (a module with no ``__file__``) aside for this test so the real
    # engine loads, or the test skips where none is installed; monkeypatch
    # restores them afterwards.
    for name, module in list(sys.modules.items()):
        if name.split(".")[0] in {"policyengine_us", "policyengine_core"} and (
            getattr(module, "__file__", None) is None
        ):
            monkeypatch.delitem(sys.modules, name)
    policyengine_us = pytest.importorskip("policyengine_us")
    people = {
        "parent": {"age": {2030: 25}, "employment_income": {2030: 12_000}},
        "infant": {"age": {2030: 1}},
        "child": {"age": {2030: 4}},
    }
    members = list(people)
    situation = {
        "people": people,
        "tax_units": {"tax_unit": {"members": members}},
        "families": {"family": {"members": members}},
        "spm_units": {"spm_unit": {"members": members}},
        "marital_units": {name: {"members": [name]} for name in members},
        "households": {"household": {"members": members, "state_code": {2030: "CA"}}},
    }

    def totals(reform):
        sim = policyengine_us.Simulation(situation=situation, reform=reform)
        return {
            variable: float(sim.calculate(variable, 2030).sum())
            for variable in (
                "household_benefits",
                "household_net_income",
                "spm_unit_net_income",
                "spm_unit_is_in_spm_poverty",
            )
        } | {
            "head_start_counted": sum(
                float(sim.calculate(variable, 2030).sum())
                for variable in EXCLUDED
                if variable in sim.tax_benefit_system.variables
            )
        }

    removed = set()
    baseline = totals(None)
    corrected = totals(runtime.net_income_exclusion_reform(removed))

    counted = baseline["head_start_counted"] if removed else 0.0
    # On an engine that counts Head Start, this household must exercise it.
    assert counted > 0 or not removed
    assert corrected["household_benefits"] == pytest.approx(
        baseline["household_benefits"] - counted
    )
    assert corrected["household_net_income"] == pytest.approx(
        baseline["household_net_income"] - counted
    )
    assert corrected["spm_unit_net_income"] == baseline["spm_unit_net_income"]
    assert (
        corrected["spm_unit_is_in_spm_poverty"]
        == baseline["spm_unit_is_in_spm_poverty"]
    )
