"""analysis.branch_arrays: a branch shares its parent's cached arrays, and each
simulation copies a shared array the first time it reads it.

Invariants (policyengine-core#556's, plus the parent's copy on first read, on
the pinned core 3.30.3):

- Isolation: nothing done through a branch changes a value its parent reads,
  and nothing the parent does after branching, in-place writes into what it
  reads included, changes a value the branch reads.
- Snapshot: a branch reads its parent's values as they were when the branch
  was made, whatever the parent stores, deletes or writes afterwards.
- Differential: every read equals, in dtype, shape and bytes, the read the same
  steps give when each branch copies every array up front.
- No copy without a read: an array neither simulation has read since the
  branch was made shares memory between them, and nothing can write through
  either simulation's copy.

Isolation and the differential fail only after an in-place write, in three
cases, each intended and pinned below:

- a write through a stored array by a reference from before the branch (with
  frozen sources, it raises instead);
- a write through another array over the same memory held from before the
  branch, such as a view or the 0-dim array a formula returned;
- a write into the parent's copy of an array that something else still holds:
  a reference from before the branch, or another variable or month core stored
  the same array under.

The first two reach a branch; the third changes only what the parent reads.

After a branch, the parent reads each array the branch shares through
``Simulation._calculate``, where core serves it from the fast cache. The
differential also fails wherever the two paths disagree with no write at all.
We know three such reads, each intended and pinned below. A formula's 0-dim
result comes back with shape (1,) rather than (). A variable that the parent's
own system neutralized after the parent cached it reads as its default rather
than the cached values. And after a delete of the month's year, or one through
its holder, core's fast cache serves the deleted month, while the parent
computes the month again and stores it.

Every test here but the first needs policyengine-core 3.30.3, and the last
needs policyengine-us; CI installs neither, so they skip there.
"""

import contextlib
import copy
import importlib.metadata
import pickle

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
    """An array's dtype, shape and values: bytes, or the objects in an object
    array, whose bytes are pointers."""
    array = np.asarray(array)
    if array.dtype.hasobject:
        return array.dtype.str, array.shape, tuple(array.tolist())
    return array.dtype.str, array.shape, array.tobytes()


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


def _zero_dim_variable():
    """A variable whose formula returns a 0-dim array. In a one-person
    simulation, core keeps that array in the fast cache and stores a reshaped
    view of it (Holder._to_array), so the two hold different objects over the
    same memory."""
    pytest.importorskip("policyengine_core")
    from policyengine_core.country_template.entities import Person
    from policyengine_core.periods import MONTH
    from policyengine_core.variables import Variable

    class salary_total(Variable):
        value_type = float
        entity = Person
        definition_period = MONTH
        label = "Every person's salary, summed into a 0-dim array"

        def formula(person, period, parameters):
            return np.array(person("salary", period).sum(), dtype=np.float32)

    return salary_total


def _write_into_a_0_dim_result_after_branching(write_through):
    """Parent and branch reads of ``salary_total`` after the parent adds 1
    after branching, through a fresh read (``"fresh read"``) or through the
    0-dim array the first calculation returned (``"first result"``)."""
    template = pytest.importorskip("policyengine_core.country_template")
    from policyengine_core.country_template.situation_examples import single

    system = template.CountryTaxBenefitSystem()
    system.add_variables(_zero_dim_variable())
    sim = template.Simulation(tax_benefit_system=system, situation=single)
    sim.set_input("salary", "2022-01", np.array([3000.0], dtype=np.float32))
    first = sim.calculate("salary_total", "2022-01")
    assert first.ndim == 0
    branch = sim.get_branch("raise")
    target = first if write_through == "first result" else sim.calculate(
        "salary_total", "2022-01"
    )
    target += 1
    return (
        np.array(sim.calculate("salary_total", "2022-01")),
        np.array(branch.calculate("salary_total", "2022-01")),
    )


