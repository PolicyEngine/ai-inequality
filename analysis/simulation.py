"""Microsimulation scenarios for capital income doubling analysis."""

import numpy as np
import pandas as pd
from policyengine_us import Microsimulation
from policyengine_core.reforms import Reform

from .constants import YEAR, CAPITAL_INCOME_VARS
from .metrics import extract_results as _extract_results


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
    # Only scale positive capital income — scaling losses is an artifact
    # that distorts bottom-decile results without modeling anything real.
    print("Creating doubled capital income branch...")
    doubled = baseline.get_branch("doubled_capital")
    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        vals = np.array(original)
        doubled.set_input(var, YEAR, np.where(vals >= 0, vals * 2, vals))

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
        vals = np.array(original)
        ubi_branch.set_input(var, YEAR, np.where(vals >= 0, vals * 2, vals))

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
