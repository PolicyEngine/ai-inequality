"""Visualization functions for capital income sweep analysis."""

import os

import plotly.graph_objects as go

from .metrics import lorenz_curve


def generate_all(results, output_dir):
    """Generate and save all sweep charts.

    Args:
        results: Dict from capital_share_sweep.run_sweep().
        output_dir: Directory to write HTML files.
    """
    os.makedirs(output_dir, exist_ok=True)

    _gini_vs_multiplier(results, output_dir)
    _poverty_vs_multiplier(results, output_dir)
    _revenue_vs_multiplier(results, output_dir)
    _decile_shares(results, output_dir)

    print(f"  Saved 4 interactive charts to {output_dir}")


def _gini_vs_multiplier(results, output_dir):
    rows = results["rows"]
    mults = [r["multiplier"] for r in rows]
    cap_shares = [r["capital_share"] for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=mults, y=[r["market_gini"] for r in rows],
        name="Market Gini", mode="lines+markers",
    ))
    fig.add_trace(go.Scatter(
        x=mults, y=[r["net_gini"] for r in rows],
        name="Net Gini", mode="lines+markers",
    ))

    fig.update_layout(
        title="Gini coefficient vs capital income multiplier",
        xaxis_title="Capital income multiplier",
        yaxis_title="Gini coefficient",
        width=800, height=500,
    )
    # Add capital share as secondary x-axis labels via annotations
    for mult, cs in zip(mults, cap_shares):
        fig.add_annotation(
            x=mult, y=0, yref="paper", yshift=-35,
            text=f"{cs:.0%}", showarrow=False, font=dict(size=9),
        )
    fig.add_annotation(
        x=0.5, y=0, xref="paper", yref="paper", yshift=-55,
        text="Capital share of market income",
        showarrow=False, font=dict(size=11),
    )
    fig.write_html(os.path.join(output_dir, "gini_vs_multiplier.html"))


def _poverty_vs_multiplier(results, output_dir):
    rows = results["rows"]
    mults = [r["multiplier"] for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=mults, y=[r["spm_poverty_rate"] for r in rows],
        name="SPM poverty rate", mode="lines+markers",
        line=dict(color="red"),
    ))

    fig.update_layout(
        title="SPM poverty rate vs capital income multiplier",
        xaxis_title="Capital income multiplier",
        yaxis_title="SPM poverty rate",
        yaxis_tickformat=".1%",
        width=800, height=500,
    )
    fig.write_html(os.path.join(output_dir, "poverty_vs_multiplier.html"))


def _revenue_vs_multiplier(results, output_dir):
    rows = results["rows"]
    mults = [r["multiplier"] for r in rows]
    baseline_rev = rows[0]["total_revenue"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=mults,
        y=[r["total_revenue"] / 1e9 for r in rows],
        name="Total revenue", mode="lines+markers",
    ))
    fig.add_trace(go.Scatter(
        x=mults,
        y=[(r["total_revenue"] - baseline_rev) / 1e9 for r in rows],
        name="Extra revenue", mode="lines+markers",
        line=dict(dash="dash"),
    ))

    fig.update_layout(
        title="Tax revenue vs capital income multiplier",
        xaxis_title="Capital income multiplier",
        yaxis_title="Revenue ($B)",
        width=800, height=500,
    )
    fig.write_html(os.path.join(output_dir, "revenue_vs_multiplier.html"))


def _decile_shares(results, output_dir):
    rows = results["rows"]
    labels = [f"D{i+1}" for i in range(10)]

    # Show baseline, 2x, and 5x
    fig = go.Figure()
    for r in rows:
        if r["multiplier"] in (1.0, 2.0, 5.0):
            fig.add_trace(go.Bar(
                name=r["label"], x=labels, y=r["decile_shares"],
            ))

    fig.update_layout(
        title="Net income shares by decile",
        xaxis_title="Income decile",
        yaxis_title="Share of total net income",
        yaxis_tickformat=".1%",
        barmode="group",
        width=800, height=500,
    )
    fig.write_html(os.path.join(output_dir, "decile_shares.html"))
