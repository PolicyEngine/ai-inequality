"""Build the paper's figures as vector PDFs under paper/figures/.

Reads the same canonical result files as emit_paper_values.py. Colors follow
the site's chart palette (src/components/AIScenarios.jsx).

Usage:
    python analysis/paper_figures.py
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "outputs")
FIG = os.path.join(ROOT, "paper", "figures")

TEAL = "#227773"
NAVY = "#17354F"
GRAY = "#718096"
GRID = "#e2e8f0"
BAD = "#ef4444"
GOOD = "#22c55e"

plt.rcParams.update(
    {
        "font.size": 9,
        "axes.titlesize": 9.5,
        "axes.labelsize": 9,
        "axes.edgecolor": GRAY,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "legend.frameon": False,
        "figure.dpi": 150,
    }
)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, name))
    plt.close(fig)
    print("wrote", name)


def main():
    os.makedirs(FIG, exist_ok=True)
    with open(os.path.join(OUT, "ai_scenarios.json")) as fh:
        sc = json.load(fh)
    with open(os.path.join(ROOT, "src", "data", "shiftSweepData.json")) as fh:
        sweep = json.load(fh)
    base = sc["baseline"]

    rows = sorted(sweep["scenarios"], key=lambda r: r["shift_pct"])
    x = [r["shift_pct"] for r in rows]

    def payroll(r):
        if "payroll_change_b" in r:
            return r["payroll_change_b"]
        return (
            r["employee_ss_tax_change_b"]
            + r["employee_medicare_tax_change_b"]
            + r["employer_payroll_change_b"]
            + r.get("self_employment_tax_change_b", 0.0)
        )

    # --- Figure 1: sweep revenue decomposition ---
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.axhspan(0, 0, color=GRAY)
    ax.axhline(0, color=GRAY, lw=0.8, ls=(0, (4, 3)))
    ax.plot(x, [r["total_rev_change_b"] for r in rows], color=TEAL, lw=2, label="Net government revenue")
    ax.plot(x, [r["income_tax_change_b"] for r in rows], color=NAVY, lw=1.4, label="Federal income tax")
    ax.plot(x, [payroll(r) for r in rows], color=GRAY, lw=1.4, label="Payroll")
    ax.plot(
        x,
        [
            r["state_tax_before_refundable_credits_change_b"]
            - r["state_refundable_credits_change_b"]
            for r in rows
        ],
        color=TEAL,
        lw=1.2,
        ls=":",
        label="State tax (net)",
    )
    ax.plot(
        x,
        [-r["benefits_change_b"] for r in rows],
        color=BAD,
        lw=1.2,
        ls="--",
        label="Benefit outlays (sign flipped)",
    )
    # Forecast-equivalence band, derived the same way as emit_paper_values.py.
    ks = {}
    for r in sc["scenarios"]:
        s = r["scenario"]
        if s["inequality"] == "proportional" and not s.get("hold_shares_fixed"):
            ks[s["name"]] = 100 * (1 - (1 + s["labor_growth"]) / (1 + s["gdp_growth"]))
    band = ks["Rapid"]
    ax.axvspan(0, band, color=TEAL, alpha=0.08)
    ax.annotate(
        "forecast-equivalent range\n"
        f"(Slow {ks['Slow']:.1f}, Moderate {ks['Moderate']:.1f}, Rapid {ks['Rapid']:.1f})",
        xy=(band, ax.get_ylim()[0]),
        xytext=(10, -880),
        fontsize=7.5,
        color=TEAL,
    )
    ax.set_xlabel("Share of labor income shifted to capital (%)")
    ax.set_ylabel("Change vs baseline ($B, 2026)")
    ax.grid(axis="y")
    ax.legend(fontsize=7.5, loc="lower left")
    save(fig, "sweep_revenue.pdf")

    # --- Figure 2: sweep distribution ---
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.9))
    axes[0].plot(x, [r["net_gini"] for r in rows], color=TEAL, lw=2)
    axes[0].set_ylabel("Net-income Gini")
    axes[1].plot(
        x, [100 * r["spm_poverty_rate"] for r in rows], color=BAD, lw=2
    )
    axes[1].set_ylabel("SPM poverty rate (%)")
    for ax in axes:
        ax.set_xlabel("Share of labor income shifted (%)")
        ax.grid(axis="y")
        ax.axvspan(0, band, color=TEAL, alpha=0.08)
    save(fig, "sweep_distribution.pdf")

    # --- Figure 3: scenario grid ---
    names = ["Slow", "Moderate", "Rapid"]
    variants = [
        ("fixed", "Shares fixed", NAVY),
        ("compressive", "Compressive", GOOD),
        ("proportional", "Proportional", TEAL),
        ("expansive", "Expansive", BAD),
    ]

    def srow(name, var):
        for r in sc["scenarios"]:
            s = r["scenario"]
            fixed = var == "fixed"
            if (
                s["name"] == name
                and bool(s.get("hold_shares_fixed")) == fixed
                and (fixed or s["inequality"] == var)
            ):
                return r

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0))
    w = 0.19
    xs = np.arange(len(names))
    for i, (var, label, color) in enumerate(variants):
        rev = [srow(n, var)["total_rev_change_b"] for n in names]
        pov = [
            100 * (srow(n, var)["spm_poverty_rate"] - base["spm_poverty_rate"])
            for n in names
        ]
        off = (i - 1.5) * w
        axes[0].bar(xs + off, rev, w, color=color, label=label)
        axes[1].bar(xs + off, pov, w, color=color, label=label)
    axes[0].set_ylabel("Net revenue change ($B, 2030)")
    axes[1].set_ylabel("SPM poverty change (pp)")
    axes[1].axhline(0, color=GRAY, lw=0.8)
    for ax in axes:
        ax.set_xticks(xs)
        ax.set_xticklabels(names)
        ax.grid(axis="y")
    axes[0].legend(fontsize=7, ncol=1)
    save(fig, "scenarios.pdf")

    # --- Figure 4: realization sweep ---
    real = sorted(
        sc["sensitivities"]["realization"],
        key=lambda r: r["scenario"]["realization_rate"],
    )
    rp = srow("Rapid", "proportional")
    rates = [r["scenario"]["realization_rate"] for r in real] + [1.0]
    revs = [r["total_rev_change_b"] for r in real] + [rp["total_rev_change_b"]]
    # Their committed Rapid corporate wedge (g_K times their CBO 2030 CIT level;
    # realization-independent).
    import pandas as pd

    wedge = float(
        pd.read_excel(
            os.path.join(OUT, "yale_publishable_2030.xlsx"),
            sheet_name="revenue_grid_wide",
            engine="openpyxl",
        )
        .set_index("scenario_id")
        .loc["ai_R_R_S0_V1", "macro_cit_delta"]
    )
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    ax.axhline(0, color=GRAY, lw=0.8, ls=(0, (4, 3)))
    ax.plot(
        [100 * r for r in rates], revs, color=TEAL, lw=2, marker="o", ms=3.5,
        label="Household-sector net revenue",
    )
    ax.plot(
        [100 * r for r in rates],
        [v + wedge for v in revs],
        color=NAVY,
        lw=1.3,
        ls="--",
        label=f"Plus their corporate wedge (+${wedge:.0f}B)",
    )
    # Breakeven.
    grid = sorted(zip(rates, revs))
    for (x0, y0), (x1, y1) in zip(grid, grid[1:]):
        if y0 <= 0 <= y1:
            bx = 100 * (x0 + (0 - y0) * (x1 - x0) / (y1 - y0))
            ax.plot([bx], [0], marker="D", color=BAD, ms=5)
            ax.annotate(
                f"breakeven {bx:.1f}%",
                xy=(bx, 0),
                xytext=(bx + 4, -38),
                fontsize=8,
                color=BAD,
            )
    ax.set_xlabel("Realized share of the incremental capital flow (%)")
    ax.set_ylabel("Revenue change ($B, 2030)")
    ax.grid(axis="y")
    ax.legend(fontsize=7.5, loc="upper left")
    save(fig, "realization.pdf")

    # --- Figure 5: transfer decomposition across Rapid variants ---
    labels = ["Compressive", "Proportional", "Expansive"]
    gross, transfers, net = [], [], []
    for var in ("compressive", "proportional", "expansive"):
        r = srow("Rapid", var)
        tr = r["refundable_credits_change_b"] + r["benefits_change_b"]
        transfers.append(tr)
        net.append(r["total_rev_change_b"])
        gross.append(r["total_rev_change_b"] + tr)
    xs = np.arange(3)
    fig, ax = plt.subplots(figsize=(5.6, 3.1))
    ax.bar(xs - 0.22, gross, 0.2, color=NAVY, label="Gross tax collections")
    ax.bar(xs, transfers, 0.2, color=BAD, label="Automatic transfer response")
    ax.bar(xs + 0.22, net, 0.2, color=TEAL, label="Net revenue")
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Change vs baseline ($B, 2030)")
    ax.grid(axis="y")
    ax.legend(fontsize=7.5)
    save(fig, "transfers.pdf")

    # --- Figure 6: state concentration ---
    rp_states = {
        k: v["state_net_change_b"]
        for k, v in srow("Rapid", "proportional")["state_deltas"].items()
        if isinstance(v, dict) and "state_net_change_b" in v
    }
    top = sorted(rp_states.items(), key=lambda kv: kv[1], reverse=True)[:10]
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    codes = [c for c, _ in top][::-1]
    vals = [v for _, v in top][::-1]
    colors = [TEAL if c != "WA" else NAVY for c in codes]
    ax.barh(codes, vals, color=colors, height=0.62)
    ax.set_xlabel("Net state revenue change ($B, Rapid / proportional, 2030)")
    ax.grid(axis="x")
    for c, v in zip(codes, vals):
        ax.annotate(
            f"{v:+.1f}", xy=(v, c), xytext=(3, -2), textcoords="offset points",
            fontsize=7.5, color=GRAY,
        )
    if "WA" in codes:
        ax.annotate(
            "WA has no income tax; its take is the\ncapital gains excise tax",
            xy=(0.98, 0.05),
            xycoords="axes fraction",
            ha="right",
            fontsize=7.5,
            color=NAVY,
        )
    save(fig, "states.pdf")


if __name__ == "__main__":
    main()
