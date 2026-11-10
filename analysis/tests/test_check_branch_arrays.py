"""analysis.check_branch_arrays: a digest changes with any change in an array's
type, dtype, shape or bytes; ``canonical`` keeps every bit of every number and
survives a JSON round trip; a subset keeps everyone in each drawn household;
and ``compare`` reports every way two runs differ, including a run that tests
nothing.

These need numpy, pandas and Hypothesis, which CI installs. The HDF round trip
also needs PyTables, which CI doesn't install, so it skips there.
"""

import copy
import gzip
import json

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from analysis import check_branch_arrays as check

DTYPES = st.sampled_from([np.bool_, np.int32, np.int64, np.float32, np.float64])
ARRAYS = DTYPES.flatmap(
    lambda dtype: hnp.arrays(dtype, hnp.array_shapes(max_dims=2, max_side=8))
)


class Labelled(np.ndarray):
    """An ndarray subclass, as policyengine-core's EnumArray is one."""


@given(ARRAYS)
def test_a_digest_depends_only_on_type_dtype_shape_and_values(array):
    assert check.array_digest(array) == check.array_digest(array.copy())
    view = array[::-1]
    assert check.array_digest(view) == check.array_digest(np.ascontiguousarray(view))


@given(ARRAYS.filter(lambda array: array.size > 0), st.data())
def test_changing_any_byte_changes_the_digest(array, data):
    changed = array.copy()
    raw = changed.reshape(-1).view(np.uint8)
    raw[data.draw(st.integers(0, raw.size - 1))] ^= 1
    assert check.array_digest(changed) != check.array_digest(array)


def test_a_digest_tells_apart_arrays_with_the_same_bytes():
    same_bytes = [
        np.zeros(4, np.int32),
        np.zeros(4, np.float32),
        np.zeros((2, 2), np.int32),
        np.zeros(4, np.int32).view(Labelled),
    ]
    assert len({check.array_digest(array) for array in same_bytes}) == len(same_bytes)


def test_an_object_array_s_digest_follows_its_objects():
    def values(*numbers):
        # float() makes new objects on each call, so two such arrays hold
        # different pointers.
        return np.array([float(number) for number in numbers], dtype=object)

    assert check.array_digest(values("1.5", "2")) == check.array_digest(values("1.5", "2"))
    assert check.array_digest(values("1.5", "2")) != check.array_digest(values("1.5", "3"))


def test_canonical_keeps_every_bit_of_every_number():
    assert check.canonical(0.1 + 0.2) != check.canonical(0.3)
    assert check.canonical(-0.0) != check.canonical(0.0)
    assert check.canonical(np.float32(0.1)) == float(np.float32(0.1)).hex()
    assert check.canonical(True) != check.canonical(1)
    assert check.canonical(1) != check.canonical(1.0)
    assert check.canonical(None) != check.canonical("None")
    assert check.canonical({"b": 1, "a": [2.0, 3]}) == check.canonical(
        {"a": [2.0, 3], "b": 1}
    )


def test_canonical_tells_frames_apart_by_column_order_and_values():
    frame = pd.DataFrame({"a": [1.0, 2.0], "b": [3, 4]})
    assert check.canonical(frame) == check.canonical(frame.copy())
    assert check.canonical(frame) != check.canonical(frame[["b", "a"]])
    changed = frame.copy()
    changed.loc[1, "a"] = np.nextafter(2.0, 3.0)
    assert check.canonical(changed) != check.canonical(frame)


JSON_LIKE = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=True)
    | st.text(max_size=5),
    lambda children: st.lists(children, max_size=4)
    | st.dictionaries(st.text(max_size=5), children, max_size=4),
    max_leaves=20,
)


@given(JSON_LIKE)
def test_canonical_survives_a_json_round_trip(value):
    # The check writes each run's digests to JSON and compares what it reads back.
    form = check.canonical(value)
    assert json.loads(json.dumps(form)) == form
    assert check.canonical(copy.deepcopy(value)) == form


@st.composite
def microdata(draw):
    """Tables shaped like the pinned microdata's: households of one to four
    people, grouped at random within each household into tax units, SPM units,
    families and marital units, plus one group of each kind with no members."""
    sizes = draw(st.lists(st.integers(1, 4), min_size=1, max_size=15))
    household_ids = draw(st.permutations(range(10, 10 + len(sizes))))
    rows = {"person": [], **{entity: [] for entity in check.GROUP_ENTITIES}}
    next_id = {entity: 100 for entity in check.GROUP_ENTITIES}
    for household_id, size in zip(household_ids, sizes):
        members = {}
        for entity in check.GROUP_ENTITIES:
            labels = draw(st.lists(st.integers(0, size - 1), min_size=size, max_size=size))
            members[entity] = [next_id[entity] + label for label in labels]
            rows[entity] += [{f"{entity}_id": group} for group in sorted(set(members[entity]))]
            next_id[entity] += size
        for index in range(size):
            rows["person"].append(
                {
                    "person_id": len(rows["person"]),
                    "person_household_id": household_id,
                    **{
                        f"person_{entity}_id": members[entity][index]
                        for entity in check.GROUP_ENTITIES
                    },
                }
            )
    tables = {key: pd.DataFrame(value) for key, value in rows.items()}
    for entity in check.GROUP_ENTITIES:
        orphan = pd.DataFrame({f"{entity}_id": [next_id[entity] + 7]})
        tables[entity] = pd.concat([tables[entity], orphan], ignore_index=True)
    tables["household"] = pd.DataFrame(
        {
            "household_id": list(household_ids),
            "household_weight": np.arange(len(sizes), dtype=float),
        }
    )
    tables["_time_period"] = pd.DataFrame({"values": [2024]})
    return tables


