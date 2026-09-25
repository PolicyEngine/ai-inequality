"""Property tests for resume-store fingerprints and legacy input renames.

These state the invariants the example tests in ``test_runtime_provenance``
illustrate, and check them over generated inputs:

- a checkpoint load returns, for each key, the last payload a matching
  runtime wrote, and nothing another runtime wrote; it warns exactly when it
  skipped something, and a torn final line never changes the result;
- the legacy WIC rename sets the live input, for every month of every dataset
  year, to the stored draw, and sets nothing when it does not apply;
- the runtime fingerprint is deterministic, and its digest changes whenever any
  component changes.
"""

import json
import warnings
from unittest import mock

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from analysis import policyengine_runtime as runtime
from analysis.compute_ai_scenarios import append_checkpoint, load_checkpoint
from analysis.tests.test_runtime_provenance import _FakeSim, _variables

FINGERPRINTS = st.sampled_from([None, "aaaa", "bbbb"])
RECORDS = st.lists(
    st.tuples(
        st.sampled_from(["baseline", "grid:1", "grid:2"]), st.integers(), FINGERPRINTS
    ),
    max_size=12,
)


def _write(path, records):
    for key, payload, fingerprint in records:
        append_checkpoint(str(path), key, {"value": payload}, fingerprint)


def _expected(records, fingerprint):
    expected = {}
    for key, payload, written in records:
        if fingerprint is None or written == fingerprint:
            expected[key] = {"value": payload}
    return expected


@settings(max_examples=150, deadline=None)
@given(records=RECORDS, fingerprint=st.sampled_from([None, "aaaa"]))
def test_checkpoint_returns_the_last_matching_payload_per_key(
    tmp_path_factory, records, fingerprint
):
    path = tmp_path_factory.mktemp("ckpt") / "checkpoint.jsonl"
    _write(path, records)
    skips = fingerprint is not None and any(
        written != fingerprint for _, _, written in records
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        loaded = load_checkpoint(str(path), fingerprint)
    assert loaded == _expected(records, fingerprint)
    # It warns exactly when it skipped a unit another runtime wrote.
    assert any("another runtime" in str(w.message) for w in caught) == skips


@settings(max_examples=100, deadline=None)
@given(
    records=RECORDS, fingerprint=st.sampled_from([None, "aaaa"]), cut=st.integers(1, 40)
)
def test_a_torn_final_line_never_changes_the_result(
    tmp_path_factory, records, fingerprint, cut
):
    path = tmp_path_factory.mktemp("ckpt") / "checkpoint.jsonl"
    _write(path, records)
    torn = json.dumps({"key": "grid:9", "payload": {"value": 1}, "fingerprint": "aaaa"})
    with open(path, "a") as handle:
        handle.write(torn[: min(cut, len(torn) - 1)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert load_checkpoint(str(path), fingerprint) == _expected(
            records, fingerprint
        )


YEARS = st.lists(
    st.sampled_from([2024, 2025, 2026, 2030]), min_size=1, max_size=3, unique=True
)


@settings(max_examples=100, deadline=None)
@given(years=YEARS, n=st.integers(1, 25), data=st.data())
def test_rename_sets_every_month_of_every_year_to_the_stored_draw(years, n, data):
    person_by_year = {
        year: pd.DataFrame(
            {
                "person_id": list(range(100, 100 + n)),
                "would_claim_wic": data.draw(
                    st.lists(st.booleans(), min_size=n, max_size=n)
                ),
            }
        )
        for year in years
    }
    sim = _FakeSim(_variables("takes_up_wic_if_eligible", "person_id"), person_by_year)

    applied = runtime.apply_legacy_input_renames(sim)

    assert applied == {"would_claim_wic": "takes_up_wic_if_eligible"}
    assert len(sim.inputs) == 12 * len(years)
    for year, person in person_by_year.items():
        for month in range(1, 13):
            values = sim.inputs[("takes_up_wic_if_eligible", f"{year}-{month:02d}")]
            assert values.tolist() == person["would_claim_wic"].tolist()


@settings(max_examples=100, deadline=None)
@given(
    years=YEARS,
    case=st.sampled_from(["engine_knows_legacy", "engine_lacks_live", "data_has_live"]),
    n=st.integers(1, 10),
)
def test_rename_sets_nothing_when_it_does_not_apply(years, case, n):
    person_by_year = {}
    for year in years:
        person = pd.DataFrame(
            {"person_id": list(range(n)), "would_claim_wic": [True] * n}
        )
        if case == "data_has_live":
            person["takes_up_wic_if_eligible"] = [False] * n
        person_by_year[year] = person
    names = {
        "engine_knows_legacy": ("would_claim_wic", "takes_up_wic_if_eligible"),
        "engine_lacks_live": ("person_id",),
        "data_has_live": ("takes_up_wic_if_eligible", "person_id"),
    }[case]
    sim = _FakeSim(_variables(*names), person_by_year)

    assert runtime.apply_legacy_input_renames(sim) == {}
    assert sim.inputs == {}


COMPONENT = st.one_of(
    st.tuples(st.just("revision"), st.integers(0, 50)),
    st.tuples(
        st.just("renames"),
        st.dictionaries(
            st.sampled_from(["would_claim_wic", "old_a", "old_b"]),
            st.sampled_from(["takes_up_wic_if_eligible", "new_a", "new_b"]),
            max_size=3,
        ),
    ),
    st.tuples(
        st.just("us_version"), st.sampled_from(["1.764.6", "2.2.1", "2.13.0", None])
    ),
)


def _installed_us_version():
    try:
        return runtime.importlib.metadata.version("policyengine-us")
    except runtime.importlib.metadata.PackageNotFoundError:
        return None


def _intended_state(component):
    """The runtime a component describes: the defaults with one field changed."""
    state = {
        "revision": runtime.RUNTIME_REVISION,
        "renames": dict(sorted(runtime.LEGACY_INPUT_RENAMES.items())),
        "us_version": _installed_us_version(),
    }
    kind, value = component
    state[kind] = dict(sorted(value.items())) if kind == "renames" else value
    return state


def _fingerprint_with(component):
    kind, value = component
    if kind == "revision":
        patch = mock.patch.object(runtime, "RUNTIME_REVISION", value)
    elif kind == "renames":
        patch = mock.patch.object(runtime, "LEGACY_INPUT_RENAMES", value)
    else:
        real = runtime.importlib.metadata.version

        def version(package):
            if package == "policyengine-us":
                if value is None:
                    raise runtime.importlib.metadata.PackageNotFoundError(package)
                return value
            return real(package)

        patch = mock.patch.object(runtime.importlib.metadata, "version", version)
    with patch:
        return runtime.runtime_fingerprint()


@settings(max_examples=150, deadline=None)
@given(first=COMPONENT, second=COMPONENT)
def test_fingerprint_digest_tracks_every_component(first, second):
    a, b = _fingerprint_with(first), _fingerprint_with(second)
    state_a, state_b = _intended_state(first), _intended_state(second)
    # Deterministic: the same runtime always yields the same digest.
    assert _fingerprint_with(first) == a
    # Each recorded component is the runtime's own value.
    for fingerprint, state in ((a, state_a), (b, state_b)):
        assert fingerprint["runtime_revision"] == state["revision"]
        assert fingerprint["legacy_input_renames"] == state["renames"]
        assert fingerprint["packages"]["policyengine-us"] == state["us_version"]
    # The digest changes exactly when the runtime changes.
    assert (a["digest"] == b["digest"]) == (state_a == state_b)