def _assert_0_dim_shapes(core, port):
    # Intended: core's fast cache hands the parent the 0-dim array the formula
    # returned, and here the parent reads the (1,) view its storage holds. Each
    # branch reads its storage, under core and here.
    assert core[0].shape == ()
    assert port[0].shape == (1,)
    assert core[1].shape == port[1].shape == (1,)


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_a_0_dim_result_the_parent_reads_again_after_branching_stays_its_own(
    freeze_sources,
):
    # The parent's fresh read after branching must miss the fast cache, which
    # holds the 0-dim array the stored view shares memory with.
    core = _write_into_a_0_dim_result_after_branching("fresh read")
    port = _ported(
        freeze_sources, _write_into_a_0_dim_result_after_branching, "fresh read"
    )
    for parent, branch in (core, port):
        np.testing.assert_array_equal(parent.reshape(-1), [3001.0])
        np.testing.assert_array_equal(branch, [3000.0])
    _assert_0_dim_shapes(core, port)


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_a_write_through_the_0_dim_array_a_formula_returned_reaches_the_branch(
    freeze_sources,
):
    # Intended, like a write through a view: the storage holds a view of that
    # 0-dim array, and freezing marks only the view read-only.
    core = _write_into_a_0_dim_result_after_branching("first result")
    port = _ported(
        freeze_sources, _write_into_a_0_dim_result_after_branching, "first result"
    )
    assert [read.reshape(-1).tolist() for read in core] == [[3001.0], [3000.0]]
    assert [read.reshape(-1).tolist() for read in port] == [[3001.0], [3001.0]]
    _assert_0_dim_shapes(core, port)


def _neutralize_after_caching():
    """``income_tax`` before the parent's own system neutralizes it, then the
    parent's and a new branch's reads of it."""
    sim = _template_with()  # its own system, so the change stays in this test
    before = sim.calculate("income_tax", "2022-01").tolist()
    sim.tax_benefit_system.neutralize_variable("income_tax")
    branch = sim.get_branch("raise")
    return (
        before,
        sim.calculate("income_tax", "2022-01").tolist(),
        branch.calculate("income_tax", "2022-01").tolist(),
    )


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_a_variable_neutralized_after_the_parent_cached_it_reads_as_its_default(
    freeze_sources,
):
    # Intended: core's fast cache serves the parent the values it cached,
    # though its own _calculate, which the branch reads through, returns the
    # default for a neutralized variable. Here the parent reads through
    # _calculate too. policyengine-us neutralizes variables only in branches
    # it makes with clone_system=True.
    tax, zero = [600.0, 375.0], [0.0, 0.0]
    assert _neutralize_after_caching() == (tax, tax, zero)
    assert _ported(freeze_sources, _neutralize_after_caching) == (tax, zero, zero)


def _delete_after_branching(delete, new_salary):
    """January's ``income_tax``, then the parent's and a branch's reads of it
    after the parent runs ``delete``, and the periods the parent stores for it
    after its read. With ``new_salary``, the parent doubles January's salaries
    before the delete."""
    sim = _template()
    before = sim.calculate("income_tax", "2022-01").tolist()
    branch = sim.get_branch("raise")
    if new_salary:
        sim.set_input("salary", "2022-01", np.array([8000.0, 5000.0], dtype=np.float32))
    delete(sim)
    parent = sim.calculate("income_tax", "2022-01").tolist()
    stored = sorted(str(period) for period in sim.get_holder("income_tax").get_known_periods())
    return (before, parent, branch.calculate("income_tax", "2022-01").tolist(), stored)


# Core's Simulation.delete_arrays with a period drops only that period's
# fast-cache entry, and Holder.delete_arrays drops none.
FAST_CACHE_KEPT = {
    "the year": lambda sim: sim.delete_arrays("income_tax", "2022"),
    "the holder": lambda sim: sim.get_holder("income_tax").delete_arrays("2022-01"),
}
FAST_CACHE_DROPPED = {
    "the month": lambda sim: sim.delete_arrays("income_tax", "2022-01"),
    "every period": lambda sim: sim.delete_arrays("income_tax"),
}
OLD_TAX, NEW_TAX = [600.0, 375.0], [1200.0, 750.0]


@pytest.mark.parametrize("freeze_sources", [True, False])
@pytest.mark.parametrize("new_salary", [True, False])
@pytest.mark.parametrize("delete", sorted(FAST_CACHE_KEPT))
def test_a_month_deleted_past_core_s_fast_cache_is_computed_again(
    freeze_sources, new_salary, delete
):
    # Intended: core's fast cache serves the parent the deleted month and the
    # storage stays empty. Here the parent reads through _calculate, finds
    # nothing stored, computes the month again, from the new salaries when the
    # parent stored them, and stores it. The sweep deletes no arrays;
    # policyengine-us 1.764.6 deletes through a simulation only without a
    # period, and through a holder only while it builds a simulation.
    steps = FAST_CACHE_KEPT[delete]
    again = NEW_TAX if new_salary else OLD_TAX
    assert _delete_after_branching(steps, new_salary) == (OLD_TAX, OLD_TAX, OLD_TAX, [])
    assert _ported(freeze_sources, _delete_after_branching, steps, new_salary) == (
        OLD_TAX,
        again,
        OLD_TAX,
        ["2022-01"],
    )


