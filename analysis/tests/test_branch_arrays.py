"""analysis.branch_arrays: a branch shares its parent's cached arrays, and each
simulation copies a shared array the first time it reads it.

Invariants (policyengine-core#556's, plus the parent's copy on first read, on
the pinned core 3.30.3):

- Isolation: nothing done through a branch changes a value its parent reads,
  and nothing the parent does after branching, in-place writes into what it
  reads included, changes a value the branch reads.
- Snapshot: a branch reads its parent's values as they were when the branch
  was made, whatever the parent stores, deletes or writes afterwards.
- Differential: every read equals, in dtype and bytes, the read the same steps
  give when each branch copies every array up front.
- No copy without a read: an array neither simulation has read since the
  branch was made shares memory between them, and nothing can write through
  either simulation's copy.

Isolation and the differential fail only after an in-place write, in three
cases, each intended and pinned below: a write through a reference from before
the branch, which raises instead with frozen sources; a write through a view
made before the branch; and a write into the parent's copy of an array that
something else still holds, such as a reference from before the branch or a
second variable core stored the same array under. The first two reach a
branch; the third changes only what the parent reads.

Every test here but the first needs policyengine-core 3.30.3, and the last
needs policyengine-us; CI installs neither, so they skip there.
"""

import importlib.metadata

import numpy as np
import pytest

from analysis import branch_arrays

PERIODS = ("2022-01", "2022-02")
COMPUTED = (
    "income_tax",
    "social_security_contribution",
    "basic_income",
    "disposable_income",
)


def test_install_refuses_another_core(monkeypatch):
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "3.31.0")
    with pytest.raises(RuntimeError, match="3.30.3"):
        branch_arrays.install()
    assert not branch_arrays.installed()
    assert branch_arrays.metadata() == {"shared_until_first_read": False}


def _template(salaries=(4000.0, 2500.0)):
    template = pytest.importorskip("policyengine_core.country_template")
    from policyengine_core.country_template.situation_examples import couple

    sim = template.Simulation(situation=couple)
    for period in PERIODS:
        sim.set_input("salary", period, np.array(salaries, dtype=np.float32))
    return sim


def _storage(sim, variable):
    return sim.persons.get_holder(variable)._memory_storage


def _contents(array):
    """An array's dtype and values: bytes, or the objects in an object array,
    whose bytes are pointers."""
    array = np.asarray(array)
    if array.dtype.hasobject:
        return array.dtype.str, tuple(array.tolist())
    return array.dtype.str, array.tobytes()


def test_a_branch_shares_each_array_until_it_reads_it():
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=False):
        tax = np.array(sim.calculate("income_tax", "2022-01"))
        branch = sim.get_branch("raise")
        key = "default:2022-01"
        parent_array = _storage(sim, "income_tax")._arrays[key]
        held = _storage(branch, "income_tax")._arrays[key]
        assert np.shares_memory(held, parent_array)
        assert not held.flags.writeable
        assert key in _storage(branch, "income_tax")._shared
        assert key in _storage(sim, "income_tax")._shared

        read = branch.calculate("income_tax", "2022-01")
        assert read.flags.writeable
        assert not np.shares_memory(read, parent_array)
        assert key not in _storage(branch, "income_tax")._shared
        np.testing.assert_array_equal(read, tax)

        # The branch's copy is its own: writing into it leaves the parent alone.
        read += 1
        np.testing.assert_array_equal(sim.calculate("income_tax", "2022-01"), tax)
        np.testing.assert_array_equal(
            branch.calculate("income_tax", "2022-01"), tax + 1
        )
        # An array the branch never reads stays shared.
        assert np.shares_memory(
            _storage(branch, "salary")._arrays["default:2022-02"],
            _storage(sim, "salary")._arrays["default:2022-02"],
        )


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_a_parent_write_after_branching_stays_out_of_the_branch(freeze_sources):
    # policyengine-us 1.764.6's ga_deductions runs ``itemized -= ...`` on a
    # cached array. Under #556 alone, such a write after branching reaches a
    # branch that hasn't read the array yet.
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=freeze_sources):
        expected = np.array(sim.calculate("income_tax", "2022-01"))
        branch = sim.get_branch("raise")
        again = sim.calculate("income_tax", "2022-01")
        assert again.flags.writeable
        again -= 5
        np.testing.assert_array_equal(
            sim.calculate("income_tax", "2022-01"), expected - 5
        )
        np.testing.assert_array_equal(
            branch.calculate("income_tax", "2022-01"), expected
        )


