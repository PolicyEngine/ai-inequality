"""Share a simulation's cached arrays with its branches, and copy on first read.

policyengine-core 3.30.3, the core the pinned runtime runs, copies every
cached array of every variable into each branch that ``Simulation.get_branch``
makes. policyengine-us 1.764.6 makes branches inside its formulas
(``itemizing``, ``not_itemizing``, ``no_salt``, and Delaware's, Virginia's and
New York's credit branches) and keeps them for the life of the simulation. On
the full microdata, the sweep's baseline stage passed a 39 GB footprint while
``ctc_limiting_tax_liability`` copied the cache into its ``no_salt`` branch.

policyengine-core#556 (c991b38b2, merged 2 Oct 2026) fixed this upstream: a
branch holds read-only views of its parent's arrays and copies an array only
when it first reads it. Its author measured a one-year US baseline at a 48.2 GB
peak footprint before and 8.7 GB after. #556 first shipped in core 3.32.12,
which also carries every change since 3.30.3, and some of those can change
results: 3.30.4 makes ``Microsimulation.calculate_add`` and
``calculate_divide`` honor ``map_to``, and 3.32.8 uprates an input from its
latest known earlier period rather than one picked by list position. Later
releases add more, such as #562 (3.32.16), which carries over only inputs, and
#560 (3.33.0), which makes ``set_input`` on a branch drop the values the branch
calculated from the input it replaces. So the pinned runtime keeps 3.30.3, and
``install`` ports #556 onto it and closes the one gap #556's docstrings state.

That gap: under #556, code that writes in place into one of a parent's cached
arrays after branching changes the value a branch reads, if the branch hasn't
read that array yet. So here the parent copies too: making a branch marks each
array it shares in both simulations, and each simulation copies a marked array
the first time it reads it, so neither reads the other's writes. Making a
branch also drops each of the parent's fast-cache entries
(``Simulation._fast_cache``) that shares a base array with an array the branch
shares, so the parent's reads reach its storage, which copies. (For a formula
that returns a 0-dim array, the fast cache holds that array and the storage a
reshaped view of it.) With ``freeze_sources`` (the sweep's setting), making a
branch also marks every array it shares read-only, so a formula that writes
through a stored array, by a reference it took before the branch, raises
``ValueError`` instead of changing a result.

With ``freeze_sources``, writes can still make a run read values that copying
every array up front wouldn't give, but only in-place writes after a branch,
in one of two ways:

- through another array over a shared array's memory, held from before the
  branch: a view of the shared array, or the array it views, such as the 0-dim
  array a formula returned or the data frame a flat-file dataset's input came
  from. Marking an array read-only leaves those writeable;
- into the parent's copy of an array while something else still holds the
  array that copy replaced: a formula's reference from before the branch, or a
  second storage key that core filled with the same object. Under core the
  write lands in the one array every holder sees; here the other holder keeps
  the old values.

Without ``freeze_sources``, a write through a stored array, by a reference
from before the branch, also reaches a branch that hasn't read the array.

Making a branch drops the parent's fast-cache entries for the arrays the
branch shares, so after a branch the parent reads those arrays through
``Simulation._calculate``. Core's ``Simulation.calculate`` serves them from the
fast cache, so wherever the two paths disagree, the parent gets
``_calculate``'s answer and core gets the cached one, with no write at all. We
know three such cases:

- A formula's 0-dim result reads as the ``(1,)`` view the storage holds, where
  core returns the 0-dim array.
- If the parent's own system neutralizes a variable after the parent caches
  it, the parent reads the variable's default, where core returns the cached
  values. ``_calculate`` checks neutralization before it reads the storage.
- After a delete that leaves the fast cache alone, the parent computes the
  value again and stores it, where core returns the deleted value and leaves
  the storage empty. ``Holder.delete_arrays`` never touches the fast cache,
  and ``Simulation.delete_arrays`` with a period drops only that period's
  entry, so deleting a year leaves its months' entries in place.

None of this happens in the sweep. policyengine-us#9739's scan finds five
formulas in policyengine-us 1.764.6 that write in place into arrays they read
from variables, and none writes into a shared array that anything else holds:

- ``basic_income_phase_in`` writes only when a run sets
  ``include_ss_benefits_as_earnings``, and the sweep doesn't;
- CRFB's ``agi_surtax`` reform is off;
- ``nj_gross_income`` adds into the new array ``add`` builds from its eight
  sources (``add`` returns a variable's own array only when it sums a single
  variable of the formula's entity);
- ``ga_deductions`` subtracts an adjustment the microdata don't carry, so it
  subtracts zero;
- ``ut_personal_exemption``, the only formula that reads
  ``ut_total_dependents``, reads and writes it in one call, with no branch
  made in between.

No formula in 1.764.6 writes through a view of a variable's array, and the
sweep's own code writes only into the accumulators and dicts it builds. Every
population in the sweep holds thousands of members, so no stored array views
a formula's 0-dim result. policyengine-us 1.764.6 neutralizes variables only
in the systems of branches it makes with ``clone_system=True``, so no parent's
system changes under its cache. The sweep's own code deletes no arrays.
policyengine-us 1.764.6 calls ``Simulation.delete_arrays`` only without a
period. It calls ``Holder.delete_arrays`` only while it builds a simulation,
before the simulation has any branch, and in ``BranchedSimulation``, a class it
imports but never uses. And the sweep freezes its sources, so a write through a
stored array by a reference from before a branch would raise.
``analysis.check_branch_arrays`` checks the whole sweep: it runs
``run_shift_sweep`` both ways on a subset of the microdata and compares every
array in every branch, byte for byte.

``Simulation.clone()`` called directly, as ``Simulation.derivative`` does, still
copies every array straight away. After ``uninstall``, a storage that still
shares an array goes on copying it on first read. ``Holder.get_memory_usage``
counts an array a branch still shares for both simulations, though memory
holds it once.
"""

