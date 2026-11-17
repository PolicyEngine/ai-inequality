# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.9"]
# ///
"""Draw the policy-analysis page's link-preview card from the sweep data.

Usage: uv run scripts/make_og_card.py
Reads src/data/shiftSweepData.json and writes
public/images/og/policy-analysis.png at 1200 x 630. The PNG carries the
year and amounts it drew, and the callout's whole billions, in a "Source"
text chunk, which src/utils/routeMetadata.test.js checks against the data
and the meta description, so a data refresh without a new card fails the
tests. Rerun this script after any refresh.
"""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "data" / "shiftSweepData.json"
OUT = ROOT / "public" / "images" / "og" / "policy-analysis.png"

# The repo's validated teal (analysis/california_chart.py) on a white card.
TEAL = "#00908E"
SURFACE = "#ffffff"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e1"
MINUS = "−"


def whole_billions(value):
    """Whole billions, halves away from zero, as routeMetadata.js rounds."""
    return math.floor(abs(value) + 0.5)


def money(value):
    size = whole_billions(value)
    sign = MINUS if value < 0 and size else ""
    return f"{sign}${size:,}B"


def main():
    assert money(-194.5) == f"{MINUS}$195B" and money(194.5) == "$195B"
    assert money(-0.4) == "$0B"
    data = json.loads(DATA.read_text())
    rows = sorted(data["scenarios"], key=lambda row: row["shift_pct"])
    xs = [row["shift_pct"] for row in rows]
    ys = [row["revenue_change_b"] for row in rows]
    year = data.get("metadata", {}).get("year", data.get("year"))
    ten = next(row["revenue_change_b"] for row in rows if row["shift_pct"] == 10)
    # The site's test for a run that counts health coverage
    # (countsHealthTanf in src/utils/sweepRevenue.js).
    counts_health = any(row.get("federal_health_change_b") is not None for row in rows)

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Inter", "Helvetica Neue", "Helvetica", "Arial"],
        }
    )
    fig = plt.figure(figsize=(12, 6.3), dpi=100)
    fig.patch.set_facecolor(SURFACE)
    ax = fig.add_axes([0.11, 0.19, 0.84, 0.53])
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(TEXT_SECONDARY)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.tick_params(colors=TEXT_SECONDARY, length=0, labelsize=15)
    ax.set_xlim(-2, 102)
    ax.set_xticks(range(0, 101, 10))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: money(v)))
    ax.set_xlabel(
        "Share of labor income shifted to capital income",
        color=TEXT_SECONDARY,
        fontsize=15,
    )
    ax.axhline(0, color=TEXT_SECONDARY, linewidth=1)
    ax.plot(xs, ys, color=TEAL, linewidth=4, solid_capstyle="round")
    ax.plot([10], [ten], "o", color=TEAL, markersize=13, markeredgecolor=SURFACE,
            markeredgewidth=3)
    ax.annotate(
        f"{money(ten)} at a 10% shift",
        xy=(10, ten),
        xytext=(16, ten * 0.35),
        fontsize=19,
        fontweight="bold",
        color=TEXT_PRIMARY,
        va="center",
    )

    fig.text(0.04, 0.9, f"US net government revenue change, {year}",
             fontsize=30, fontweight="bold", color=TEXT_PRIMARY)
    scope = (
        "Federal, state and local taxes less benefits and health coverage, "
        "excluding corporate taxes"
        if counts_health
        else "Federal, state and local taxes less benefits, excluding health "
        "coverage and corporate taxes"
    )
    fig.text(0.04, 0.82, scope, fontsize=16, color=TEXT_SECONDARY)
    fig.text(0.04, 0.04, "PolicyEngine prototype analysis",
             fontsize=14, color=TEXT_SECONDARY)
    fig.text(0.96, 0.04, "policyengine.org/us/ai-inequality", fontsize=14,
             color=TEXT_SECONDARY, ha="right")

    source = {
        "file": "src/data/shiftSweepData.json",
        "year": year,
        "counts_health": counts_health,
        "revenue_change_b": {str(x): round(y, 3) for x, y in zip(xs, ys)},
        # The callout's whole billions, which the meta description must match.
        "callout_billions_at_10": whole_billions(ten),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=SURFACE, metadata={"Source": json.dumps(source)})
    plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