def test_frozen_sources_turn_a_write_through_an_earlier_reference_into_an_error():
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        tax = sim.calculate("income_tax", "2022-01")
        sim.get_branch("raise")
        with pytest.raises(ValueError, match="read-only"):
            tax += 1
        # What the parent calculates after branching stays writeable.
        assert sim.calculate("disposable_income", "2022-02").flags.writeable


def test_without_frozen_sources_a_write_through_an_earlier_reference_reaches_the_branch():
    # Intended, and the reason the sweep freezes sources.
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=False):
        tax = sim.calculate("income_tax", "2022-01")
        expected = np.array(tax)
        branch = sim.get_branch("raise")
        tax += 1
        np.testing.assert_array_equal(
            branch.calculate("income_tax", "2022-01"), expected + 1
        )


def _view_write_after_branching(sim):
    """What a branch reads after a write through a view made before it."""
    tax = sim.calculate("income_tax", "2022-01")
    expected = np.array(tax)
    view = tax[:]
    branch = sim.get_branch("raise")
    view += 1
    return expected, branch.calculate("income_tax", "2022-01")


def test_frozen_sources_leave_a_view_from_before_the_branch_writeable():
    # Intended: marking an array read-only leaves its existing views writeable,
    # so a write through one reaches a branch that hasn't read the array, where
    # copying up front keeps the branch's values. The module docstring says why
    # the sweep makes no such write.
    expected, read = _view_write_after_branching(_template())
    np.testing.assert_array_equal(read, expected)
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        expected, read = _view_write_after_branching(_template())
    np.testing.assert_array_equal(read, expected + 1)


def _alias_variable():
    """A variable whose formula returns ``income_tax``'s own array, so core
    stores that one array under two variables."""
    pytest.importorskip("policyengine_core")
    from policyengine_core.country_template.entities import Person
    from policyengine_core.periods import MONTH
    from policyengine_core.variables import Variable

    class income_tax_alias(Variable):
        value_type = float
        entity = Person
        definition_period = MONTH
        label = "income_tax, stored again under a second variable"

        def formula(person, period, parameters):
            return person("income_tax", period)

    return income_tax_alias


def _template_with(*variables):
    template = pytest.importorskip("policyengine_core.country_template")
    from policyengine_core.country_template.situation_examples import couple

    system = template.CountryTaxBenefitSystem()
    system.add_variables(*variables)
    sim = template.Simulation(tax_benefit_system=system, situation=couple)
    for period in PERIODS:
        sim.set_input("salary", period, np.array([4000.0, 2500.0], dtype=np.float32))
    return sim


def _write_into_a_fresh_read_after_branching(sim):
    """After the parent writes into a fresh read of ``income_tax``: what a
    reference from before the branch holds, what ``income_tax_alias`` holds,
    what the parent stores and what the branch reads."""
    sim.calculate("income_tax_alias", "2022-01")
    held = sim.calculate("income_tax", "2022-01")
    expected = np.array(held)
    branch = sim.get_branch("raise")
    fresh = sim.calculate("income_tax", "2022-01")
    fresh -= 5
    return {
        "expected": expected,
        "held": np.array(held),
        "alias": np.array(sim.calculate("income_tax_alias", "2022-01")),
        "stored": np.array(sim.calculate("income_tax", "2022-01")),
        "branch": np.array(branch.calculate("income_tax", "2022-01")),
    }


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_the_parent_s_first_read_after_branching_splits_an_array_core_shares(
    freeze_sources,
):
    # Intended: the parent copies a shared array the first time it reads it,
    # so a write into that copy misses whatever still holds the array it
    # replaced. Core never copies in the parent, so there the write lands in
    # the one array every holder sees. Nothing writes through the frozen array,
    # so freezing can't catch this; the module docstring says why the sweep
    # makes no such write.
    core = _write_into_a_fresh_read_after_branching(_template_with(_alias_variable()))
    with branch_arrays.shared_branch_arrays(freeze_sources=freeze_sources):
        port = _write_into_a_fresh_read_after_branching(
            _template_with(_alias_variable())
        )
    for run in (core, port):
        np.testing.assert_array_equal(run["stored"], run["expected"] - 5)
        np.testing.assert_array_equal(run["branch"], run["expected"])
    np.testing.assert_array_equal(core["held"], core["expected"] - 5)
    np.testing.assert_array_equal(core["alias"], core["expected"] - 5)
    np.testing.assert_array_equal(port["held"], port["expected"])
    np.testing.assert_array_equal(port["alias"], port["expected"])


