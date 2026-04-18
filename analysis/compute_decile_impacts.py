"""Per-decile net-income impact of the labor→capital shift.

Reads the household microdata CSVs written alongside the sweep and
computes, for each shift level:

  - mean household net income within each baseline market-income decile
  - mean change vs baseline, in dollars and as % of baseline net income

Deciles are defined on weighted baseline market income. Each household
keeps its baseline decile across scenarios, so we're tracking "what
happens to households who started in this part of the distribution."

Output is merged into shift_sweep.json under
metadata.baseline_facts.decile_impacts so the website can render a
winners/losers chart.
"""

import json
import os

import numpy as np
import pandas as pd

from .compute_shift_sweep import OUTPUT_PATH

MICRODATA_DIR = os.path.join(
    os.path.dirname(__file__), "outputs", "shift_sweep_microdata"
)


def _load_scenario(filename):
    path = os.path.join(MICRODATA_DIR, filename)
    return pd.read_csv(path)


def main():
    manifest_path = os.path.join(MICRODATA_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Keep CSV row order so households align across scenarios. Sorting by
    # market income would re-order shift scenarios because their market
    # income differs — we would then mis-assign deciles.
    baseline = _load_scenario("baseline.csv.gz")
    weights = baseline["household_weight"].to_numpy()
    market = baseline["household_market_income"].to_numpy()
    net_base = baseline["household_net_income"].to_numpy()

    # Weighted deciles of baseline market income.
    sorted_idx = np.argsort(market)
    sorted_weights = weights[sorted_idx]
    cum = np.cumsum(sorted_weights)
    total = cum[-1]
    decile_edges = [np.searchsorted(cum, total * i / 10) for i in range(1, 10)]
    decile_labels = np.zeros_like(market, dtype=int)
    for i, idx in enumerate(sorted_idx):
        # decile_of[idx] = 1..10
        pass
    # Vectorized assignment.
    decile_of_sorted = np.digitize(
        np.arange(len(sorted_idx)), decile_edges, right=False
    ) + 1
    decile_labels[sorted_idx] = decile_of_sorted

    # Pre-compute baseline per-decile aggregates.
    def _decile_stats(net_values, weights, decile_labels):
        rows = []
        for d in range(1, 11):
            mask = decile_labels == d
            w = weights[mask].sum()
            total_net = (net_values[mask] * weights[mask]).sum()
            mean_net = total_net / w if w > 0 else float("nan")
            rows.append({"decile": d, "weight": float(w), "mean_net": float(mean_net)})
        return rows

    baseline_stats = _decile_stats(net_base, weights, decile_labels)
    baseline_mean = {r["decile"]: r["mean_net"] for r in baseline_stats}

    shift_levels = [int(pct) for pct in range(0, 101, 10)]
    all_scenarios = []
    for pct in shift_levels:
        if pct == 0:
            frame = baseline
        else:
            filename = f"shift_{pct:03d}.csv.gz"
            frame = _load_scenario(filename)
        # The rows should align with baseline on index (same microdata
        # universe). Assert first.
        if len(frame) != len(baseline):
            raise ValueError(
                f"Row count mismatch at shift {pct}% "
                f"({len(frame)} vs {len(baseline)})"
            )
        net = frame["household_net_income"].to_numpy()
        stats = _decile_stats(net, weights, decile_labels)
        for s in stats:
            s["baseline_mean_net"] = baseline_mean[s["decile"]]
            s["delta_mean_net"] = s["mean_net"] - baseline_mean[s["decile"]]
            s["pct_change"] = (
                (s["mean_net"] / baseline_mean[s["decile"]] - 1) * 100
                if baseline_mean[s["decile"]] > 0
                else None
            )
        all_scenarios.append({"shift_pct": pct, "deciles": stats})

    result = {
        "baseline_mean_net_by_decile": baseline_stats,
        "scenarios": all_scenarios,
        "methodology": (
            "Households are bucketed into deciles by baseline weighted "
            "market income. Each household's decile membership is fixed at "
            "baseline across all shift scenarios, so the chart tracks how "
            "the same groups move with the experiment."
        ),
    }

    if not os.path.exists(OUTPUT_PATH):
        print(f"shift_sweep.json not found; saving standalone.")
        path = os.path.join(
            os.path.dirname(__file__), "outputs", "decile_impacts.json"
        )
        with open(path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Saved to {path}")
        return

    with open(OUTPUT_PATH) as f:
        data = json.load(f)
    data.setdefault("metadata", {}).setdefault("baseline_facts", {})[
        "decile_impacts"
    ] = result
    with open(OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print("\nMean net-income change by decile (%):")
    header_cells = " ".join(f"{pct:>5}%" for pct in shift_levels if pct > 0)
    print(f"{'Decile':>7}  {header_cells}")
    for d in range(1, 11):
        row = [f"D{d:>5}"]
        for scenario in all_scenarios:
            if scenario["shift_pct"] == 0:
                continue
            bucket = next(s for s in scenario["deciles"] if s["decile"] == d)
            pct_change = bucket.get("pct_change")
            row.append(
                f"{pct_change:>5.1f}%" if pct_change is not None else "   nan"
            )
        print("  ".join(row))

    print(f"\nMerged decile impacts into {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
