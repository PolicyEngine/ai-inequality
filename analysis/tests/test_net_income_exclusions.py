"""Tests for keeping Head Start out of household net income.

policyengine-us 1.764.x counts Head Start and Early Head Start in
``household_benefits``; 2.x does not by default. ``drop_excluded_benefits``
makes both engines count them the 2.x way. The invariants:

- every dated benefits list loses exactly the excluded names, keeping the
  order of the rest, and the names removed are exactly those it listed;
- applying it twice is the same as applying it once;
- a parameter tree without the benefits list is left alone;
- the managed wrapper applies it through a tax-benefit system exactly when
  the engine lists an excluded name, records what it removed, and never
  builds a simulation in reform mode (``simulation.baseline`` set), which
  would read every scenario branch's Medicaid denominator from the unshocked
  baseline.

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
    twice = runtime.drop_excluded_benefits(_parameters(_values(once)), removed_again)
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
    """The slice of policyengine_core's Reform the reform class uses."""

    def __init__(self, parameters):
        self.parameters = parameters

    def modify_parameters(self, modifier):
        self.parameters = modifier(self.parameters)


def _install_fake_engine(monkeypatch, *, listed, baseline=None):
    """Fake policyengine_core.reforms, policyengine_us (with its default
    ``system``) and policyengine.py's managed_microsimulation.

    The default system lists ``listed`` and then ``wic``;
    ``CountryTaxBenefitSystem(reform=R)`` applies R to a fresh copy. The fake
    managed_microsimulation records its kwargs and returns a simulation whose
    ``baseline`` is ``baseline``.
    """

    reforms = types.ModuleType("policyengine_core.reforms")
    reforms.Reform = _FakeReform
    monkeypatch.setitem(sys.modules, "policyengine_core.reforms", reforms)

    class CountryTaxBenefitSystem:
        def __init__(self, reform=None):
            parameters = _parameters([list(listed), ["wic"]])
            if reform is not None:
                applied = reform(parameters)
                applied.apply()
                parameters = applied.parameters
            self.parameters = parameters
            self.variables = {}

    us = types.ModuleType("policyengine_us")
    us.CountryTaxBenefitSystem = CountryTaxBenefitSystem
    us_system = types.ModuleType("policyengine_us.system")
    us_system.system = CountryTaxBenefitSystem()
    monkeypatch.setitem(sys.modules, "policyengine_us", us)
    monkeypatch.setitem(sys.modules, "policyengine_us.system", us_system)

    calls = []

    def managed_microsimulation(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            policyengine_bundle={"model_version": "fake"},
            baseline=baseline,
            tax_benefit_system=kwargs.get(
                "tax_benefit_system", SimpleNamespace(variables={})
            ),
        )

    managed = types.ModuleType("policyengine.tax_benefit_models.us")
    managed.managed_microsimulation = managed_microsimulation
    monkeypatch.setitem(sys.modules, "policyengine.tax_benefit_models.us", managed)
    return calls


def test_managed_simulation_builds_the_excluding_system(monkeypatch):
    """On an engine that lists Head Start, the wrapper passes a tax-benefit
    system with the exclusion applied, never ``reform=``, and records what it
    removed."""
    calls = _install_fake_engine(
        monkeypatch, listed=("snap", "head_start", "early_head_start")
    )

    sim = runtime.managed_us_microsimulation()

    assert len(calls) == 1
    assert "reform" not in calls[0]
    assert _values(calls[0]["tax_benefit_system"].parameters) == [["snap"], ["wic"]]
    assert sim.policyengine_bundle["net_income_excluded_benefits"] == [
        "early_head_start",
        "head_start",
    ]


def test_managed_simulation_applies_nothing_when_the_engine_lists_none(
    monkeypatch,
):
    """On an engine that lists none of the names (policyengine-us 2.x lists
    ``household_head_start_benefits``), the wrapper passes neither a system
    nor a reform, so the simulation is exactly the managed default."""
    calls = _install_fake_engine(
        monkeypatch, listed=("snap", "household_head_start_benefits")
    )

    sim = runtime.managed_us_microsimulation()

    assert "tax_benefit_system" not in calls[0]
    assert "reform" not in calls[0]
    assert sim.policyengine_bundle["net_income_excluded_benefits"] == []


@pytest.mark.parametrize("kwarg", ["reform", "tax_benefit_system"])
def test_managed_simulation_refuses_a_caller_system_or_reform(monkeypatch, kwarg):
    calls = _install_fake_engine(monkeypatch, listed=("head_start",))
    with pytest.raises(ValueError, match="net-income exclusion"):
        runtime.managed_us_microsimulation(**{kwarg: object()})
    assert calls == []