def test_what_the_parent_stores_after_branching_stays_out_of_the_branch():
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        tax = np.array(sim.calculate("income_tax", "2022-01"))
        branch = sim.get_branch("raise")
        sim.set_input("salary", "2022-01", np.array([1.0, 1.0], dtype=np.float32))
        sim.delete_arrays("income_tax")
        np.testing.assert_array_equal(
            branch.calculate("salary", "2022-01"), [4000.0, 2500.0]
        )
        np.testing.assert_array_equal(branch.calculate("income_tax", "2022-01"), tax)
        assert not np.array_equal(sim.calculate("income_tax", "2022-01"), tax)


def test_put_and_delete_drop_the_marks_they_replace():
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=False):
        for period in PERIODS:
            sim.calculate("income_tax", period)
        storage = _storage(sim.get_branch("raise"), "income_tax")
        assert storage._shared == {"default:2022-01", "default:2022-02"}
        storage.put(np.zeros(2, dtype=np.float32), "2022-01")
        assert storage._shared == {"default:2022-02"}
        storage.delete("2022-02")
        assert storage._shared == set()
        assert storage.get("2022-02") is None
        np.testing.assert_array_equal(storage.get("2022-01"), [0.0, 0.0])


def test_a_branch_of_a_branch_reads_its_parent_s_snapshot():
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        sim.calculate("income_tax", "2022-01")
        first = sim.get_branch("first")
        first.set_input("salary", "2022-02", np.array([10.0, 20.0], dtype=np.float32))
        first_tax = np.array(first.calculate("income_tax", "2022-02"))
        second = first.get_branch("second")
        np.testing.assert_array_equal(
            second.calculate("income_tax", "2022-02"), first_tax
        )
        np.testing.assert_array_equal(
            second.calculate("income_tax", "2022-01"),
            sim.calculate("income_tax", "2022-01"),
        )


def test_a_direct_clone_still_copies_every_array():
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        sim.calculate("income_tax", "2022-01")
        clone = sim.clone()
        key = "default:2022-01"
        assert "_shared" not in _storage(clone, "income_tax").__dict__
        assert not np.shares_memory(
            _storage(clone, "income_tax")._arrays[key],
            _storage(sim, "income_tax")._arrays[key],
        )
        assert _storage(sim, "income_tax")._arrays[key].flags.writeable


def test_the_with_block_puts_core_back():
    pytest.importorskip("policyengine_core")

    def current():
        return {
            name: owner.__dict__[attribute]
            for name, owner, attribute, _ in branch_arrays._targets()
        }

    before = current()
    with branch_arrays.shared_branch_arrays():
        assert branch_arrays.installed()
        assert all(
            current()[name] is replacement
            for name, _, _, replacement in branch_arrays._targets()
        )
        assert branch_arrays.metadata() == {
            "shared_until_first_read": True,
            "port_of": branch_arrays.UPSTREAM,
            "parent_copies_on_first_read": True,
            "sources_frozen": True,
            "policyengine_core_version": branch_arrays.CORE_VERSION,
        }
    assert not branch_arrays.installed()
    assert current() == before