from __future__ import annotations

import contextlib
import functools
import importlib.metadata
import weakref
from contextvars import ContextVar

import numpy

CORE_VERSION = "3.30.3"
UPSTREAM = "policyengine-core#556 (c991b38b2)"

# Set by ``get_branch`` around its ``clone`` call: the simulation it branches.
_branch_request: ContextVar[_BranchClone | None] = ContextVar(
    "ai_inequality_branch_request", default=None
)
# While that clone runs: the ids of the base arrays of the arrays it shares, so
# the clone can drop the parent's fast-cache entries for them. None the rest of
# the time.
_sharing: ContextVar[set | None] = ContextVar(
    "ai_inequality_branch_sharing", default=None
)

# policyengine-core's methods this module replaces, while it replaces them.
_original: dict[str, object] = {}
# Core's storage methods, kept after ``uninstall`` for the storages that still
# share arrays (see ``_keep_copying``).
_core: dict[str, object] = {}
# Every storage that has shared an array since ``install``.
_marked: weakref.WeakSet = weakref.WeakSet()
_settings = {"freeze_sources": False}
_periods = None


class _BranchClone:
    """The simulation ``get_branch`` is about to clone into a new branch.

    Only the first ``clone`` of that simulation while ``get_branch`` runs
    shares arrays, as in #556's ``_BranchClone``.
    """

    __slots__ = ("pending", "simulation")

    def __init__(self, simulation):
        self.simulation = simulation
        self.pending = True


def _can_share(array) -> bool:
    """Whether a read-only view of ``array`` protects everything in it.

    A masked array's mask is a second array that a view shares and leaves
    writeable, and anything that isn't a numpy array has no views, so both get
    copied straight away instead.
    """
    return isinstance(array, numpy.ndarray) and not isinstance(
        array, numpy.ma.MaskedArray
    )


def _read_only_view(array: numpy.ndarray) -> numpy.ndarray:
    """A new view of ``array`` that nothing can write through.

    The view is a new array object even when ``array`` is already read-only,
    so reassigning the source's ``shape`` or ``dtype`` leaves the clone alone.
    """
    view = array.view()
    view.flags.writeable = False
    return view


