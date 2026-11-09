"""Tests for analysis.compute_decile_impacts.

Invariants:

* every household gets a decile from 1 to 10, and a household with less
  baseline market income never gets a higher decile than one with more;
* each decile holds a tenth of the total weight, give or take the largest
  single household weight;
* the baseline scenario changes nothing;
* weighting each decile's mean change by its weight gives the total weighted
  change in net income.
"""

import json

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from analysis.compute_decile_impacts import baseline_deciles, decile_impacts


def _write(folder, frames):
    """Write {shift_pct: DataFrame} the way microdata_export does, with a manifest."""
    entries = []
    for pct, frame in frames.items():
        filename = "baseline.csv.gz" if pct == 0 else f"shift_{pct:03d}.csv.gz"
        frame.to_csv(folder / filename, index=False, compression="gzip")
        entries.append({"label": f"{pct}%", "shift_pct": pct, "filename": filename})
    (folder / "manifest.json").write_text(json.dumps({"scenarios": entries}))


def _frame(weights, market, net):
    return pd.DataFrame(
        {
            "household_weight": weights,
            "household_market_income": market,
            "household_net_income": net,
        }
    )


def test_hand_example(tmp_path):
    # Ten households, one per decile; household i has market income i.
    weights = [1.0] * 10
    market = [float(i) for i in range(1, 11)]
    base_net = [-50.0, 100, 200, 300, 400, 500, 600, 700, 800, 1000]
    shift_net = [-40.0, 90, 200, 300, 400, 500, 600, 700, 800, 1500]
    _write(
        tmp_path,
        {0: _frame(weights, market, base_net), 50: _frame(weights, market, shift_net)},
    )
    result = decile_impacts(tmp_path)
    assert [s["shift_pct"] for s in result["scenarios"]] == [0, 50]
    shifted = {d["decile"]: d for d in result["scenarios"][1]["deciles"]}
    assert shifted[10]["delta_mean_net"] == pytest.approx(500.0)
    assert shifted[10]["pct_change"] == pytest.approx(50.0)
    assert shifted[2]["pct_change"] == pytest.approx(-10.0)
    # A decile whose baseline mean is negative gets no percentage.
    assert shifted[1]["delta_mean_net"] == pytest.approx(10.0)
    assert shifted[1]["pct_change"] is None
    baseline = {d["decile"]: d for d in result["scenarios"][0]["deciles"]}
    assert all(d["delta_mean_net"] == 0 for d in baseline.values())


def test_reads_scenarios_from_the_manifest_in_shift_order(tmp_path):
    frame = _frame([1.0] * 10, list(range(10)), list(range(10)))
    _write(tmp_path, {30: frame, 0: frame, 10: frame})
    assert [s["shift_pct"] for s in decile_impacts(tmp_path)["scenarios"]] == [0, 10, 30]


def test_refuses_a_scenario_with_other_households(tmp_path):
    _write(
        tmp_path,
        {
            0: _frame([1.0] * 10, list(range(10)), list(range(10))),
            10: _frame([1.0] * 9, list(range(9)), list(range(9))),
        },
    )
    with pytest.raises(ValueError, match="Row count mismatch at shift 10%"):
        decile_impacts(tmp_path)


def test_refuses_a_manifest_without_a_baseline(tmp_path):
    _write(tmp_path, {10: _frame([1.0] * 10, list(range(10)), list(range(10)))})
    with pytest.raises(ValueError, match="no baseline"):
        decile_impacts(tmp_path)


households = st.integers(min_value=10, max_value=60).flatmap(
    lambda n: st.tuples(
        st.lists(st.floats(0.5, 1_000.0), min_size=n, max_size=n),
        st.lists(st.integers(-50_000, 500_000).map(float), min_size=n, max_size=n),
        st.lists(st.integers(-20_000, 400_000).map(float), min_size=n, max_size=n),
        st.lists(st.integers(-30_000, 30_000).map(float), min_size=n, max_size=n),
    )
)


@settings(max_examples=150, deadline=None)
@given(households)
def test_deciles_are_ordered_and_split_the_weight(data):
    weights, market, _, _ = (np.asarray(x) for x in data)
    labels = baseline_deciles(market, weights)
    assert labels.min() >= 1 and labels.max() <= 10
    order = np.argsort(market, kind="stable")
    assert (np.diff(labels[order]) >= 0).all()
    total = weights.sum()
    for d in range(1, 11):
        assert abs(weights[labels == d].sum() - total / 10) <= weights.max() + 1e-9 * total


@settings(max_examples=100, deadline=None)
@given(households)
def test_changes_add_up_and_the_baseline_changes_nothing(tmp_path_factory, data):
    weights, market, net, change = (np.asarray(x) for x in data)
    folder = tmp_path_factory.mktemp("microdata")
    _write(
        folder,
        {0: _frame(weights, market, net), 40: _frame(weights, market, net + change)},
    )
    result = decile_impacts(folder)
    base, shifted = result["scenarios"]
    # A household heavier than a tenth of the total can leave a decile empty.
    assert all(d["delta_mean_net"] == 0 for d in base["deciles"] if d["weight"] > 0)
    weighted = sum(
        d["weight"] * d["delta_mean_net"] for d in shifted["deciles"] if d["weight"] > 0
    )
    assert weighted == pytest.approx(float((weights * change).sum()), rel=1e-9, abs=1e-6)
