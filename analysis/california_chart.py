"""Chart California's revenue change across the labor-to-capital shift.

Reads either the site's sweep payload (``src/data/shiftSweepData.json``) or a
``california_shift`` run, and writes one PNG.

Usage:
    python -m analysis.california_chart --source sweep --out PATH.png
    python -m analysis.california_chart --source run --run PATH.json --out PATH.png
"""

from __future__ import annotations

import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP_PATH = os.path.join(REPO, "src", "data", "shiftSweepData.json")

# Validated with the dataviz skill's palette checker (light surface #fcfcfb):
# every check passes for this pair.
CALIFORNIA = "#00908E"
OTHER_STATES = "#EB6834"
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e1"


def series_from_sweep(path=SWEEP_PATH):
    data = json.load(open(path))
    xs, ca, other = [], [], []
    for row in data["scenarios"]:
        states = row.get("state_deltas") or {}
        xs.append(row["shift_pct"])
        if not states:
            ca.append(0.0)
            other.append(0.0)
            continue
        ca_net = states["CA"]["state_net_change_b"]
        total = sum(v["state_net_change_b"] for v in states.values())
        ca.append(ca_net)
        other.append(total - ca_net)
    meta = data["metadata"]
    note = f"policyengine-us {meta['country_model_version']}, data year {data['year']}"
    return xs, ca, None, other, note


def series_from_run(path):
    data = json.load(open(path))
    xs, ca, ca_sdi, other = [0], [0.0], [0.0], [0.0]
    for row in data["levels"]:
        xs.append(row["shift_pct"])
        ca.append(row["california"]["state_net_change_b"])
        ca_sdi.append(row["california"]["state_net_including_sdi_change_b"])
        other.append(row["other_states_net_change_b"])
    meta = data["metadata"]
    note = f"policyengine-us {meta['policyengine_us_version']}, data year {data['year']}"
    return xs, ca, ca_sdi, other, note


def draw(xs, ca, ca_sdi, other, out, source_note):
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Inter", "Helvetica Neue", "Helvetica", "Arial"],
            "font.size": 11,
        }
    )
    fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    ax.axhline(0, color=TEXT_SECONDARY, linewidth=0.8, zorder=1)
    ax.plot(xs, ca, color=CALIFORNIA, linewidth=2, marker="o", markersize=5,
            label="California", zorder=3)
    if ca_sdi is not None:
        ax.plot(xs, ca_sdi, color=CALIFORNIA, linewidth=2, linestyle=(0, (4, 3)),
                marker="o", markersize=4, markerfacecolor=SURFACE,
                label="California, including SDI", zorder=3)
    ax.plot(xs, other, color=OTHER_STATES, linewidth=2, marker="o", markersize=5,
            label="All other states combined", zorder=3)

    # Direct labels at the line ends, in text ink beside the colored mark.
    ends = [(ca[-1], "California")]
    if ca_sdi is not None:
        ends.append((ca_sdi[-1], "California, including SDI"))
    ends.append((other[-1], "All other states"))
    for y, text in ends:
        ax.annotate(f"{text}  ${y:,.0f}B", xy=(xs[-1], y), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9.5,
                    color=TEXT_PRIMARY)

    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 20))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}B"))
    ax.set_xlabel("Share of labor income shifted to capital income", color=TEXT_SECONDARY)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=TEXT_SECONDARY, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=9.5, labelcolor=TEXT_PRIMARY)

    fig.text(0.06, 0.955, "California gains as labor income shifts to capital",
             fontsize=14, fontweight="bold", color=TEXT_PRIMARY, ha="left")
    fig.text(0.06, 0.915,
             "Change in state income tax net of refundable state credits and "
             "state-funded benefits, $ billions",
             fontsize=10, color=TEXT_SECONDARY, ha="left")
    fig.text(0.06, 0.02,
             "PolicyEngine static microsimulation of current law on Microcosm "
             f"microdata ({source_note}). Total income held fixed; new capital "
             "income follows existing holdings.",
             fontsize=7.5, color=TEXT_SECONDARY, ha="left", wrap=True)
    fig.subplots_adjust(left=0.1, right=0.76, top=0.86, bottom=0.16)
    fig.savefig(out, facecolor=SURFACE)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=["sweep", "run"], default="sweep")
    parser.add_argument("--run", default=None, help="california_shift output JSON")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.source == "sweep":
        series = series_from_sweep()
    else:
        series = series_from_run(args.run)
    xs, ca, ca_sdi, other, note = series
    print(draw(xs, ca, ca_sdi, other, args.out, note))


if __name__ == "__main__":
    main()
