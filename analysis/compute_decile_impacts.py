"""Per-decile net-income impact of the labor→capital shift.

Reads the household microdata CSVs written alongside the sweep and
computes, for each shift level:

  - mean household net income within each baseline market-income decile
  - mean change vs baseline, in dollars and as % of baseline net income

Deciles are defined on weighted baseline market income. Each household
keeps its baseline decile across scenarios, so we're tracking "what
happens to households who started in this part of the distribution."

``decile_impacts`` reads any folder that ``microdata_export`` wrote, guided by
its ``manifest.json``. ``main`` reads ``analysis/outputs/shift_sweep_microdata``
and merges the result into shift_sweep.json under
metadata.baseline_facts.decile_impacts so the website can render a
winners/losers chart.
"""

import json
import os

import numpy as np
import pandas as pd

MICRODATA_DIR = os.path.join(
    os.path.dirname(__file__), "outputs", "shift_sweep_microdata"
)

METHODOLOGY = (
    "Households are bucketed into deciles by baseline weighted "
    "market income. Each household's decile membership is fixed at "
    "baseline across all shift scenarios, so the chart tracks how "
    "the same groups move with the experiment."
)


def baseline_deciles(market_income, weights):
    """Each household's decile (1-10) of weighted baseline market income.

    Households sort by market income, ties in row order. Decile d holds the
    households whose cumulative weight, counting their own, exceeds (d-1)/10
    of the total and reaches at most d/10 of it.
    """
    market_income = np.asarray(market_income, dtype=float)
    weights = np.asarray(weights, dtype=float)
    sorted_idx = np.argsort(market_income, kind="stable")
    cum = np.cumsum(weights[sorted_idx])
    total = cum[-1]
    decile_edges = [
        np.searchsorted(cum, total * i / 10, side="right") for i in range(1, 10)
    ]
    labels = np.zeros(len(market_income), dtype=int)
    labels[sorted_idx] = (
        np.digitize(np.arange(len(sorted_idx)), decile_edges, right=False) + 1
    )
    return labels


def _decile_stats(net_values, weights, decile_labels):
    rows = []
    for d in range(1, 11):
        mask = decile_labels == d
        w = weights[mask].sum()
        total_net = (net_values[mask] * weights[mask]).sum()
        mean_net = total_net / w if w > 0 else float("nan")
        rows.append({"decile": d, "weight": float(w), "mean_net": float(mean_net)})
    return rows


def decile_impacts(microdata_dir):
    """Decile impacts for every scenario that ``microdata_dir``'s manifest lists.

    Households align across scenario files by row order, as
    ``microdata_export`` writes them; a file with a different row count
    raises ValueError.
    """
    with open(os.path.join(microdata_dir, "manifest.json")) as f:
        manifest = json.load(f)
    entries = sorted(manifest["scenarios"], key=lambda entry: entry["shift_pct"])
    if not entries or entries[0]["shift_pct"] != 0:
        raise ValueError(f"{microdata_dir}'s manifest lists no baseline (shift_pct 0)")

    def load(entry):
        return pd.read_csv(os.path.join(microdata_dir, entry["filename"]))

    # Keep CSV row order so households align across scenarios. Sorting by
    # market income would re-order shift scenarios because their market
    # income differs — we would then mis-assign deciles.
    baseline = load(entries[0])
    weights = baseline["household_weight"].to_numpy(dtype=float)
    decile_labels = baseline_deciles(
        baseline["household_market_income"].to_numpy(dtype=float), weights
    )
    baseline_stats = _decile_stats(
        baseline["household_net_income"].to_numpy(dtype=float), weights, decile_labels
    )
    baseline_mean = {r["decile"]: r["mean_net"] for r in baseline_stats}

    scenarios = []
    for entry in entries:
        frame = baseline if entry["shift_pct"] == 0 else load(entry)
        if len(frame) != len(baseline):
            raise ValueError(
                f"Row count mismatch at shift {entry['shift_pct']}% "
                f"({len(frame)} vs {len(baseline)})"
            )
        stats = _decile_stats(
            frame["household_net_income"].to_numpy(dtype=float), weights, decile_labels
        )
        for s in stats:
            s["baseline_mean_net"] = baseline_mean[s["decile"]]
            s["delta_mean_net"] = s["mean_net"] - baseline_mean[s["decile"]]
            s["pct_change"] = (
                (s["mean_net"] / baseline_mean[s["decile"]] - 1) * 100
                if baseline_mean[s["decile"]] > 0
                else None
            )
        scenarios.append({"shift_pct": int(entry["shift_pct"]), "deciles": stats})

    return {
        "baseline_mean_net_by_decile": baseline_stats,
        "scenarios": scenarios,
        "methodology": METHODOLOGY,
    }


def main():
    from .compute_shift_sweep import OUTPUT_PATH

    result = decile_impacts(MICRODATA_DIR)

    if not os.path.exists(OUTPUT_PATH):
        print("shift_sweep.json not found; saving standalone.")
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

    shift_levels = [s["shift_pct"] for s in result["scenarios"]]
    print("\nMean net-income change by decile (%):")
    header_cells = " ".join(f"{pct:>5}%" for pct in shift_levels if pct > 0)
    print(f"{'Decile':>7}  {header_cells}")
    for d in range(1, 11):
        row = [f"D{d:>5}"]
        for scenario in result["scenarios"]:
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
