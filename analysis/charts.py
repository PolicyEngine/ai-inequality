"""Visualization functions for capital income doubling analysis."""

import os

import plotly.express as px
import plotly.graph_objects as go

from .metrics import lorenz_curve


def generate_all(results, output_dir):
    """Generate and save all charts.

    Args:
        results: Dict from simulation.run_scenarios().
        output_dir: Directory to write HTML files.
    """
    os.makedirs(output_dir, exist_ok=True)

    _lorenz(results, output_dir)
    _decile_shares(results, output_dir)
    _gini_comparison(results, output_dir)
    _state_map(results, output_dir)

    print(f"  Saved 4 interactive charts to {output_dir}")


def _lorenz(results, output_dir):
    import numpy as np

    fig = go.Figure()
    for key in ("baseline", "doubled", "ubi"):
        r = results[key]
        series = r["_net_income"]
        x, y = lorenz_curve(np.array(series.values), np.array(series.weights))
        fig.add_trace(go.Scatter(x=x, y=y, name=r["label"], mode="lines"))
    fig.add_trace(
        go.Scatter(x=[0, 1], y=[0, 1], name="Perfect equality",
                   mode="lines", line=dict(dash="dash", color="gray"))
    )
    fig.update_layout(
        title="Lorenz curves: net income distribution",
        xaxis_title="Cumulative population share",
        yaxis_title="Cumulative income share",
        width=800, height=600,
    )
    fig.write_html(os.path.join(output_dir, "lorenz_curves.html"))


def _decile_shares(results, output_dir):
    labels = [f"D{i+1}" for i in range(10)]
    fig = go.Figure()
    for key in ("baseline", "doubled", "ubi"):
        r = results[key]
        fig.add_trace(go.Bar(name=r["label"], x=labels, y=r["decile_shares"]))
    fig.update_layout(
        title="Net income shares by decile",
        xaxis_title="Income decile",
        yaxis_title="Share of total net income",
        yaxis_tickformat=".1%",
        barmode="group",
        width=800, height=500,
    )
    fig.write_html(os.path.join(output_dir, "decile_shares.html"))


def _gini_comparison(results, output_dir):
    scenarios = [results[k]["label"] for k in ("baseline", "doubled", "ubi")]
    market = [results[k]["market_gini"] for k in ("baseline", "doubled", "ubi")]
    net = [results[k]["net_gini"] for k in ("baseline", "doubled", "ubi")]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Market Gini", x=scenarios, y=market))
    fig.add_trace(go.Bar(name="Net Gini", x=scenarios, y=net))
    fig.update_layout(
        title="Gini coefficients across scenarios",
        yaxis_title="Gini coefficient",
        barmode="group",
        width=800, height=500,
    )
    fig.write_html(os.path.join(output_dir, "gini_comparison.html"))


def _state_map(results, output_dir):
    fig = px.choropleth(
        results["state_summary"],
        locations="state",
        locationmode="USA-states",
        color="extra_per_capita",
        scope="usa",
        color_continuous_scale="Reds",
        title="Extra tax revenue per capita by state (doubled capital income)",
        labels={"extra_per_capita": "Extra revenue/capita ($)"},
    )
    fig.update_layout(width=900, height=600)
    fig.write_html(os.path.join(output_dir, "state_revenue_map.html"))
