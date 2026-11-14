"""Check that ``analysis.branch_arrays`` changes nothing the sweep computes.

From the repository root, on the pinned runtime:

    python -m analysis.check_branch_arrays [--households N] [--seed S] [--out DIR]

The check draws N households (6,000 by default) at random from the microdata
the pinned bundle certifies, keeps every person, tax unit, SPM unit, family
and marital unit in them, and writes them to DIR in the microdata's own table
format. It then runs ``run_shift_sweep`` at shifts of 0 and 10% on that subset
twice, each time in a new process: once with ``share_branch_arrays=False``,
where policyengine-core 3.30.3's branches copy every cached array up front,
and once with the sweep's own setting, where branches share them
(``analysis.branch_arrays`` with ``freeze_sources``). Each run digests every
array that every holder stores, in each simulation the sweep builds and in
every branch under it, along with the sweep's result, the household microdata
it writes and the decile impacts computed from them. The check compares the
two runs digest by digest. It exits 1 on any difference, and also when either
run fails, when the copying run shares arrays, or when no array in the sharing
run stays shared to the end, since then the comparison tests nothing.

A subset keeps the copying run small enough to fit in memory, so the check
covers the formula paths those households reach.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import gc
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_HOUSEHOLDS = 6000
DEFAULT_SEED = 20261110
SHIFT_LEVELS = (0.0, 0.1)
LABELS = ("baseline", "10% shift")
GROUP_ENTITIES = ("tax_unit", "spm_unit", "family", "marital_unit")
TABLES = ("_time_period", "household", "person", *GROUP_ENTITIES)
MODES = ("copies", "shared")
RUN_NAMES = {"copies": "copying", "shared": "sharing"}


def array_digest(array) -> str:
    """A digest of an array's type, dtype, shape and values.

    An object array's bytes are pointers, so its digest covers the objects'
    reprs instead.
    """
    import numpy as np

    values = np.asarray(array)
    digest = hashlib.sha256(
        f"{type(array).__name__}|{values.dtype.str}|{values.shape}|".encode()
    )
    if values.dtype.hasobject:
        digest.update(repr(values.tolist()).encode())
    else:
        digest.update(np.ascontiguousarray(values).tobytes())
    return digest.hexdigest()


def canonical(obj):
    """A JSON form of a result that keeps every bit of every number.

    Floats become their hex form, so ``-0.0`` and ``0.0`` stay apart, and
    arrays, series and frames become digests.
    """
    import numpy as np
    import pandas as pd

    if isinstance(obj, pd.DataFrame):
        return {
            "columns": [str(column) for column in obj.columns],
            "index": array_digest(obj.index.to_numpy()),
            "values": [
                array_digest(obj.iloc[:, i].to_numpy()) for i in range(obj.shape[1])
            ],
        }
    if isinstance(obj, pd.Series):
        return {
            "index": array_digest(obj.index.to_numpy()),
            "values": array_digest(obj.to_numpy()),
        }
    if isinstance(obj, np.ndarray):
        return array_digest(obj)
    if isinstance(obj, dict):
        return {
            str(key): canonical(value)
            for key, value in sorted(obj.items(), key=lambda item: str(item[0]))
        }
    if isinstance(obj, (list, tuple)):
        return [canonical(value) for value in obj]
    if isinstance(obj, (bool, np.bool_)):
        return repr(bool(obj))
    if isinstance(obj, (float, np.floating)):
        return float(obj).hex()
    if isinstance(obj, (int, np.integer)):
        return repr(int(obj))
    return repr(obj)


def every_array(simulation, path="root") -> dict[str, str]:
    """The digest of every array that each simulation in the tree stores."""
    held = {}
    for population in simulation.populations.values():
        for name, holder in population._holders.items():
            for key, array in holder._memory_storage._arrays.items():
                held[f"{path}|{name}|{key}"] = array_digest(array)
    for name, branch in simulation.branches.items():
        held.update(every_array(branch, f"{path}/{name}"))
    return held


def still_shared(simulation) -> int:
    """How many arrays the tree's storages still share and haven't read."""
    count = sum(
        len(holder._memory_storage.__dict__.get("_shared", ()))
        for population in simulation.populations.values()
        for holder in population._holders.values()
    )
    return count + sum(still_shared(branch) for branch in simulation.branches.values())


class _RUsageInfoV4(ctypes.Structure):
    _fields_ = [("ri_uuid", ctypes.c_uint8 * 16)] + [
        (f"field_{index}", ctypes.c_uint64) for index in range(40)
    ]


def peak_footprint_mb() -> float | None:
    """This process's lifetime peak footprint on macOS (rusage v4), in MB."""
    if sys.platform != "darwin":
        return None
    info = _RUsageInfoV4()
    library = ctypes.CDLL(ctypes.util.find_library("System"))
    if library.proc_pid_rusage(os.getpid(), 4, ctypes.byref(info)) != 0:
        return None
    return info.field_28 / 2**20  # ri_lifetime_max_phys_footprint


