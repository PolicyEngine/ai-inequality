"""State outputs come out in the same order whatever order the inputs arrive in.

Per-state deltas used to be keyed in set-iteration order, which changes with
Python's hash seed, and the state-exposure ranking broke ties by that order,
so every rerun reshuffled the states without a modelled base.
"""

import importlib
import json
import random
import sys
import types

import pytest

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
except ImportError:  # pragma: no cover - hypothesis is a test-only extra
    given = None

from analysis import compute_state_exposure as exposure
from analysis.compute_ai_scenarios import _state_delta_rows as scenario_rows


def _import_sweep_rows():
    """Import the sweep's ``_state_delta_rows`` with or without the engine.

    ``compute_shift_sweep`` imports policyengine-us and policyengine-core at
    module level (through ``labor_capital_shift``), and CI installs neither.
    Missing engine modules are stubbed only for the import and removed after,
    so later tests that probe for the real engine still see it as absent.
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
        from analysis.compute_shift_sweep import _state_delta_rows
    finally:
        for name in added:
            sys.modules.pop(name, None)
    return _state_delta_rows


sweep_rows = _import_sweep_rows()

CODES = ["AK", "CA", "FL", "NH", "NV", "NY", "SD", "TN", "TX", "WA", "WY"]


def _levels(code, scale):
    return {
        "household_state_tax_before_refundable_credits": scale * 1e9,
        "household_refundable_state_tax_credits": 0.0,
        "household_state_benefits": 0.0,
        "household_tax_before_refundable_credits": 2 * scale * 1e9,
        "eitc": 0.0,
        "snap": 0.0,
        "household_weight": 1e6,
    }


def _shuffled(mapping, seed):
    items = list(mapping.items())
    random.Random(seed).shuffle(items)
    return dict(items)


@pytest.mark.parametrize("rows", [scenario_rows, sweep_rows])
def test_state_delta_keys_are_sorted_whatever_the_input_order(rows):
    scenario = {c: _levels(c, i + 1.0) for i, c in enumerate(CODES)}
    baseline = {c: _levels(c, i + 0.5) for i, c in enumerate(CODES)}
    for seed in range(5):
        out = rows(_shuffled(scenario, seed), _shuffled(baseline, seed + 99))
        assert list(out) == sorted(CODES)


def _scenarios_file(tmp_path, order_seed):
    """A scenarios file whose Rapid rows list states in a shuffled order.

    Five states have no modelled base (baseline 0) and so tie on the ranking's
    first two keys; the rest have distinct exposures.
    """

    zero = {"FL", "NH", "NV", "SD", "TN", "TX", "WY"}
    rows = []
    for variant, shift in (
        ("compressive", 0.5),
        ("proportional", 1.0),
        ("expansive", 1.5),
    ):
        deltas = {
            c: {"state_net_change_b": 0.0 if c in zero else shift * (i + 1)}
            for i, c in enumerate(CODES)
        }
        rows.append(
            {
                "scenario": {"label": f"Rapid / {variant}"},
                "state_deltas": _shuffled(deltas, order_seed),
            }
        )
    path = tmp_path / f"scenarios_{order_seed}.json"
    path.write_text(
        json.dumps(
            {"metadata": {"runtime_fingerprint": {"digest": "d"}}, "scenarios": rows}
        )
    )
    baseline = {
        c: {
            "household_state_tax_before_refundable_credits": 0.0
            if c in zero
            else 10e9 * (len(CODES) - i),
            "household_weight": 1e6,
        }
        for i, c in enumerate(CODES)
    }
    return path, baseline


def _build(monkeypatch, tmp_path, order_seed):
    path, baseline = _scenarios_file(tmp_path, order_seed)
    monkeypatch.setattr(exposure, "runtime_fingerprint", lambda: {"digest": "d"})
    monkeypatch.setattr(exposure, "baseline_state_levels", lambda **kwargs: baseline)
    return exposure.build(
        verbose=False,
        scenarios_path=str(path),
        output_path=str(tmp_path / f"out_{order_seed}.json"),
        website_output_path="none",
    )


def test_exposure_ranking_is_independent_of_input_order(monkeypatch, tmp_path):
    orders = {
        tuple(e["state"] for e in _build(monkeypatch, tmp_path, seed)["states"])
        for seed in range(8)
    }
    assert len(orders) == 1
    (order,) = orders
    # Ranked states first, by exposure; the tied unmeasured states last, by code.
    unmeasured = [s for s in order if s in {"FL", "NH", "NV", "SD", "TN", "TX", "WY"}]
    assert unmeasured == sorted(unmeasured)
    assert list(order[-len(unmeasured) :]) == unmeasured


if given is not None:

    @settings(max_examples=50, deadline=None)
    @given(st.permutations(CODES), st.permutations(CODES))
    def test_state_delta_order_property(scenario_order, baseline_order):
        scenario = {c: _levels(c, 1.0) for c in scenario_order}
        baseline = {c: _levels(c, 0.5) for c in baseline_order}
        for rows in (scenario_rows, sweep_rows):
            out = rows(scenario, baseline)
            assert list(out) == sorted(CODES)
            assert out == rows(dict(sorted(scenario.items())), baseline)