def _base_array(array: numpy.ndarray) -> numpy.ndarray:
    """The last numpy array in ``array``'s chain of bases: ``array`` itself
    when it owns its memory. Two arrays with the same base array share memory.
    """
    while isinstance(array.base, numpy.ndarray):
        array = array.base
    return array


def _storage_key(storage, period, branch_name) -> str:
    """The key ``InMemoryStorage.get`` and ``put`` build for ``period``."""
    if storage.is_eternal:
        period = _periods.period(_periods.ETERNITY)
    return f"{branch_name}:{_periods.period(period)}"


def _storage_clone(self):
    shared_ids = _sharing.get()
    if shared_ids is None:
        return _core["InMemoryStorage.clone"](self)
    from policyengine_core.data_storage.in_memory_storage import InMemoryStorage

    clone = InMemoryStorage(self.is_eternal)
    shared = set()
    freeze = _settings["freeze_sources"]
    for key, array in self._arrays.items():
        if _can_share(array):
            if freeze:
                array.flags.writeable = False
            clone._arrays[key] = _read_only_view(array)
            shared.add(key)
            shared_ids.add(id(_base_array(array)))
        else:
            clone._arrays[key] = array.copy()
    if shared:
        clone._shared = shared
        # The source copies too, so its in-place writes stay its own.
        self.__dict__.setdefault("_shared", set()).update(shared)
        _marked.add(clone)
        _marked.add(self)
    return clone


def _storage_get(self, period, branch_name="default"):
    shared = self.__dict__.get("_shared")
    if not shared:
        return _core["InMemoryStorage.get"](self, period, branch_name)
    key = _storage_key(self, period, branch_name)
    values = self._arrays.get(key)
    if values is None:
        return None
    if key in shared:
        # First read of an array this storage shares: from here on the caller
        # may write into it, so it needs to be this storage's own.
        values = values.copy()
        self._arrays[key] = values
        shared.discard(key)
    return values


def _storage_put(self, value, period, branch_name="default"):
    _core["InMemoryStorage.put"](self, value, period, branch_name)
    shared = self.__dict__.get("_shared")
    if shared:
        shared.discard(_storage_key(self, period, branch_name))


def _storage_delete(self, period=None, branch_name="default"):
    _core["InMemoryStorage.delete"](self, period, branch_name)
    shared = self.__dict__.get("_shared")
    if shared:
        shared.intersection_update(self._arrays)


def _simulation_clone(self, *args, **kwargs):
    request = _branch_request.get()
    if request is None or not request.pending or request.simulation is not self:
        return _original["Simulation.clone"](self, *args, **kwargs)
    request.pending = False
    shared_ids = set()
    token = _sharing.set(shared_ids)
    try:
        clone = _original["Simulation.clone"](self, *args, **kwargs)
    finally:
        _sharing.reset(token)
    # The fast cache holds arrays over the same memory as the storage's: most
    # often the same objects, but for a formula that returns a 0-dim array,
    # the original, where the storage holds a reshaped view of it
    # (Holder._to_array). Drop every entry built on the base array of a shared
    # array, so the parent reads those through its storage, which copies them
    # first. Each id here belongs to the base of an array the storage still
    # holds, which keeps that base alive, so no other live object can carry it.
    fast_cache = self.__dict__.get("_fast_cache")
    if fast_cache and shared_ids:
        for key in [
            key
            for key, value in fast_cache.items()
            if isinstance(value, numpy.ndarray)
            and id(_base_array(value)) in shared_ids
        ]:
            del fast_cache[key]
    return clone


def _simulation_get_branch(self, *args, **kwargs):
    request = _BranchClone(self)
    token = _branch_request.set(request)
    try:
        return _original["Simulation.get_branch"](self, *args, **kwargs)
    finally:
        request.pending = False
        _branch_request.reset(token)


