"""
Capital Income Doubling Analysis
================================
Simulates an AI-driven economic scenario where capital income doubles
(representing AI increasing returns to capital) while labor income stays
constant. Measures effects on inequality and tax revenue, then explores
using the extra revenue to fund a UBI.
"""

# %% Section 1: Setup & imports
from policyengine_us import Microsimulation
from policyengine_core.reforms import Reform
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os

YEAR = 2026
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CAPITAL_INCOME_VARS = [
    "long_term_capital_gains",
    "short_term_capital_gains",
    "taxable_interest_income",
    "qualified_dividend_income",
    "non_qualified_dividend_income",
    "rental_income",
]

# %% Section 2: Baseline microsimulation & branching
# IMPORTANT: Create branches BEFORE computing any downstream variables,
# otherwise cached values won't recalculate on the branch.
print("Running baseline microsimulation...")
baseline = Microsimulation()

# Create branch before computing any downstream vars
print("Creating doubled capital income branch...")
doubled = baseline.get_branch("doubled_capital")
for var in CAPITAL_INCOME_VARS:
    original = baseline.calculate(var, period=YEAR)
    doubled.set_input(var, YEAR, original * 2)

# MicroSeries — .sum() and .mean() are automatically weighted
household_net_income = baseline.calculate("household_net_income", period=YEAR)
household_market_income = baseline.calculate("household_market_income", period=YEAR)
income_tax = baseline.calculate("income_tax", map_to="household", period=YEAR)
state_income_tax = baseline.calculate("state_income_tax", map_to="household", period=YEAR)
household_count_people = baseline.calculate("household_count_people", period=YEAR)
in_spm_poverty = baseline.calculate("spm_unit_is_in_spm_poverty", map_to="person", period=YEAR)

# For state breakdown, we need raw arrays
state_codes = np.array(baseline.calculate("state_code", period=YEAR))
weights = np.array(baseline.calculate("household_weight", period=YEAR))

total_households = weights.sum()
total_population = household_count_people.sum()

print(f"  Households: {total_households:,.0f}")
print(f"  Population: {total_population:,.0f}")
print(f"  Mean household net income: ${household_net_income.mean():,.0f}")

# %% Section 3: Doubled capital income results
print("\nComputing doubled capital income results...")
doubled_net_income = doubled.calculate("household_net_income", period=YEAR)
doubled_market_income = doubled.calculate("household_market_income", period=YEAR)
doubled_income_tax = doubled.calculate("income_tax", map_to="household", period=YEAR)
doubled_state_income_tax = doubled.calculate("state_income_tax", map_to="household", period=YEAR)
doubled_in_spm_poverty = doubled.calculate("spm_unit_is_in_spm_poverty", map_to="person", period=YEAR)

print(f"  Mean doubled household net income: ${doubled_net_income.mean():,.0f}")


# %% Section 4: Inequality metrics
def weighted_gini(series):
    """Compute the Gini coefficient from a MicroSeries."""
    values = np.array(series.values, dtype=float)
    w = np.array(series.weights, dtype=float)

    mask = w > 0
    values = values[mask]
    w = w[mask]

    sorted_indices = np.argsort(values)
    values = values[sorted_indices]
    w = w[sorted_indices]

    cumw = np.cumsum(w)
    total_weight = cumw[-1]
    cumwv = np.cumsum(values * w)
    total_wv = cumwv[-1]

    if total_wv == 0:
        return 0.0

    gini = 1 - 2 * np.sum(cumwv * w) / (total_weight * total_wv) + 1 / total_weight
    return float(gini)


def compute_decile_shares(series, n=10):
    """Compute income shares by quantile from a MicroSeries."""
    incomes = np.array(series.values, dtype=float)
    w = np.array(series.weights, dtype=float)

    sorted_idx = np.argsort(incomes)
    incomes = incomes[sorted_idx]
    w = w[sorted_idx]

    cumw = np.cumsum(w)
    total_w = cumw[-1]

    shares = []
    for i in range(n):
        lower = i / n * total_w
        upper = (i + 1) / n * total_w
        mask = (cumw > lower) & (cumw <= upper)
        if i == 0:
            mask = cumw <= upper
        decile_income = (incomes[mask] * w[mask]).sum()
        shares.append(decile_income)

    total = sum(shares)
    if total > 0:
        shares = [s / total for s in shares]
    return shares