def file_digest(path) -> str:
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def pinned_microdata() -> tuple[str, str]:
    """The URI and local file of the US microdata the pinned bundle certifies.

    It resolves both as ``managed_microsimulation`` does when given no dataset.
    """
    from policyengine.provenance.dataset_sources import materialize_dataset_source
    from policyengine.provenance.manifest import (
        resolve_local_managed_dataset_source,
        resolve_managed_dataset_reference,
    )

    uri = resolve_managed_dataset_reference("us")
    local = materialize_dataset_source(resolve_local_managed_dataset_source("us", uri))
    return uri, local


def subset_tables(tables, households, seed=DEFAULT_SEED):
    """Draw ``households`` households from ``tables``, with everyone in them.

    ``tables`` maps each of the microdata's tables to its frame. The draw keeps
    every person in a drawn household and every group any of them belongs to,
    and gives each frame a fresh index.
    """
    import numpy as np

    unknown, missing = set(tables) - set(TABLES), set(TABLES) - set(tables)
    if unknown or missing:
        raise ValueError(
            f"the microdata should hold the tables {', '.join(TABLES)}; "
            f"unknown: {sorted(unknown)}, missing: {sorted(missing)}"
        )
    household = tables["household"]
    chosen = np.random.default_rng(seed).choice(
        household["household_id"].to_numpy(), size=households, replace=False
    )
    person = tables["person"][tables["person"]["person_household_id"].isin(chosen)]
    out = {
        "_time_period": tables["_time_period"],
        "household": household[household["household_id"].isin(chosen)],
        "person": person,
    }
    for entity in GROUP_ENTITIES:
        table = tables[entity]
        out[entity] = table[
            table[f"{entity}_id"].isin(person[f"person_{entity}_id"].unique())
        ]
    return {key: frame.reset_index(drop=True) for key, frame in out.items()}


def write_subset(source, households, out_path, seed=DEFAULT_SEED) -> dict[str, int]:
    """Write ``subset_tables``' draw from the file ``source`` to ``out_path``."""
    import pandas as pd

    with pd.HDFStore(source, "r") as store:
        tables = {key.strip("/"): store[key] for key in store.keys()}
    subset = subset_tables(tables, households, seed)
    with pd.HDFStore(out_path, "w") as store:
        for key, frame in subset.items():
            store.put(key, frame, format="table")
    return {key: len(frame) for key, frame in subset.items() if key != "_time_period"}


def microdata_digests(folder) -> dict[str, object]:
    """Digests of what ``microdata_export`` wrote to ``folder``.

    Each gzip file's digest covers its decompressed bytes, since gzip headers
    carry a time, and the manifest's leaves out ``created_at``.
    """
    digests = {}
    for path in sorted(Path(folder).iterdir()):
        if path.name == "manifest.json":
            manifest = json.loads(path.read_text())
            manifest.pop("created_at", None)
            digests[path.name] = canonical(manifest)
        elif path.suffix == ".gz":
            digests[path.name] = hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()
        else:
            digests[path.name] = file_digest(path)
    return digests