# Differential property test: the same steps on a tree of simulations, once
# with branches that copy every array up front (core 3.30.3 as shipped) and
# once with shared arrays. Indexes pick a simulation modulo the tree's size.
def _steps():
    hypothesis = pytest.importorskip("hypothesis")
    st = hypothesis.strategies
    sim_index = st.integers(0, 7)
    salaries = st.lists(st.floats(0, 1e5, width=32), min_size=2, max_size=2)
    return st.lists(
        st.one_of(
            st.tuples(st.just("branch"), sim_index, st.integers(0, 2)),
            st.tuples(st.just("set"), sim_index, st.sampled_from(PERIODS), salaries),
            st.tuples(
                st.just("calculate"),
                sim_index,
                st.sampled_from(COMPUTED + ("salary",)),
                st.sampled_from(PERIODS),
            ),
            st.tuples(st.just("delete"), sim_index, st.sampled_from(COMPUTED)),
            st.tuples(
                st.just("write"),
                sim_index,
                st.sampled_from(COMPUTED),
                st.sampled_from(PERIODS),
            ),
        ),
        max_size=30,
    )


def _run(steps):
    """Each step's outcome, every array each simulation holds at the end, and
    the step a frozen source stopped (None if none did)."""
    sims = [_template()]
    outcomes = []
    for step in steps:
        kind, index = step[0], step[1] % len(sims)
        sim = sims[index]
        try:
            if kind == "branch":
                sims.append(sim.get_branch(f"b{step[2]}"))
                outcome = ("branch", sims.index(sims[-1]))
            elif kind == "set":
                sim.set_input("salary", step[2], np.array(step[3], dtype=np.float32))
                outcome = ("set",)
            elif kind == "calculate":
                outcome = ("value", *_contents(sim.calculate(step[2], step[3])))
            elif kind == "delete":
                sim.delete_arrays(step[2])
                outcome = ("delete",)
            else:
                value = sim.calculate(step[2], step[3])
                value += 1
                outcome = ("write",)
        except ValueError as error:
            if kind == "write" and "read-only" in str(error):
                return outcomes, None, len(outcomes)
            outcome = ("error", type(error).__name__, str(error))
        outcomes.append(outcome)
    held = [
        {
            (name, key): _contents(array)
            for name, holder in sim.persons._holders.items()
            for key, array in holder._memory_storage._arrays.items()
        }
        for sim in sims
    ]
    return outcomes, held, None


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_shared_branches_read_what_full_copies_hold(freeze_sources):
    hypothesis = pytest.importorskip("hypothesis")
    _template()  # skip without policyengine-core

    @hypothesis.settings(
        max_examples=150,
        deadline=None,
        suppress_health_check=[hypothesis.HealthCheck.too_slow],
    )
    @hypothesis.given(_steps())
    def check(steps):
        copied, copied_held, _ = _run(steps)
        with branch_arrays.shared_branch_arrays(freeze_sources=freeze_sources):
            shared, shared_held, stopped = _run(steps)
        # Each write here goes into a value read just before it, after any
        # branch it follows, so a frozen source never stops one.
        assert stopped is None
        assert shared == copied
        assert shared_held == copied_held

    check()