@settings(max_examples=100, deadline=None)
@given(microdata(), st.data())
def test_a_subset_keeps_everyone_in_each_drawn_household(tables, data):
    households = data.draw(st.integers(1, len(tables["household"])))
    seed = data.draw(st.integers(0, 2**32 - 1))
    subset = check.subset_tables(tables, households, seed)

    drawn = set(subset["household"]["household_id"])
    assert len(drawn) == households == len(subset["household"])
    assert drawn <= set(tables["household"]["household_id"])
    person = tables["person"]
    assert set(subset["person"]["person_id"]) == set(
        person[person["person_household_id"].isin(drawn)]["person_id"]
    )
    for entity in check.GROUP_ENTITIES:
        kept = subset[entity][f"{entity}_id"]
        assert set(kept) == set(subset["person"][f"person_{entity}_id"])
        assert kept.is_unique
    pd.testing.assert_frame_equal(subset["_time_period"], tables["_time_period"])
    for frame in subset.values():
        assert frame.index.equals(pd.RangeIndex(len(frame)))
    again = check.subset_tables(tables, households, seed)
    for key, frame in subset.items():
        pd.testing.assert_frame_equal(again[key], frame)


def _small_microdata():
    return {
        "_time_period": pd.DataFrame({"values": [2024]}),
        "household": pd.DataFrame({"household_id": [1, 2, 3], "household_weight": [1.0, 2.0, 3.0]}),
        "person": pd.DataFrame(
            {
                "person_id": [0, 1, 2, 3],
                "person_household_id": [1, 1, 2, 3],
                **{
                    f"person_{entity}_id": [5, 5, 6, 7]
                    for entity in check.GROUP_ENTITIES
                },
            }
        ),
        **{
            entity: pd.DataFrame({f"{entity}_id": [5, 6, 7]})
            for entity in check.GROUP_ENTITIES
        },
    }


def test_a_subset_refuses_tables_it_does_not_know():
    tables = _small_microdata()
    with pytest.raises(ValueError, match=r"unknown: \['extra'\]"):
        check.subset_tables({**tables, "extra": pd.DataFrame()}, 1)
    del tables["family"]
    with pytest.raises(ValueError, match=r"missing: \['family'\]"):
        check.subset_tables(tables, 1)


def test_write_subset_round_trips_through_hdf(tmp_path):
    pytest.importorskip("tables")
    tables = _small_microdata()
    source = tmp_path / "source.h5"
    with pd.HDFStore(source, "w") as store:
        for key, frame in tables.items():
            store.put(key, frame, format="table")
    counts = check.write_subset(source, 2, tmp_path / "subset.h5", seed=1)
    with pd.HDFStore(tmp_path / "subset.h5", "r") as store:
        written = {key.strip("/"): store[key] for key in store.keys()}
    expected = check.subset_tables(tables, 2, seed=1)
    assert written.keys() == expected.keys()
    for key, frame in expected.items():
        pd.testing.assert_frame_equal(written[key], frame)
    assert counts == {
        key: len(frame) for key, frame in expected.items() if key != "_time_period"
    }


def _write_microdata(folder, rows, mtime, created_at):
    folder.mkdir()
    with gzip.GzipFile(filename=str(folder / "baseline.csv.gz"), mode="wb", mtime=mtime) as f:
        f.write(rows)
    (folder / "manifest.json").write_text(json.dumps({"created_at": created_at, "year": 2026}))


def test_microdata_digests_skip_gzip_times_and_the_manifest_s_timestamp(tmp_path):
    rows = b"household_weight,household_net_income\n1.5,100\n"
    _write_microdata(tmp_path / "a", rows, 1, "2026-11-10T00:00:00+00:00")
    _write_microdata(tmp_path / "b", rows, 2, "2026-11-11T00:00:00+00:00")
    assert (tmp_path / "a" / "baseline.csv.gz").read_bytes() != (
        tmp_path / "b" / "baseline.csv.gz"
    ).read_bytes()
    assert check.microdata_digests(tmp_path / "a") == check.microdata_digests(tmp_path / "b")
    _write_microdata(tmp_path / "c", rows.replace(b"100", b"101"), 1, "2026-11-10T00:00:00+00:00")
    assert check.microdata_digests(tmp_path / "c") != check.microdata_digests(tmp_path / "a")