def _targets():
    from policyengine_core.data_storage.in_memory_storage import InMemoryStorage
    from policyengine_core.simulations.simulation import Simulation

    return (
        ("InMemoryStorage.clone", InMemoryStorage, "clone", _storage_clone),
        ("InMemoryStorage.get", InMemoryStorage, "get", _storage_get),
        ("InMemoryStorage.put", InMemoryStorage, "put", _storage_put),
        ("InMemoryStorage.delete", InMemoryStorage, "delete", _storage_delete),
        ("Simulation.clone", Simulation, "clone", _simulation_clone),
        ("Simulation.get_branch", Simulation, "get_branch", _simulation_get_branch),
    )


def installed() -> bool:
    return bool(_original)


def install(freeze_sources: bool = True) -> None:
    """Make ``get_branch`` share cached arrays (see the module docstring).

    Refuses any policyengine-core but 3.30.3: the replacements mirror that
    release's ``InMemoryStorage`` and ``Simulation`` code. Calling it again
    only updates ``freeze_sources``, which applies to branches made from then
    on.
    """
    global _periods
    version = importlib.metadata.version("policyengine-core")
    if version != CORE_VERSION:
        raise RuntimeError(
            f"analysis.branch_arrays ports {UPSTREAM} onto policyengine-core "
            f"{CORE_VERSION}, but policyengine-core {version} is installed"
        )
    _settings["freeze_sources"] = bool(freeze_sources)
    if _original:
        return
    from policyengine_core import periods

    _periods = periods
    for name, owner, attribute, replacement in _targets():
        _original[name] = owner.__dict__[attribute]
        _core.setdefault(name, _original[name])
        setattr(owner, attribute, replacement)


_STORAGE_METHODS = (
    ("get", _storage_get),
    ("put", _storage_put),
    ("delete", _storage_delete),
)


def _keep_copying() -> None:
    """Give each storage that still shares an array its own ``get``, ``put``
    and ``delete``, so it keeps copying on first read after ``uninstall``.

    A simulation made while the port ran can outlive it, and its branches
    still hold read-only views of their parents' arrays. Copying them all at
    ``uninstall`` would bring back the memory peak the port removes, so each
    storage goes on copying an array when it first reads it. Once a storage
    shares nothing, these methods do exactly what core's do.

    Each method is a ``functools.partial`` of a module-level function, so
    ``pickle`` and ``copy.deepcopy`` rebuild it around the copied storage. A
    bound method would pickle as a lookup of its function's name on the
    storage, and the storage has no attribute by that name.
    """
    for storage in list(_marked):
        if storage.__dict__.get("_shared"):
            for name, method in _STORAGE_METHODS:
                storage.__dict__[name] = functools.partial(method, storage)
    _marked.clear()


def uninstall() -> None:
    """Put back policyengine-core's own methods.

    Storages that still share arrays keep copying on first read (see
    ``_keep_copying``), so a simulation made before reads what it would
    have.
    """
    for name, owner, attribute, _ in _targets():
        if name in _original:
            setattr(owner, attribute, _original.pop(name))
    _keep_copying()
    _settings["freeze_sources"] = False


@contextlib.contextmanager
def shared_branch_arrays(freeze_sources: bool = True):
    """``install`` for the length of a ``with`` block, then restore.

    A simulation made inside the block can be used after it: its storages
    keep copying on first read (see ``uninstall``).
    """
    was_installed = installed()
    previous = _settings["freeze_sources"]
    install(freeze_sources)
    try:
        yield
    finally:
        if was_installed:
            _settings["freeze_sources"] = previous
        else:
            uninstall()


def metadata() -> dict:
    """What a run's output records about how its branches held arrays."""
    if not installed():
        return {"shared_until_first_read": False}
    return {
        "shared_until_first_read": True,
        "port_of": UPSTREAM,
        "parent_copies_on_first_read": True,
        "sources_frozen": _settings["freeze_sources"],
        "policyengine_core_version": CORE_VERSION,
    }