@pytest.mark.parametrize("freeze_sources", [True, False])
@pytest.mark.parametrize("new_salary", [True, False])
@pytest.mark.parametrize("delete", sorted(FAST_CACHE_DROPPED))
def test_a_delete_that_drops_core_s_fast_cache_entry_reads_as_core_s(
    freeze_sources, new_salary, delete
):
    steps = FAST_CACHE_DROPPED[delete]
    after = (OLD_TAX, NEW_TAX if new_salary else OLD_TAX, OLD_TAX, ["2022-01"])
    assert _delete_after_branching(steps, new_salary) == after
    assert _ported(freeze_sources, _delete_after_branching, steps, new_salary) == after


def _ported(freeze_sources, steps, *args):
    with branch_arrays.shared_branch_arrays(freeze_sources=freeze_sources):
        return steps(*args)


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


def _set_input_again_after_a_sub_branch():
    """A branch sets ``income_tax``, makes its own branch, then sets it again:
    whether the branch's first read returns the array it passed the second
    time, the branch's read after a write into that array, and the
    sub-branch's read."""
    sim = _template()
    branch = sim.get_branch("B")
    branch.set_input("income_tax", "2022-01", np.array([1.0, 2.0], dtype=np.float32))
    sub_branch = branch.get_branch("Y")
    again = np.array([3.0, 4.0], dtype=np.float32)
    branch.set_input("income_tax", "2022-01", again)
    first = branch.calculate("income_tax", "2022-01")
    again[0] = 99.0
    return (
        first is again,
        branch.calculate("income_tax", "2022-01").tolist(),
        sub_branch.calculate("income_tax", "2022-01").tolist(),
    )


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_a_branch_setting_an_input_again_after_its_own_branch_reads_as_core_s(
    freeze_sources,
):
    # Core's set_input keys a branch's input under the branch's own name, so
    # put has to drop the mark of the key that name builds, not the default's.
    core = _set_input_again_after_a_sub_branch()
    assert core == (True, [99.0, 4.0], [1.0, 2.0])
    assert _ported(freeze_sources, _set_input_again_after_a_sub_branch) == core


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


def test_a_branch_copies_a_masked_array_straight_away():
    # A view of a masked array shares its mask, which a read-only flag on the
    # data leaves writeable, so the branch gets its own copy.
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        storage = _storage(sim, "income_tax")
        storage.put(
            np.ma.masked_array(
                np.array([1.0, 2.0], dtype=np.float32), mask=[False, True]
            ),
            "2022-01",
        )
        key = "default:2022-01"
        source = storage._arrays[key]
        branch_storage = _storage(sim.get_branch("raise"), "income_tax")
        held = branch_storage._arrays[key]
        assert isinstance(held, np.ma.MaskedArray)
        assert not np.shares_memory(held.data, source.data)
        assert not np.shares_memory(held.mask, source.mask)
        np.testing.assert_array_equal(held.mask, [False, True])
        assert source.flags.writeable
        assert "_shared" not in storage.__dict__
        assert "_shared" not in branch_storage.__dict__


def test_a_branch_reads_an_enum_array_as_its_parent_holds_it():
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        status = sim.calculate("housing_occupancy_status", "2022-01")
        branch = sim.get_branch("raise")

        def stored(simulation):
            holder = simulation.populations["household"].get_holder(
                "housing_occupancy_status"
            )
            return holder._memory_storage._arrays["default:2022-01"]

        held = stored(branch)
        assert np.shares_memory(held, stored(sim))
        read = branch.calculate("housing_occupancy_status", "2022-01")
        assert read.flags.writeable
        assert not np.shares_memory(read, stored(sim))
        for array in (held, read):
            assert type(array) is type(status)
            assert array.possible_values is status.possible_values
        np.testing.assert_array_equal(read.decode_to_str(), status.decode_to_str())