def _run_record(mode):
    """A small stand-in for what ``run_sweep`` writes for each mode."""
    sharing = {"shared_until_first_read": mode == "shared"}
    if mode == "shared":
        sharing["sources_frozen"] = True
    return {
        "mode": mode,
        "subset": "subset_6000_20261110.h5",
        "branch_arrays": sharing,
        "simulations": [
            {
                "households": 3,
                "arrays": {
                    "root|income_tax|default:2026": "aa",
                    "root/itemizing|income_tax|default:2026": "bb",
                },
                "still_shared": 5 if mode == "shared" else 0,
            },
            {
                "households": 3,
                "arrays": {"root|employment_income|default:2026": "cc"},
                "still_shared": 0,
            },
        ],
        "result": {
            "scenarios": [
                {"shift_pct": "0", "total_rev_change_b": "0x0.0p+0"},
                {"shift_pct": "10", "total_rev_change_b": "-0x1.0p+0"},
            ]
        },
        "microdata": {"baseline.csv.gz": "dd", "manifest.json": {"year": "2026"}},
        "deciles": {"10": ["0x1.0p-3"]},
        "seconds": 1,
        "peak_footprint_mb": None,
    }


def test_compare_finds_nothing_between_matching_runs():
    assert check.compare(_run_record("copies"), _run_record("shared")) == []


SHARED_RUN_CHANGES = {
    "an array's values": (
        lambda run: run["simulations"][0]["arrays"].update(
            {"root|income_tax|default:2026": "zz"}
        ),
        "baseline: root|income_tax|default:2026 holds different values",
    ),
    "an extra array": (
        lambda run: run["simulations"][1]["arrays"].update({"root|x|default:2026": "ee"}),
        "10% shift: only the sharing run stores root|x|default:2026",
    ),
    "a missing array": (
        lambda run: run["simulations"][0]["arrays"].pop(
            "root/itemizing|income_tax|default:2026"
        ),
        "baseline: only the copying run stores root/itemizing|income_tax|default:2026",
    ),
    "a result": (
        lambda run: run["result"]["scenarios"][1].update(
            {"total_rev_change_b": "-0x1.0000000000001p+0"}
        ),
        "the sweep's result differs at result.scenarios[1].total_rev_change_b",
    ),
    "a microdata file": (
        lambda run: run["microdata"].update({"shift_10.csv.gz": "ff"}),
        "the household microdata differ at microdata.shift_10.csv.gz",
    ),
    "the deciles": (
        lambda run: run["deciles"]["10"].append("0x0.0p+0"),
        "the decile impacts differ at deciles.10",
    ),
    "the households": (
        lambda run: run["simulations"][1].update({"households": 4}),
        "10% shift: 3 and 4 households",
    ),
    "a simulation": (
        lambda run: run["simulations"].pop(),
        "the copying run built 2 simulations and the sharing run 1",
    ),
    "the subset": (
        lambda run: run.update({"subset": "other.h5"}),
        "the runs read different subsets: subset_6000_20261110.h5 and other.h5",
    ),
    "the sharing setting": (
        lambda run: run["branch_arrays"].update({"sources_frozen": False}),
        "the sharing run didn't share arrays with frozen sources",
    ),
    "the arrays left shared": (
        lambda run: run["simulations"][0].update({"still_shared": 0}),
        "no array in the sharing run stayed shared to the end, so it may have shared none",
    ),
}


@pytest.mark.parametrize("name", sorted(SHARED_RUN_CHANGES))
def test_compare_reports_each_way_the_sharing_run_can_differ(name):
    change, expected = SHARED_RUN_CHANGES[name]
    shared = _run_record("shared")
    change(shared)
    assert expected in check.compare(_run_record("copies"), shared)


@pytest.mark.parametrize(
    "change",
    [
        lambda run: run["branch_arrays"].update({"shared_until_first_read": True}),
        lambda run: run["simulations"][1].update({"still_shared": 1}),
    ],
)
def test_compare_reports_a_copying_run_that_shared_arrays(change):
    copies = _run_record("copies")
    change(copies)
    assert "the copying run shared arrays" in check.compare(copies, _run_record("shared"))


def test_summary_counts_arrays_simulations_and_what_stayed_shared():
    lines = check.summary(_run_record("copies"), _run_record("shared"))
    assert lines[0] == (
        "baseline: 3 households; 2 arrays in 2 simulations (root, root/itemizing); "
        "5 still shared at the end of the sharing run"
    )
    assert lines[2:] == ["copying run: 1 s", "sharing run: 1 s"]