def run_sweep(mode, subset_path, out_dir) -> dict:
    """Run ``run_shift_sweep`` on the subset in ``mode`` and digest what it computes."""
    from .compute_decile_impacts import decile_impacts
    from .compute_shift_sweep import run_shift_sweep
    from .policyengine_runtime import managed_us_microsimulation

    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    microdata_dir = Path(out_dir) / f"{mode}_microdata"
    if microdata_dir.exists():
        raise FileExistsError(f"{microdata_dir} exists; pass a new --out")
    simulations, held = [], []

    def digest_held():
        # The sweep has finished with a simulation by the time it asks for the
        # next one, so the check digests it then, and memory holds one tree
        # at a time.
        while held:
            simulation = held.pop()
            simulations.append(
                {
                    "households": int(simulation.populations["household"].count),
                    "arrays": every_array(simulation),
                    "still_shared": still_shared(simulation),
                }
            )
            del simulation
            gc.collect()

    def factory():
        digest_held()
        simulation = managed_us_microsimulation(
            dataset=str(subset_path), allow_unmanaged=True
        )
        held.append(simulation)
        return simulation

    start = time.time()
    result = run_shift_sweep(
        shift_levels=list(SHIFT_LEVELS),
        microsim_factory=factory,
        microdata_output_dir=str(microdata_dir),
        share_branch_arrays=mode == "shared",
    )
    digest_held()
    # The one field that records which way the run held arrays.
    sharing = result["metadata"].pop("branch_arrays")
    return {
        "mode": mode,
        "subset": str(subset_path),
        "branch_arrays": sharing,
        "simulations": simulations,
        "result": canonical(result),
        "microdata": microdata_digests(microdata_dir),
        "deciles": canonical(decile_impacts(str(microdata_dir))),
        "seconds": round(time.time() - start),
        "peak_footprint_mb": peak_footprint_mb(),
    }