def _write_into_an_enum_after_branching():
    """The parent's and the branch's reads of ``housing_occupancy_status``
    after the parent writes into a fresh read of it after branching."""
    sim = _template()
    sim.calculate("housing_occupancy_status", "2022-01")
    branch = sim.get_branch("raise")
    fresh = sim.calculate("housing_occupancy_status", "2022-01")
    fresh[0] = 2
    return (
        sim.calculate("housing_occupancy_status", "2022-01").decode_to_str().tolist(),
        branch.calculate("housing_occupancy_status", "2022-01").decode_to_str().tolist(),
    )


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_a_parent_write_into_an_enum_after_branching_stays_out_of_the_branch(
    freeze_sources,
):
    # An EnumArray is an ndarray subclass, and the fast-cache drop has to catch
    # it too. Otherwise the parent's fresh read returns the source the branch's
    # view shares, which freezing makes read-only.
    expected = (["free_lodger"], ["tenant"])
    assert _write_into_an_enum_after_branching() == expected
    assert _ported(freeze_sources, _write_into_an_enum_after_branching) == expected


def _nickname_variable():
    """A string variable with no ``max_length``, which core stores as an object
    array, as it does policyengine-us's string variables."""
    pytest.importorskip("policyengine_core")
    from policyengine_core.country_template.entities import Person
    from policyengine_core.periods import MONTH
    from policyengine_core.variables import Variable

    class nickname(Variable):
        value_type = str
        entity = Person
        definition_period = MONTH
        label = "Nickname"

    return nickname


def _write_into_a_nickname_after_branching(check_sharing=False):
    sim = _template_with(_nickname_variable())
    sim.set_input("nickname", "2022-01", np.array(["Ada", "Bo"], dtype=object))
    branch = sim.get_branch("rename")
    if check_sharing:
        key = "default:2022-01"
        held = _storage(branch, "nickname")._arrays[key]
        assert held.dtype == object
        assert np.shares_memory(held, _storage(sim, "nickname")._arrays[key])
        assert not held.flags.writeable
    fresh = sim.calculate("nickname", "2022-01")
    fresh[0] = "Cy"
    return (
        _contents(sim.calculate("nickname", "2022-01")),
        _contents(branch.calculate("nickname", "2022-01")),
    )


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_an_object_array_reads_as_core_s_after_a_parent_write(freeze_sources):
    core = _write_into_a_nickname_after_branching()
    port = _ported(freeze_sources, _write_into_a_nickname_after_branching, True)
    assert core == (("|O", (2,), ("Cy", "Bo")), ("|O", (2,), ("Ada", "Bo")))
    assert port == core


def test_a_branch_with_its_own_system_shares_arrays_too():
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        tax = np.array(sim.calculate("income_tax", "2022-01"))
        branch = sim.get_branch("reform", clone_system=True)
        assert branch.tax_benefit_system is not sim.tax_benefit_system
        key = "default:2022-01"
        assert np.shares_memory(
            _storage(branch, "income_tax")._arrays[key],
            _storage(sim, "income_tax")._arrays[key],
        )
        assert key in _storage(branch, "income_tax")._shared
        np.testing.assert_array_equal(branch.calculate("income_tax", "2022-01"), tax)


def test_a_direct_holder_read_copies_a_shared_array():
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        tax = np.array(sim.calculate("income_tax", "2022-01"))
        branch = sim.get_branch("raise")
        key = "default:2022-01"
        source = _storage(sim, "income_tax")._arrays[key]
        read = branch.persons.get_holder("income_tax").get_array("2022-01")
        assert read.flags.writeable
        assert not np.shares_memory(read, source)
        assert key not in _storage(branch, "income_tax")._shared
        np.testing.assert_array_equal(read, tax)


def _write_into_one_month_of_a_yearly_salary():
    """Parent and branch reads after the parent writes into January's salary
    after branching. Core's ``set_input_divide_by_period`` stores the one array
    it builds from a yearly salary under every month."""
    sim = _template()
    sim.set_input("salary", "2023", np.array([12_000.0, 24_000.0], dtype=np.float32))
    stored = _storage(sim, "salary")._arrays
    assert all(
        stored[f"default:2023-{month:02d}"] is stored["default:2023-01"]
        for month in range(2, 13)
    )
    branch = sim.get_branch("raise")
    january = sim.calculate("salary", "2023-01")
    january += 1
    return (
        sim.calculate("salary", "2023-01").tolist(),
        sim.calculate("salary", "2023-02").tolist(),
        branch.calculate("salary", "2023-02").tolist(),
    )


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_a_write_into_one_month_of_a_yearly_input_stays_in_that_month(
    freeze_sources,
):
    # Intended, like the second variable above: under core the write lands in
    # the one array all twelve months hold, and here the parent's first read
    # of January after branching copies January's alone.
    january, february = [1001.0, 2001.0], [1000.0, 2000.0]
    assert _write_into_one_month_of_a_yearly_salary() == (january, january, february)
    assert _ported(freeze_sources, _write_into_one_month_of_a_yearly_salary) == (
        january,
        february,
        february,
    )


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