# policyengine-us households whose taxes open the itemizing, not_itemizing,
# no_salt and state credit branches, and a Georgia itemizer, whose
# ga_deductions writes in place into the cached federal itemized deductions.
US_YEAR = 2026
Y = str(US_YEAR)  # situation periods are strings
US_SITUATION = {
    "people": {
        "ny_head": {
            "age": {Y: 45},
            "employment_income": {Y: 185_000},
            "real_estate_taxes": {Y: 16_000},
            "deductible_mortgage_interest": {Y: 21_000},
            "charitable_cash_donations": {Y: 4_000},
        },
        "ny_spouse": {"age": {Y: 43}, "employment_income": {Y: 62_000}},
        "ny_child": {"age": {Y: 8}},
        "ny_baby": {"age": {Y: 1}},
        "va_head": {"age": {Y: 31}, "employment_income": {Y: 23_000}},
        "va_child": {"age": {Y: 3}},
        "de_head": {
            "age": {Y: 52},
            "employment_income": {Y: 41_000},
            "real_estate_taxes": {Y: 3_000},
        },
        "de_child": {"age": {Y: 12}},
        "ga_head": {
            "age": {Y: 58},
            "employment_income": {Y: 150_000},
            "real_estate_taxes": {Y: 9_000},
            "deductible_mortgage_interest": {Y: 18_000},
            "charitable_cash_donations": {Y: 6_000},
        },
        "ga_spouse": {"age": {Y: 56}, "employment_income": {Y: 70_000}},
    },
    "tax_units": {
        "ny": {"members": ["ny_head", "ny_spouse", "ny_child", "ny_baby"]},
        "va": {"members": ["va_head", "va_child"]},
        "de": {"members": ["de_head", "de_child"]},
        "ga": {"members": ["ga_head", "ga_spouse"]},
    },
    "spm_units": {
        "ny": {"members": ["ny_head", "ny_spouse", "ny_child", "ny_baby"]},
        "va": {"members": ["va_head", "va_child"]},
        "de": {"members": ["de_head", "de_child"]},
        "ga": {"members": ["ga_head", "ga_spouse"]},
    },
    "families": {
        "ny": {"members": ["ny_head", "ny_spouse", "ny_child", "ny_baby"]},
        "va": {"members": ["va_head", "va_child"]},
        "de": {"members": ["de_head", "de_child"]},
        "ga": {"members": ["ga_head", "ga_spouse"]},
    },
    "marital_units": {
        "ny": {"members": ["ny_head", "ny_spouse"]},
        "ny_child": {"members": ["ny_child"]},
        "ny_baby": {"members": ["ny_baby"]},
        "va": {"members": ["va_head"]},
        "va_child": {"members": ["va_child"]},
        "de": {"members": ["de_head"]},
        "de_child": {"members": ["de_child"]},
        "ga": {"members": ["ga_head", "ga_spouse"]},
    },
    "households": {
        "ny": {
            "members": ["ny_head", "ny_spouse", "ny_child", "ny_baby"],
            "state_code": {Y: "NY"},
        },
        "va": {"members": ["va_head", "va_child"], "state_code": {Y: "VA"}},
        "de": {"members": ["de_head", "de_child"], "state_code": {Y: "DE"}},
        "ga": {"members": ["ga_head", "ga_spouse"], "state_code": {Y: "GA"}},
    },
}
US_VARIABLES = (
    "household_net_income",
    "income_tax",
    "state_income_tax",
    "tax_unit_itemizes",
    "ctc_limiting_tax_liability",
    "refundable_ctc",
)


def _every_array(sim, path="root"):
    """Every array each simulation in the tree holds, by branch path."""
    held = {}
    for population in sim.populations.values():
        for name, holder in population._holders.items():
            for key, array in holder._memory_storage._arrays.items():
                held[(path, name, key)] = _contents(array)
    for name, branch in sim.branches.items():
        held.update(_every_array(branch, f"{path}/{name}"))
    return held


def _us_run():
    from policyengine_us import Simulation

    sim = Simulation(situation=US_SITUATION)
    values = {name: _contents(sim.calculate(name, US_YEAR)) for name in US_VARIABLES}
    shared = sum(
        len(holder._memory_storage.__dict__.get("_shared", ()))
        for branch in sim.branches.values()
        for population in branch.populations.values()
        for holder in population._holders.values()
    )
    return values, _every_array(sim), shared


def test_policyengine_us_branches_read_what_full_copies_hold():
    pytest.importorskip("policyengine_us")
    copied_values, copied_held, _ = _us_run()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        shared_values, shared_held, still_shared = _us_run()
    paths = {key[0] for key in copied_held}
    assert {"root/itemizing", "root/not_itemizing"} <= paths
    assert any(path.endswith("/no_salt") for path in paths)
    assert still_shared > 0  # the branches left most arrays unread
    assert shared_values == copied_values
    assert shared_held.keys() == copied_held.keys()
    assert shared_held == copied_held