def lorenz_curve(series, n_points=100):
    """Compute Lorenz curve points from a MicroSeries."""
    incomes = np.array(series.values, dtype=float)
    w = np.array(series.weights, dtype=float)

    sorted_idx = np.argsort(incomes)
    incomes = incomes[sorted_idx]
    w = w[sorted_idx]

    cumw = np.cumsum(w)
    cumwv = np.cumsum(incomes * w)

    total_w = cumw[-1]
    total_wv = cumwv[-1]

    pop_fracs = np.concatenate([[0], cumw / total_w])
    if total_wv > 0:
        income_fracs = np.concatenate([[0], cumwv / total_wv])
    else:
        income_fracs = np.concatenate([[0], cumw / total_w])

    x = np.linspace(0, 1, n_points)
    y = np.interp(x, pop_fracs, income_fracs)
    return x, y


print("\nComputing inequality metrics...")

baseline_market_gini = weighted_gini(household_market_income)
baseline_net_gini = weighted_gini(household_net_income)
baseline_poverty = float(in_spm_poverty.mean())
baseline_decile_shares = compute_decile_shares(household_net_income)

doubled_market_gini = weighted_gini(doubled_market_income)
doubled_net_gini = weighted_gini(doubled_net_income)
doubled_poverty = float(doubled_in_spm_poverty.mean())
doubled_decile_shares = compute_decile_shares(doubled_net_income)

print(f"  Baseline market Gini: {baseline_market_gini:.4f}")
print(f"  Baseline net Gini:    {baseline_net_gini:.4f}")
print(f"  Doubled market Gini:  {doubled_market_gini:.4f}")
print(f"  Doubled net Gini:     {doubled_net_gini:.4f}")
print(f"  Baseline SPM poverty: {baseline_poverty:.2%}")
print(f"  Doubled SPM poverty:  {doubled_poverty:.2%}")

# %% Section 5: Tax revenue impact
print("\nComputing tax revenue impact...")

baseline_fed_revenue = float(income_tax.sum())
doubled_fed_revenue = float(doubled_income_tax.sum())
extra_fed_revenue = doubled_fed_revenue - baseline_fed_revenue

baseline_state_revenue = float(state_income_tax.sum())
doubled_state_revenue = float(doubled_state_income_tax.sum())
extra_state_revenue = doubled_state_revenue - baseline_state_revenue

extra_total_revenue = extra_fed_revenue + extra_state_revenue

print(f"  Baseline federal income tax revenue: ${baseline_fed_revenue:,.0f}")
print(f"  Doubled federal income tax revenue:  ${doubled_fed_revenue:,.0f}")
print(f"  Extra federal revenue:               ${extra_fed_revenue:,.0f}")
print(f"  Extra state revenue:                 ${extra_state_revenue:,.0f}")
print(f"  Extra total revenue:                 ${extra_total_revenue:,.0f}")

# %% Section 6: State-level breakdown
print("\nComputing state-level breakdown...")

# Use raw numpy arrays for the grouped DataFrame
state_df = pd.DataFrame({
    "state": state_codes,
    "weight": weights,
    "baseline_fed_tax": np.array(income_tax),
    "doubled_fed_tax": np.array(doubled_income_tax),
    "baseline_state_tax": np.array(state_income_tax),
    "doubled_state_tax": np.array(doubled_state_income_tax),
    "household_count_people": np.array(household_count_people),
})

state_df["extra_fed"] = state_df["doubled_fed_tax"] - state_df["baseline_fed_tax"]
state_df["extra_state"] = state_df["doubled_state_tax"] - state_df["baseline_state_tax"]
state_df["extra_total"] = state_df["extra_fed"] + state_df["extra_state"]

state_summary = state_df.groupby("state").apply(
    lambda g: pd.Series({
        "extra_fed_revenue": (g.extra_fed * g.weight).sum(),
        "extra_state_revenue": (g.extra_state * g.weight).sum(),
        "extra_total_revenue": (g.extra_total * g.weight).sum(),
        "weighted_households": g.weight.sum(),
        "weighted_population": (g.household_count_people * g.weight).sum(),
    })
).reset_index()

