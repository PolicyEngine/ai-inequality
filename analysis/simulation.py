"""Microsimulation scenarios for capital income doubling analysis."""

import numpy as np
import pandas as pd
from policyengine_us import Microsimulation
from policyengine_core.reforms import Reform

from .metrics import compute_decile_shares

YEAR = 2026

CAPITAL_INCOME_VARS = [
    "long_term_capital_gains",
    "short_term_capital_gains",
    "taxable_interest_income",
    "qualified_dividend_income",
    "non_qualified_dividend_income",
    "rental_income",
]


def _extract_results(sim, label):
    """Extract standard metrics from a simulation or branch.

    Uses MicroSeries.gini() from microdf for Gini calculation —
    the same implementation used throughout PolicyEngine.
    """
    net_income = sim.calculate("household_net_income", period=YEAR)
    market_income = sim.calculate("household_market_income", period=YEAR)
    income_tax = sim.calculate("income_tax", map_to="household", period=YEAR)
    state_income_tax = sim.calculate("state_income_tax", map_to="household", period=YEAR)
    in_poverty = sim.calculate("spm_unit_is_in_spm_poverty", map_to="person", period=YEAR)

    return {
        "label": label,
        "mean_net_income": float(net_income.mean()),
        "market_gini": float(market_income.gini()),
        "net_gini": float(net_income.gini()),
        "spm_poverty_rate": float(in_poverty.mean()),
        "fed_revenue": float(income_tax.sum()),
        "state_revenue": float(state_income_tax.sum()),
        "decile_shares": compute_decile_shares(
            np.array(net_income.values), np.array(net_income.weights)
        ),
        # Raw MicroSeries for downstream use (charts, state breakdown)
        "_net_income": net_income,
        "_market_income": market_income,
        "_income_tax": income_tax,
        "_state_income_tax": state_income_tax,
    }


def run_scenarios():
    """Run all three scenarios and return results dict.

    Returns:
        Dict with keys "baseline", "doubled", "ubi", each containing
        a results dict, plus "meta" with population/household counts
        and "state_summary" DataFrame.
    """
    print("Running baseline microsimulation...")
    baseline = Microsimulation()

    # Branch BEFORE computing downstream variables
    print("Creating doubled capital income branch...")
    doubled = baseline.get_branch("doubled_capital")
    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        doubled.set_input(var, YEAR, original * 2)

    weights = np.array(baseline.calculate("household_weight", period=YEAR))
    household_count_people = baseline.calculate("household_count_people", period=YEAR)
    total_population = float(household_count_people.sum())

    baseline_results = _extract_results(baseline, "Baseline")
    doubled_results = _extract_results(doubled, "Doubled capital")

    # State-level breakdown
    state_codes = np.array(baseline.calculate("state_code", period=YEAR))
    state_summary = _compute_state_summary(
        state_codes, weights,
        np.array(baseline_results["_income_tax"]),
        np.array(doubled_results["_income_tax"]),
        np.array(baseline_results["_state_income_tax"]),
        np.array(doubled_results["_state_income_tax"]),
        np.array(household_count_people),
    )

    # UBI scenario: recycle extra federal revenue as flat UBI
    extra_fed_revenue = doubled_results["fed_revenue"] - baseline_results["fed_revenue"]
    ubi_amount = extra_fed_revenue / total_population
    print(f"UBI amount: ${ubi_amount:,.2f}/person/year (${ubi_amount/12:,.2f}/month)")

    reform = Reform.from_dict({
        "gov.contrib.ubi_center.basic_income.amount.person.flat": {
            f"{YEAR}-01-01.2100-12-31": round(ubi_amount, 2)
        },
    }, country_id="us")

    ubi_sim = Microsimulation(reform=reform)
    ubi_branch = ubi_sim.get_branch("doubled_capital_ubi")
    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        ubi_branch.set_input(var, YEAR, original * 2)

    ubi_results = _extract_results(ubi_branch, "Doubled + UBI")
    ubi_results["ubi_per_person"] = ubi_amount

    return {
        "baseline": baseline_results,
        "doubled": doubled_results,
        "ubi": ubi_results,
        "meta": {
            "year": YEAR,
            "total_households": float(weights.sum()),
            "total_population": total_population,
            "extra_fed_revenue": extra_fed_revenue,
            "extra_state_revenue": doubled_results["state_revenue"] - baseline_results["state_revenue"],
        },
        "state_summary": state_summary,
    }


def _compute_state_summary(state_codes, weights, baseline_fed, doubled_fed,
                           baseline_state, doubled_state, hh_count_people):
    """Compute state-level revenue breakdown."""
    df = pd.DataFrame({
        "state": state_codes,
        "weight": weights,
        "extra_fed": doubled_fed - baseline_fed,
        "extra_state": doubled_state - baseline_state,
        "household_count_people": hh_count_people,
    })
    df["extra_total"] = df["extra_fed"] + df["extra_state"]

    summary = df.groupby("state").apply(
        lambda g: pd.Series({
            "extra_fed_revenue": (g.extra_fed * g.weight).sum(),
            "extra_state_revenue": (g.extra_state * g.weight).sum(),
            "extra_total_revenue": (g.extra_total * g.weight).sum(),
            "weighted_households": g.weight.sum(),
            "weighted_population": (g.household_count_people * g.weight).sum(),
        }),
        include_groups=False,
    ).reset_index()

    summary["extra_per_capita"] = summary["extra_total_revenue"] / summary["weighted_population"]
    return summary