@pytest.mark.parametrize("outer, inner", [(True, False), (False, True)])
def test_a_nested_block_puts_back_the_outer_block_s_freezing(outer, inner):
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=outer):
        with branch_arrays.shared_branch_arrays(freeze_sources=inner):
            assert branch_arrays.metadata()["sources_frozen"] is inner
        assert branch_arrays.installed()
        assert branch_arrays.metadata()["sources_frozen"] is outer
        sim.calculate("income_tax", "2022-01")
        sim.get_branch("raise")
        source = _storage(sim, "income_tax")._arrays["default:2022-01"]
        assert source.flags.writeable == (not outer)
    assert not branch_arrays.installed()


def _branch_in_a_block_then_write_after_it(block):
    """What a parent and its branch read after ``block`` closes, once each has
    written in place into what it read. The branch comes from inside the
    block."""
    sim = _template()
    with block:
        sim.calculate("income_tax", "2022-01")
        branch = sim.get_branch("raise")
    parent = sim.calculate("income_tax", "2022-01")
    parent += 6
    child = branch.calculate("income_tax", "2022-01")
    child -= 3
    return (
        sim.calculate("income_tax", "2022-01").tolist(),
        branch.calculate("income_tax", "2022-01").tolist(),
        branch.calculate("income_tax", "2022-02").tolist(),
    )


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_a_simulation_made_inside_the_block_reads_core_s_values_after_it(
    freeze_sources,
):
    core = _branch_in_a_block_then_write_after_it(contextlib.nullcontext())
    port = _branch_in_a_block_then_write_after_it(
        branch_arrays.shared_branch_arrays(freeze_sources=freeze_sources)
    )
    assert not branch_arrays.installed()
    assert port == core


def _set_input_after_the_block(block):
    """After ``block`` closes, the parent sets ``income_tax`` over a key it
    still shares: whether its first read returns the array it passed, and its
    read after a write into that array."""
    sim = _template()
    with block:
        sim.calculate("income_tax", "2022-01")
        sim.get_branch("raise")
    new = np.array([10.0, 20.0], dtype=np.float32)
    sim.set_input("income_tax", "2022-01", new)
    first = sim.calculate("income_tax", "2022-01")
    new[0] = 99.0
    return first is new, sim.calculate("income_tax", "2022-01").tolist()


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_an_input_set_after_the_block_over_a_shared_key_reads_as_core_s(
    freeze_sources,
):
    # After the block, put has to keep dropping the mark of the key it
    # replaces, or the next read copies the input and misses the write.
    core = _set_input_after_the_block(contextlib.nullcontext())
    port = _set_input_after_the_block(
        branch_arrays.shared_branch_arrays(freeze_sources=freeze_sources)
    )
    assert core == (True, [99.0, 20.0])
    assert port == core