state_summary["extra_per_capita"] = (
    state_summary["extra_total_revenue"] / state_summary["weighted_population"]
)

print(f"  States with data: {len(state_summary)}")
print("  Top 5 states by extra total revenue:")
top_5 = state_summary.nlargest(5, "extra_total_revenue")
for _, row in top_5.iterrows():
    print(f"    {row['state']}: ${row['extra_total_revenue']:,.0f} "
          f"(${row['extra_per_capita']:,.0f}/capita)")

# %% Section 7: UBI funded by extra revenue
print("\nComputing UBI scenario...")

ubi_amount = extra_fed_revenue / total_population
print(f"  Extra federal revenue: ${extra_fed_revenue:,.0f}")
print(f"  UBI amount per person: ${ubi_amount:,.2f}/year")

ubi_reform_dict = {
    "gov.contrib.ubi_center.basic_income.amount.person.flat": {
        f"{YEAR}-01-01.2100-12-31": round(ubi_amount, 2)
    },
}

reform = Reform.from_dict(ubi_reform_dict, country_id="us")
ubi_sim = Microsimulation(reform=reform)

# Create branch BEFORE computing anything, then set doubled capital income
ubi_branch = ubi_sim.get_branch("doubled_capital_ubi")
for var in CAPITAL_INCOME_VARS:
    original = baseline.calculate(var, period=YEAR)
    ubi_branch.set_input(var, YEAR, original * 2)

ubi_net_income = ubi_branch.calculate("household_net_income", period=YEAR)
ubi_market_income = ubi_branch.calculate("household_market_income", period=YEAR)
ubi_income_tax = ubi_branch.calculate("income_tax", map_to="household", period=YEAR)
ubi_in_spm_poverty = ubi_branch.calculate("spm_unit_is_in_spm_poverty", map_to="person", period=YEAR)

ubi_market_gini = weighted_gini(ubi_market_income)
ubi_net_gini = weighted_gini(ubi_net_income)
ubi_poverty = float(ubi_in_spm_poverty.mean())
ubi_decile_shares = compute_decile_shares(ubi_net_income)
ubi_fed_revenue = float(ubi_income_tax.sum())

print(f"  UBI net Gini:    {ubi_net_gini:.4f}")
print(f"  UBI SPM poverty: {ubi_poverty:.2%}")

# %% Section 8: Summary comparison table
print("\n" + "=" * 70)
print("SUMMARY COMPARISON")
print("=" * 70)

summary = pd.DataFrame({
    "Metric": [
        "Market income Gini",
        "Net income Gini",
        "SPM poverty rate",
        "Federal income tax revenue",
        "Top decile income share",
        "Bottom decile income share",
    ],
    "Baseline": [
        f"{baseline_market_gini:.4f}",
        f"{baseline_net_gini:.4f}",
        f"{baseline_poverty:.2%}",
        f"${baseline_fed_revenue:,.0f}",
        f"{baseline_decile_shares[9]:.2%}",
        f"{baseline_decile_shares[0]:.2%}",
    ],
    "Doubled capital": [
        f"{doubled_market_gini:.4f}",
        f"{doubled_net_gini:.4f}",
        f"{doubled_poverty:.2%}",
        f"${doubled_fed_revenue:,.0f}",
        f"{doubled_decile_shares[9]:.2%}",
        f"{doubled_decile_shares[0]:.2%}",
    ],
    "Doubled + UBI": [
        f"{ubi_market_gini:.4f}",
        f"{ubi_net_gini:.4f}",
        f"{ubi_poverty:.2%}",
        f"${ubi_fed_revenue:,.0f}",
        f"{ubi_decile_shares[9]:.2%}",
        f"{ubi_decile_shares[0]:.2%}",
    ],
})

print(summary.to_string(index=False))

summary_numeric = pd.DataFrame({
    "metric": [
        "market_gini", "net_gini", "spm_poverty_rate",
        "fed_revenue", "top_decile_share", "bottom_decile_share",
        "ubi_per_person",
    ],
    "baseline": [
        baseline_market_gini, baseline_net_gini, baseline_poverty,
        baseline_fed_revenue, baseline_decile_shares[9], baseline_decile_shares[0],
        0,
    ],
    "doubled_capital": [
        doubled_market_gini, doubled_net_gini, doubled_poverty,
        doubled_fed_revenue, doubled_decile_shares[9], doubled_decile_shares[0],
        0,
    ],
    "doubled_plus_ubi": [
        ubi_market_gini, ubi_net_gini, ubi_poverty,
        ubi_fed_revenue, ubi_decile_shares[9], ubi_decile_shares[0],
        ubi_amount,
    ],
})