def test_managed_simulation_refuses_reform_mode(monkeypatch):
    """A simulation in reform mode (``baseline`` set) would read every scenario
    branch's Medicaid denominator from the unshocked baseline, so the wrapper
    refuses it."""
    _install_fake_engine(monkeypatch, listed=("head_start",), baseline=object())
    with pytest.raises(RuntimeError, match="reform mode"):
        runtime.managed_us_microsimulation()


@settings(max_examples=100, deadline=None)
@given(dated_lists=DATED_LISTS)
def test_listed_names_are_exactly_the_excluded_names_present(dated_lists):
    system = SimpleNamespace(parameters=_parameters(dated_lists))
    assert runtime.listed_excluded_benefits(system) == (
        {name for names in dated_lists for name in names} & EXCLUDED
    )


def test_fingerprint_tracks_the_exclusion_list(monkeypatch):
    before = runtime.runtime_fingerprint()
    assert before["net_income_excluded_benefits"] == sorted(EXCLUDED)
    monkeypatch.setattr(runtime, "NET_INCOME_EXCLUDED_BENEFITS", ("head_start",))
    assert runtime.runtime_fingerprint()["digest"] != before["digest"]


def test_engine_moves_net_income_but_not_spm_or_health(monkeypatch):
    """On a real engine, one low-income California household with an infant
    and a four-year-old in 2030. The engine's own benefits list is the oracle
    for which names the exclusion must remove. Household benefits and net
    income fall by exactly the value of the listed Head Start programs (which
    this household must exercise wherever the engine lists them). SPM net
    income, SPM poverty status and health benefits do not move, and no
    simulation or branch is in reform mode."""

    # Earlier tests leave stub ``policyengine_us`` and ``policyengine_core``
    # modules in sys.modules. Set every stub (a module with no ``__file__``)
    # aside for this test so the real engine loads, or the test skips where
    # none is installed; monkeypatch restores them afterwards.
    for name, module in list(sys.modules.items()):
        if name.split(".")[0] in {"policyengine_us", "policyengine_core"} and (
            getattr(module, "__file__", None) is None
        ):
            monkeypatch.delitem(sys.modules, name)
    policyengine_us = pytest.importorskip("policyengine_us")

    default = policyengine_us.CountryTaxBenefitSystem()
    listed = (
        set(default.parameters("2030-01-01").gov.household.household_benefits)
        & EXCLUDED
    )
    household = {"members": ["parent", "infant", "child"], "state_code": {2030: "CA"}}
    if "county_fips" in default.variables:
        household["county_fips"] = {2030: "06037"}
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
        "households": {"household": household},
    }
    compared = [
        "household_benefits",
        "household_net_income",
        "spm_unit_net_income",
        "spm_unit_is_in_spm_poverty",
        *(
            variable
            for variable in (
                "household_health_benefits",
                "healthcare_benefit_value",
                "medicaid_cost",
            )
            if variable in default.variables
        ),
    ]

    def run(tax_benefit_system):
        kwargs = {"situation": situation}
        if tax_benefit_system is not None:
            kwargs["tax_benefit_system"] = tax_benefit_system
        sim = policyengine_us.Simulation(**kwargs)
        assert sim.baseline is None
        assert sim.get_branch("scenario_probe").baseline is None
        totals = {v: float(sim.calculate(v, 2030).sum()) for v in compared}
        for v in listed:
            totals[f"value:{v}"] = float(sim.calculate(v, 2030).sum())
        totals["listed_value"] = sum(totals[f"value:{v}"] for v in listed)
        return totals

    removed = set()
    system = runtime.net_income_exclusion_system(removed)
    before = run(None)
    after = run(system)

    assert removed == listed
    assert (system is None) == (not listed)
    # The household exercises every listed program, so each one's exclusion is
    # tested, not just their sum.
    for v in listed:
        assert before[f"value:{v}"] > 0, v
    if not listed:
        # The 2.x premise: Head Start stays out of net income by default.
        simulation_parameters = default.parameters("2030-01-01").gov.simulation
        assert not getattr(
            simulation_parameters, "include_head_start_benefits_in_net_income", False
        )
    counted = before["listed_value"]
    assert after["household_benefits"] == pytest.approx(
        before["household_benefits"] - counted
    )
    assert after["household_net_income"] == pytest.approx(
        before["household_net_income"] - counted
    )
    for variable in compared[2:]:
        assert after[variable] == before[variable], variable


def test_scenario_metadata_carries_the_excluded_benefits():
    """Every scenarios output records which benefit names the running engine
    had removed from household net income."""
    from analysis import compute_ai_scenarios

    baseline = SimpleNamespace(
        policyengine_bundle={
            "net_income_excluded_benefits": ["early_head_start", "head_start"]
        }
    )
    metadata = compute_ai_scenarios._metadata(baseline, 2030, [])
    assert metadata["net_income_excluded_benefits"] == [
        "early_head_start",
        "head_start",
    ]
    assert metadata["runtime_fingerprint"]["net_income_excluded_benefits"] == sorted(
        EXCLUDED
    )
