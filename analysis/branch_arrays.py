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
peak footprint before and 8.7 GB after. Core releases after #556 also change
results (#560 makes ``set_input`` on a branch drop the values the branch
calculated from the input it replaces, and #562 carries over only inputs), so
the pinned runtime can't take a newer core. ``install`` ports #556 onto 3.30.3
and closes the one gap #556's docstrings state.

That gap: under #556, code that writes in place into one of a parent's cached
arrays after branching changes the value a branch reads, if the branch hasn't
read that array yet. policyengine-us 1.764.6 has such a write:
``ga_deductions`` runs ``itemized -= ...`` on the cached
``itemized_taxable_income_deductions`` (policyengine-us main now subtracts into
a new array). So here the parent copies too: making a branch marks each array
it shares in both simulations, and each copies a marked array the first time it
reads it, so neither ever reads the other's writes. Making a branch also drops
the parent's fast-cache entries (``Simulation._fast_cache``) for the arrays it
shares, so the parent's reads reach its storage, which copies.

A write can still reach a shared array through a reference taken before the
branch was made, such as an array a formula read and still holds while a
calculation it calls makes a branch. With ``freeze_sources`` (the sweep's
setting), making a branch marks every array it shares read-only, so such a
write raises ``ValueError`` instead of changing a result, unless it goes
through a separate view of the array made before the branch. With that
setting, a run that finishes reads the values copying every array up front
gives, byte for byte.

``Simulation.clone()`` called directly, as ``Simulation.derivative`` does, still
copies every array straight away. ``Holder.get_memory_usage`` counts an array a
branch still shares for both simulations, though memory holds it once.
"""

from __future__ import annotations

import contextlib
import importlib.metadata
from contextvars import ContextVar

import numpy

CORE_VERSION = "3.30.3"
UPSTREAM = "policyengine-core#556 (c991b38b2)"

# Set by ``get_branch`` around its ``clone`` call: the simulation it branches.
_branch_request: ContextVar[_BranchClone | None] = ContextVar(
    "ai_inequality_branch_request", default=None
)
# While that clone runs: the ids of the arrays it shares, so the clone can drop
# the parent's fast-cache entries for them. None the rest of the time.
_sharing: ContextVar[set | None] = ContextVar(
    "ai_inequality_branch_sharing", default=None
)

_original: dict[str, object] = {}
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


def _storage_key(storage, period, branch_name) -> str:
    """The key ``InMemoryStorage.get`` and ``put`` build for ``period``."""
    if storage.is_eternal:
        period = _periods.period(_periods.ETERNITY)
    return f"{branch_name}:{_periods.period(period)}"


def _storage_clone(self):
    shared_ids = _sharing.get()
    if shared_ids is None:
        return _original["InMemoryStorage.clone"](self)
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
            shared_ids.add(id(array))
        else:
            clone._arrays[key] = array.copy()
    if shared:
        clone._shared = shared
        # The source copies too, so its in-place writes stay its own.
        self.__dict__.setdefault("_shared", set()).update(shared)
    return clone


def _storage_get(self, period, branch_name="default"):
    shared = self.__dict__.get("_shared")
    if not shared:
        return _original["InMemoryStorage.get"](self, period, branch_name)
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
    _original["InMemoryStorage.put"](self, value, period, branch_name)
    shared = self.__dict__.get("_shared")
    if shared:
        shared.discard(_storage_key(self, period, branch_name))


def _storage_delete(self, period=None, branch_name="default"):
    _original["InMemoryStorage.delete"](self, period, branch_name)
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
    # The fast cache holds the same array objects as the storage. Drop the
    # entries for shared arrays, so the parent reads them through its storage,
    # which copies them first. Every id here belongs to an array the storage
    # still holds, so no other live object can carry it.
    fast_cache = self.__dict__.get("_fast_cache")
    if fast_cache and shared_ids:
        for key in [
            key for key, value in fast_cache.items() if id(value) in shared_ids
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
        setattr(owner, attribute, replacement)


def uninstall() -> None:
    """Put back policyengine-core's own methods."""
    for name, owner, attribute, _ in _targets():
        if name in _original:
            setattr(owner, attribute, _original.pop(name))
    _settings["freeze_sources"] = False


@contextlib.contextmanager
def shared_branch_arrays(freeze_sources: bool = True):
    """``install`` for the length of a ``with`` block, then restore."""
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
