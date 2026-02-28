"""Visualization functions for labor-to-capital shift analysis."""

import os

import numpy as np
import plotly.graph_objects as go

from .metrics import lorenz_curve


def generate_all(results, output_dir):
    """Generate and save all labor shift charts.

    Args:
        results: Dict from labor_capital_shift.run_scenarios().
        output_dir: Directory to write HTML files.
    """
    os.makedirs(output_dir, exist_ok=True)

    _gini_comparison(results, output_dir)
    _decile_shares(results, output_dir)
    _lorenz(results, output_dir)
    _poverty_comparison(results, output_dir)

    print(f"  Saved 4 interactive charts to {output_dir}")


def _gini_comparison(results, output_dir):
    all_rows = [results["baseline"]] + results["shifts"]
    if results["ubi"]:
        all_rows.append(results["ubi"])
    scenarios = [r["label"] for r in all_rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Market Gini", x=scenarios,
        y=[r["market_gini"] for r in all_rows],
    ))
    fig.add_trace(go.Bar(
        name="Net Gini", x=scenarios,
        y=[r["net_gini"] for r in all_rows],
    ))

    fig.update_layout(
        title="Gini coefficients: labor-to-capital shift scenarios",
        yaxis_title="Gini coefficient",
        barmode="group",
        width=800, height=500,
    )
    fig.write_html(os.path.join(output_dir, "gini_comparison.html"))


def _decile_shares(results, output_dir):
    labels = [f"D{i+1}" for i in range(10)]
    all_rows = [results["baseline"]] + results["shifts"]
    if results["ubi"]:
        all_rows.append(results["ubi"])

    fig = go.Figure()
    for r in all_rows:
        fig.add_trace(go.Bar(
            name=r["label"], x=labels, y=r["decile_shares"],
        ))

    fig.update_layout(
        title="Net income shares by decile: labor shift scenarios",
        xaxis_title="Income decile",
        yaxis_title="Share of total net income",
        yaxis_tickformat=".1%",
        barmode="group",
        width=800, height=500,
    )
    fig.write_html(os.path.join(output_dir, "decile_shares.html"))


def _lorenz(results, output_dir):
    fig = go.Figure()

    all_rows = [results["baseline"]] + results["shifts"]
    if results["ubi"]:
        all_rows.append(results["ubi"])

    for r in all_rows:
        series = r["_net_income"]
        x, y = lorenz_curve(np.array(series.values), np.array(series.weights))
        fig.add_trace(go.Scatter(x=x, y=y, name=r["label"], mode="lines"))

    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], name="Perfect equality",
        mode="lines", line=dict(dash="dash", color="gray"),
    ))

    fig.update_layout(
        title="Lorenz curves: labor shift scenarios",
        xaxis_title="Cumulative population share",
        yaxis_title="Cumulative income share",
        width=800, height=600,
    )
    fig.write_html(os.path.join(output_dir, "lorenz_curves.html"))


def _poverty_comparison(results, output_dir):
    all_rows = [results["baseline"]] + results["shifts"]
    if results["ubi"]:
        all_rows.append(results["ubi"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[r["label"] for r in all_rows],
        y=[r["spm_poverty_rate"] for r in all_rows],
        marker_color=["#636EFA"] + ["#EF553B"] * len(results["shifts"])
        + (["#00CC96"] if results["ubi"] else []),
    ))

    fig.update_layout(
        title="SPM poverty rate: labor shift scenarios",
        yaxis_title="SPM poverty rate",
        yaxis_tickformat=".1%",
        width=800, height=500,
    )
    fig.write_html(os.path.join(output_dir, "poverty_comparison.html"))