# %% Section 9: Visualizations
print("\nGenerating visualizations...")

# 9a: Lorenz curves
lorenz_fig = go.Figure()
for label, series in [
    ("Baseline", household_net_income),
    ("Doubled capital", doubled_net_income),
    ("Doubled + UBI", ubi_net_income),
]:
    x, y = lorenz_curve(series)
    lorenz_fig.add_trace(go.Scatter(x=x, y=y, name=label, mode="lines"))
lorenz_fig.add_trace(
    go.Scatter(x=[0, 1], y=[0, 1], name="Perfect equality",
               mode="lines", line=dict(dash="dash", color="gray"))
)
lorenz_fig.update_layout(
    title="Lorenz curves: net income distribution",
    xaxis_title="Cumulative population share",
    yaxis_title="Cumulative income share",
    width=800, height=600,
)

# 9b: Decile income shares
decile_labels = [f"D{i+1}" for i in range(10)]
decile_fig = go.Figure()
decile_fig.add_trace(go.Bar(name="Baseline", x=decile_labels, y=baseline_decile_shares))
decile_fig.add_trace(go.Bar(name="Doubled capital", x=decile_labels, y=doubled_decile_shares))
decile_fig.add_trace(go.Bar(name="Doubled + UBI", x=decile_labels, y=ubi_decile_shares))
decile_fig.update_layout(
    title="Net income shares by decile",
    xaxis_title="Income decile",
    yaxis_title="Share of total net income",
    yaxis_tickformat=".1%",
    barmode="group",
    width=800, height=500,
)

# 9c: Gini comparison bar chart
gini_fig = go.Figure()
scenarios = ["Baseline", "Doubled capital", "Doubled + UBI"]
market_ginis = [baseline_market_gini, doubled_market_gini, ubi_market_gini]
net_ginis = [baseline_net_gini, doubled_net_gini, ubi_net_gini]
gini_fig.add_trace(go.Bar(name="Market Gini", x=scenarios, y=market_ginis))
gini_fig.add_trace(go.Bar(name="Net Gini", x=scenarios, y=net_ginis))
gini_fig.update_layout(
    title="Gini coefficients across scenarios",
    yaxis_title="Gini coefficient",
    barmode="group",
    width=800, height=500,
)

# 9d: State-level extra revenue map
state_map_fig = px.choropleth(
    state_summary,
    locations="state",
    locationmode="USA-states",
    color="extra_per_capita",
    scope="usa",
    color_continuous_scale="Reds",
    title="Extra tax revenue per capita by state (doubled capital income)",
    labels={"extra_per_capita": "Extra revenue/capita ($)"},
)
state_map_fig.update_layout(width=900, height=600)

# Save as HTML
lorenz_fig.write_html(os.path.join(OUTPUT_DIR, "lorenz_curves.html"))
decile_fig.write_html(os.path.join(OUTPUT_DIR, "decile_shares.html"))
gini_fig.write_html(os.path.join(OUTPUT_DIR, "gini_comparison.html"))
state_map_fig.write_html(os.path.join(OUTPUT_DIR, "state_revenue_map.html"))

print("  Saved 4 interactive charts to analysis/outputs/")

# %% Section 10: Export results
print("\nExporting CSV results...")

summary_numeric.to_csv(os.path.join(OUTPUT_DIR, "summary_metrics.csv"), index=False)
state_summary.to_csv(os.path.join(OUTPUT_DIR, "state_breakdown.csv"), index=False)

decile_df = pd.DataFrame({
    "decile": list(range(1, 11)),
    "baseline_share": baseline_decile_shares,
    "doubled_share": doubled_decile_shares,
    "ubi_share": ubi_decile_shares,
})
decile_df.to_csv(os.path.join(OUTPUT_DIR, "decile_shares.csv"), index=False)

print("  Saved summary_metrics.csv, state_breakdown.csv, decile_shares.csv")
print("\nDone!")