def _leaf_differences(a, b, path):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(a.keys() | b.keys()):
            yield from _leaf_differences(a.get(key), b.get(key), f"{path}.{key}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for index, (x, y) in enumerate(zip(a, b)):
            yield from _leaf_differences(x, y, f"{path}[{index}]")
    elif a != b:
        yield path


def compare(copies, shared) -> list[str]:
    """Every way the sharing run differs from the copying run.

    Also reports a copying run that shared arrays, a sharing run that didn't
    share them with frozen sources, and a sharing run in which no array stayed
    shared to the end.
    """
    differences = []
    if copies["branch_arrays"].get("shared_until_first_read") or any(
        simulation["still_shared"] for simulation in copies["simulations"]
    ):
        differences.append("the copying run shared arrays")
    settings = shared["branch_arrays"]
    if not (settings.get("shared_until_first_read") and settings.get("sources_frozen")):
        differences.append("the sharing run didn't share arrays with frozen sources")
    elif not any(simulation["still_shared"] for simulation in shared["simulations"]):
        differences.append(
            "no array in the sharing run stayed shared to the end, so it may have shared none"
        )
    if copies["subset"] != shared["subset"]:
        differences.append(f"the runs read different subsets: {copies['subset']} and {shared['subset']}")
    if len(copies["simulations"]) != len(shared["simulations"]):
        differences.append(
            f"the copying run built {len(copies['simulations'])} simulations "
            f"and the sharing run {len(shared['simulations'])}"
        )
    for index, (a, b) in enumerate(zip(copies["simulations"], shared["simulations"])):
        label = LABELS[index] if index < len(LABELS) else f"simulation {index + 1}"
        if a["households"] != b["households"]:
            differences.append(f"{label}: {a['households']:,} and {b['households']:,} households")
        for key in sorted(a["arrays"].keys() ^ b["arrays"].keys()):
            run = "copying" if key in a["arrays"] else "sharing"
            differences.append(f"{label}: only the {run} run stores {key}")
        differences += [
            f"{label}: {key} holds different values"
            for key in sorted(a["arrays"].keys() & b["arrays"].keys())
            if a["arrays"][key] != b["arrays"][key]
        ]
    differences += [
        f"the sweep's result differs at {path}"
        for path in _leaf_differences(copies["result"], shared["result"], "result")
    ]
    differences += [
        f"the household microdata differ at {path}"
        for path in _leaf_differences(copies["microdata"], shared["microdata"], "microdata")
    ]
    differences += [
        f"the decile impacts differ at {path}"
        for path in _leaf_differences(copies["deciles"], shared["deciles"], "deciles")
    ]
    return differences


def summary(copies, shared) -> list[str]:
    lines = []
    for index, (a, b) in enumerate(zip(copies["simulations"], shared["simulations"])):
        label = LABELS[index] if index < len(LABELS) else f"simulation {index + 1}"
        trees = sorted({key.split("|")[0] for key in a["arrays"]})
        lines.append(
            f"{label}: {a['households']:,} households; {len(a['arrays']):,} arrays in "
            f"{len(trees)} simulations ({', '.join(trees)}); "
            f"{b['still_shared']:,} still shared at the end of the sharing run"
        )
    for run in (copies, shared):
        peak = run["peak_footprint_mb"]
        lines.append(
            f"{RUN_NAMES[run['mode']]} run: {run['seconds']} s"
            + (f", peak footprint {peak:,.0f} MB" if peak is not None else "")
        )
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that analysis.branch_arrays changes nothing the sweep computes."
    )
    parser.add_argument("--households", type=int, default=DEFAULT_HOUSEHOLDS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", help="folder for the subset and the digests (default: a new one)")
    parser.add_argument("--source", help="microdata file to draw from (default: the pinned one)")
    parser.add_argument(
        "--run", nargs=3, metavar=("MODE", "SUBSET", "OUT"), help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)
    if args.run:
        mode, subset_path, out_dir = args.run
        record = run_sweep(mode, subset_path, out_dir)
        (Path(out_dir) / f"{mode}.json").write_text(json.dumps(record))
        return 0

    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="check_branch_arrays-"))
    out.mkdir(parents=True, exist_ok=True)
    uri, source = (None, args.source) if args.source else pinned_microdata()
    subset_path = out / f"subset_{args.households}_{args.seed}.h5"
    counts = write_subset(source, args.households, subset_path, args.seed)
    print(f"microdata: {uri or source}, sha256 {file_digest(source)[:16]}", flush=True)
    print(
        f"subset (seed {args.seed}) in {subset_path}: "
        + ", ".join(f"{count:,} {key}" for key, count in counts.items()),
        flush=True,
    )
    runs = {}
    for mode in MODES:
        completed = subprocess.run(
            [sys.executable, "-m", "analysis.check_branch_arrays", "--run", mode, str(subset_path), str(out)]
        )
        if completed.returncode != 0:
            print(f"branch_arrays check: the {RUN_NAMES[mode]} run exited {completed.returncode}")
            return 1
        runs[mode] = json.loads((out / f"{mode}.json").read_text())
        print(f"{RUN_NAMES[mode]} run done in {runs[mode]['seconds']} s", flush=True)
    for line in summary(runs["copies"], runs["shared"]):
        print(line)
    differences = compare(runs["copies"], runs["shared"])
    for line in differences[:50]:
        print(f"  {line}")
    if len(differences) > 50:
        print(f"  ... and {len(differences) - 50:,} more")
    print(
        "branch_arrays check: "
        + (
            "every array, the sweep's result, its microdata and its decile impacts match"
            if not differences
            else f"{len(differences):,} differences"
        )
    )
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
