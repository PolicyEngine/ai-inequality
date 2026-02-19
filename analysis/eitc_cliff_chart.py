"""Chart: net income vs capital income for a min-wage single parent.

Shows EITC investment income cliff and other benefit interactions.
"""

import numpy as np
import plotly.graph_objects as go
from policyengine_us import Simulation

YEAR = 2026


def make_situation(capital_income, capital_type="qualified_dividend_income"):
    """Single parent, one child, earning federal minimum wage ($7.25 * 2080h)."""
    return {
        "people": {
            "parent": {
                "age": {YEAR: 30},
                "employment_income": {YEAR: 7.25 * 2080},  # ~$15,080
                capital_type: {YEAR: capital_income},
            },
            "child": {
                "age": {YEAR: 5},
            },
        },
        "tax_units": {
            "tax_unit": {
                "members": ["parent", "child"],
            },
        },
        "spm_units": {"spm_unit": {"members": ["parent", "child"]}},
        "families": {"family": {"members": ["parent", "child"]}},
        "households": {
            "household": {
                "members": ["parent", "child"],
                "state_code": {YEAR: "TX"},  # No state income tax
            },
        },
        "marital_units": {"marital_unit": {"members": ["parent"]}},
    }


def compute_series(capital_type, max_cap=30_000, steps=300):
    """Compute net income and components across capital income range."""
    cap_values = np.linspace(0, max_cap, steps)
    results = {
        "capital_income": cap_values,
        "household_net_income": [],
        "eitc": [],
        "snap": [],
        "income_tax": [],
        "ssi": [],
    }

    for cap in cap_values:
        sim = Simulation(situation=make_situation(float(cap), capital_type))
        results["household_net_income"].append(
            float(sim.calculate("household_net_income", YEAR).sum())
        )
        results["eitc"].append(
            float(sim.calculate("eitc", YEAR).sum())
        )
        results["snap"].append(
            float(sim.calculate("snap", YEAR).sum())
        )
        results["income_tax"].append(
            float(sim.calculate("income_tax", YEAR).sum())
        )
        results["ssi"].append(
            float(sim.calculate("ssi", YEAR).sum())
        )

    return {k: np.array(v) for k, v in results.items()}


def make_chart(results, capital_label):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results["capital_income"],
        y=results["household_net_income"],
        name="Net income",
        line=dict(width=3, color="#2c7a7b"),
    ))

    # 45-degree reference: net income if capital income just added with no clawbacks
    baseline_net = results["household_net_income"][0]
    fig.add_trace(go.Scatter(
        x=results["capital_income"],
        y=baseline_net + results["capital_income"],
        name="If no clawbacks (baseline + cap income)",
        line=dict(dash="dash", color="gray"),
    ))

    fig.update_layout(
        title=f"Net income vs. {capital_label}<br>"
              f"<sub>Single parent, 1 child, federal min wage ($15,080), TX</sub>",
        xaxis_title=f"{capital_label} ($)",
        yaxis_title="Household net income ($)",
        xaxis_tickformat="$,.0f",
        yaxis_tickformat="$,.0f",
        width=900, height=600,
        hovermode="x unified",
    )
    return fig


def make_component_chart(results, capital_label):
    fig = go.Figure()

    for name, key, color in [
        ("EITC", "eitc", "#e53e3e"),
        ("SNAP", "snap", "#38a169"),
        ("SSI", "ssi", "#805ad5"),
        ("Federal income tax", "income_tax", "#3182ce"),
    ]:
        fig.add_trace(go.Scatter(
            x=results["capital_income"],
            y=results[key],
            name=name,
            line=dict(width=2, color=color),
        ))

    fig.update_layout(
        title=f"Benefit/tax components vs. {capital_label}<br>"
              f"<sub>Single parent, 1 child, federal min wage ($15,080), TX</sub>",
        xaxis_title=f"{capital_label} ($)",
        yaxis_title="Amount ($)",
        xaxis_tickformat="$,.0f",
        yaxis_tickformat="$,.0f",
        width=900, height=600,
        hovermode="x unified",
    )
    return fig


if __name__ == "__main__":
    import os

    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    for cap_type, label in [
        ("qualified_dividend_income", "Qualified dividend income"),
        ("long_term_capital_gains", "Long-term capital gains"),
    ]:
        print(f"Computing {label}...")
        results = compute_series(cap_type)

        fig = make_chart(results, label)
        fig.write_html(os.path.join(output_dir, f"net_income_vs_{cap_type}.html"))

        comp_fig = make_component_chart(results, label)
        comp_fig.write_html(os.path.join(output_dir, f"components_vs_{cap_type}.html"))

        # Print the cliff
        net = results["household_net_income"]
        diffs = np.diff(net)
        worst_idx = np.argmin(diffs)
        cap_at_cliff = results["capital_income"][worst_idx]
        drop = diffs[worst_idx]
        print(f"  Largest net income drop: ${drop:,.0f} at ~${cap_at_cliff:,.0f} {label}")

    print("Done! Charts saved to analysis/outputs/")
