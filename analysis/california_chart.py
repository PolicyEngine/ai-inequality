"""Chart California's revenue change across the labor-to-capital shift.

Reads either the site's sweep payload (``src/data/shiftSweepData.json``) or a
``california_shift`` run, and writes one PNG.

Usage:
    python -m analysis.california_chart --source sweep --out PATH.png
    python -m analysis.california_chart --source run --run PATH.json --out PATH.png [--california-only]
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

# The shift scales the six variables in ``constants.CAPITAL_INCOME_VARS``.
ALLOCATION_NOTE = (
    "We move labor income to capital income nationwide, in proportion to the interest, "
    "dividends, capital gains and rent people already receive."
)
# ``fiscal.state_revenue_delta`` nets California's refundable credits
# (gov.states.ca.tax.income.credits.refundable) and its entries in
# gov.household.household_state_benefits, which hold no CalWORKs or Medi-Cal.
CALIFORNIA_MEASURE_NOTE = (
    "We net out refundable credits like CalEITC and benefits like the SSI supplement, "
    "and leave out Medi-Cal and CalWORKs."
)
# ``california_shift._health_tanf_accounting`` adds California's share of
# Medi-Cal, CHIP and Medicare Savings Program costs, the coverage it funds
# alone, its premium subsidy and CalWORKs.
CALIFORNIA_HEALTH_TANF_NOTE = (
    "We net out refundable credits like CalEITC, benefits like the SSI supplement, CalWORKs, "
    "and California's Medi-Cal and premium subsidy spending."
)

#: What each measure reads from a run (California, California with SDI, all
#: other states) and how the chart describes it.
MEASURES = {
    "study": {
        "fields": (
            "state_net_change_b",
            "state_net_including_sdi_change_b",
            "other_states_net_change_b",
        ),
        "subtitle": (
            "Change in state tax revenue, net of refundable state credits and "
            "some state benefits, $ billions"
        ),
        "california_note": CALIFORNIA_MEASURE_NOTE,
    },
    "with_health_tanf": {
        "fields": (
            "state_net_with_health_tanf_change_b",
            "state_net_with_health_tanf_including_sdi_change_b",
            "other_states_net_with_health_tanf_change_b",
        ),
        "subtitle": (
            "Change in state tax revenue, net of credits, benefits, Medi-Cal and "
            "CalWORKs, $ billions"
        ),
        "subtitle_all_states": (
            "Change in state tax revenue, net of credits, benefits, Medicaid and "
            "TANF, $ billions"
        ),
        "california_note": CALIFORNIA_HEALTH_TANF_NOTE,
    },
}


def subtitle_for(measure, california_only):
    """The measure's subtitle, naming California's programs only when California stands alone."""
    entry = MEASURES[measure]
    if california_only:
        return entry["subtitle"]
    return entry.get("subtitle_all_states", entry["subtitle"])


def title_for(ca):
    """A title that says which way California's revenue moves."""
    moved = [v for v in ca if v != 0]
    if moved and all(v > 0 for v in moved):
        return "California gains as labor income shifts to capital"
    if moved and all(v < 0 for v in moved):
        return "California loses as labor income shifts to capital"
    return "California's revenue as labor income shifts to capital"


def dollar_format(values):
    """Format for $B labels: one decimal when the values span less than $5 billion."""
    span = max(values) - min(values) if values else 0.0
    decimals = 1 if span < 5 else 0
    return lambda v: f"${v:,.{decimals}f}B"


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
    note = f"policyengine-us {meta['country_model_version']}, {data['year']}"
    return xs, ca, None, other, note