@pytest.mark.parametrize(
    "round_trip",
    [lambda storage: pickle.loads(pickle.dumps(storage)), copy.deepcopy],
    ids=["pickle", "deepcopy"],
)
def test_a_storage_that_still_shares_after_the_block_survives_a_round_trip(
    round_trip,
):
    sim = _template()
    with branch_arrays.shared_branch_arrays(freeze_sources=True):
        tax = np.array(sim.calculate("income_tax", "2022-01"))
        branch = sim.get_branch("raise")
    key = "default:2022-01"
    for storage in (_storage(sim, "income_tax"), _storage(branch, "income_tax")):
        assert key in storage._shared
        back = round_trip(storage)
        read = back.get("2022-01")
        assert read.flags.writeable
        assert not np.shares_memory(read, storage._arrays[key])
        np.testing.assert_array_equal(read, tax)
        # The copy's methods act on the copy, not on the storage it came from.
        assert back._arrays[key] is read
        assert key not in back._shared
        assert key in storage._shared


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
            # Every period or one month: a delete of a year, or one through a
            # holder, can leave core's fast cache serving a deleted month, a
            # difference pinned above.
            st.tuples(
                st.just("delete"),
                sim_index,
                st.sampled_from(COMPUTED),
                st.sampled_from((None,) + PERIODS),
            ),
            st.tuples(st.just("purge"), sim_index),
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
                sim.delete_arrays(step[2], step[3])
                outcome = ("delete",)
            elif kind == "purge":
                # What apply_reform runs: drop every calculated array in the
                # simulation and its branches, and put back the inputs.
                sim._invalidate_all_caches()
                outcome = ("purge",)
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


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_a_purge_after_branching_reads_what_full_copies_hold(freeze_sources):
    _template()  # skip without policyengine-core
    steps = [
        ("calculate", 0, "disposable_income", "2022-01"),
        ("branch", 0, 0),
        ("purge", 0),
        ("write", 0, "salary", "2022-01"),
        ("write", 0, "income_tax", "2022-01"),
        ("calculate", 1, "income_tax", "2022-01"),
        ("purge", 1),
        ("calculate", 1, "disposable_income", "2022-01"),
        ("calculate", 0, "disposable_income", "2022-01"),
    ]
    copied = _run(steps)
    assert copied[2] is None
    assert _ported(freeze_sources, _run, steps) == copied


# policyengine-us households whose taxes open the itemizing, not_itemizing,
# no_salt and state credit branches; a Georgia itemizer with an adjustment, so
# ga_deductions' in-place write into the cached federal itemized deductions
# changes bytes; and a Utah parent with a newborn, whom ut_personal_exemption
# adds into ut_total_dependents in place. Without the adjustment and the
# newborn, policyengine-core#556 alone gives these households the same bytes
# as full copies.
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
        "ut_head": {"age": {Y: 34}, "employment_income": {Y: 58_000}},
        "ut_baby": {"age": {Y: 0}},
    },
    "tax_units": {
        "ny": {"members": ["ny_head", "ny_spouse", "ny_child", "ny_baby"]},
        "va": {"members": ["va_head", "va_child"]},
        "de": {"members": ["de_head", "de_child"]},
        "ga": {
            "members": ["ga_head", "ga_spouse"],
            "ga_itemized_deductions_adjustment": {Y: 2_000},
        },
        "ut": {"members": ["ut_head", "ut_baby"]},
    },
    "spm_units": {
        "ny": {"members": ["ny_head", "ny_spouse", "ny_child", "ny_baby"]},
        "va": {"members": ["va_head", "va_child"]},
        "de": {"members": ["de_head", "de_child"]},
        "ga": {"members": ["ga_head", "ga_spouse"]},
        "ut": {"members": ["ut_head", "ut_baby"]},
    },
    "families": {
        "ny": {"members": ["ny_head", "ny_spouse", "ny_child", "ny_baby"]},
        "va": {"members": ["va_head", "va_child"]},
        "de": {"members": ["de_head", "de_child"]},
        "ga": {"members": ["ga_head", "ga_spouse"]},
        "ut": {"members": ["ut_head", "ut_baby"]},
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
        "ut": {"members": ["ut_head"]},
        "ut_baby": {"members": ["ut_baby"]},
    },
    "households": {
        "ny": {
            "members": ["ny_head", "ny_spouse", "ny_child", "ny_baby"],
            "state_code": {Y: "NY"},
        },
        "va": {"members": ["va_head", "va_child"], "state_code": {Y: "VA"}},
        "de": {"members": ["de_head", "de_child"], "state_code": {Y: "DE"}},
        "ga": {"members": ["ga_head", "ga_spouse"], "state_code": {Y: "GA"}},
        "ut": {"members": ["ut_head", "ut_baby"], "state_code": {Y: "UT"}},
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


@pytest.mark.parametrize("freeze_sources", [True, False])
def test_policyengine_us_branches_read_what_full_copies_hold(freeze_sources):
    pytest.importorskip("policyengine_us")
    copied_values, copied_held, _ = _us_run()
    with branch_arrays.shared_branch_arrays(freeze_sources=freeze_sources):
        shared_values, shared_held, still_shared = _us_run()
    paths = {key[0] for key in copied_held}
    assert {"root/itemizing", "root/not_itemizing"} <= paths
    assert any(path.endswith("/no_salt") for path in paths)
    assert still_shared > 0  # the branches left most arrays unread
    assert shared_values == copied_values
    assert shared_held.keys() == copied_held.keys()
    assert shared_held == copied_held