def series_from_run(path, measure="with_health_tanf"):
    ca_key, ca_sdi_key, other_key = MEASURES[measure]["fields"]
    data = json.load(open(path))
    xs, ca, ca_sdi, other = [0], [0.0], [0.0], [0.0]
    for row in data["levels"]:
        xs.append(row["shift_pct"])
        ca.append(row["california"][ca_key])
        ca_sdi.append(row["california"][ca_sdi_key])
        other.append(row[other_key])
    meta = data["metadata"]
    note = f"policyengine-us {meta['policyengine_us_version']}, {data['year']}"
    return xs, ca, ca_sdi, other, note


def draw(xs, ca, ca_sdi, other, out, source_note, measure_note=None,
         subtitle=MEASURES["study"]["subtitle"]):
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
    # clip_on=False keeps the end markers at 0% and 100% whole.
    ax.plot(xs, ca, color=CALIFORNIA, linewidth=2, marker="o", markersize=5,
            label="California", zorder=3, clip_on=False)
    if ca_sdi is not None:
        ax.plot(xs, ca_sdi, color=CALIFORNIA, linewidth=2, linestyle=(0, (4, 3)),
                marker="o", markersize=4, markerfacecolor=SURFACE,
                label="California, including SDI contributions", zorder=3, clip_on=False)
    if other is not None:
        ax.plot(xs, other, color=OTHER_STATES, linewidth=2, marker="o", markersize=5,
                label="All other states combined", zorder=3, clip_on=False)

    drawn = list(ca) + list(ca_sdi or []) + list(other or [])
    dollars = dollar_format(drawn)

    # Direct labels at the line ends, in text ink beside the colored mark.
    ends = [(ca[-1], "California")]
    if ca_sdi is not None:
        ends.append((ca_sdi[-1], "California, including SDI"))
    if other is not None:
        ends.append((other[-1], "All other states"))
    for y, text in ends:
        ax.annotate(f"{text}  {dollars(y)}", xy=(xs[-1], y), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9.5,
                    color=TEXT_PRIMARY)

    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 20))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: dollars(v)))
    ax.set_xlabel("Share of labor income that moves to capital income", color=TEXT_SECONDARY)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=TEXT_SECONDARY, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=9.5, labelcolor=TEXT_PRIMARY)

    fig.text(0.06, 0.955, title_for(ca),
             fontsize=14, fontweight="bold", color=TEXT_PRIMARY, ha="left")
    fig.text(0.06, 0.915, subtitle, fontsize=10, color=TEXT_SECONDARY, ha="left")
    notes = [
        "Source: PolicyEngine static microsimulation of current law on Microcosm "
        f"data ({source_note}).",
        ALLOCATION_NOTE,
    ]
    if measure_note:
        notes.append(measure_note)
    fig.text(0.06, 0.02, "\n".join(notes), fontsize=7.5, color=TEXT_SECONDARY,
             ha="left", linespacing=1.4)
    fig.subplots_adjust(left=0.1, right=0.76, top=0.86, bottom=0.14 + 0.025 * len(notes))
    fig.savefig(out, facecolor=SURFACE)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=["sweep", "run"], default="sweep")
    parser.add_argument("--run", default=None, help="california_shift output JSON")
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--california-only",
        action="store_true",
        help="omit the all-other-states line, whose path depends on where new capital income lands",
    )
    parser.add_argument(
        "--measure",
        choices=sorted(MEASURES),
        default=None,
        help="state measure to chart: a run defaults to with_health_tanf; the sweep has only study",
    )
    args = parser.parse_args()
    if args.source == "sweep":
        measure = args.measure or "study"
        if measure != "study":
            parser.error("the sweep payload holds only the study measure")
        series = series_from_sweep()
    else:
        measure = args.measure or "with_health_tanf"
        series = series_from_run(args.run, measure)
    xs, ca, ca_sdi, other, note = series
    measure_note = None
    if args.california_only:
        other = None
        measure_note = MEASURES[measure]["california_note"]
    print(draw(xs, ca, ca_sdi, other, args.out, note, measure_note,
               subtitle=subtitle_for(measure, args.california_only)))


if __name__ == "__main__":
    main()
