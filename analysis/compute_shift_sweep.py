"""Sensitivity sweep of labor→capital shift at multiple magnitudes.

Runs the shift at 0%, 10%, 20%, 30%, 50%, 100% and records:
  - Net income Gini and market Gini
  - SPM poverty rate
  - Revenue decomposition: income tax, payroll, EITC, CTC, SNAP
"""

import json
import os
import numpy as np
from policyengine_us import Microsimulation

from .labor_capital_shift import CAPITAL_INCOME_VARS, YEAR, _apply_shift, _extract_results

SHIFT_LEVELS = [0.0, 0.10, 0.20, 0.30, 0.50, 1.00]
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "outputs", "shift_sweep.json")


def _revenue_components(sim):
    """Return raw revenue/cost totals (in dollars) for a sim/branch."""
    income_tax = float(sim.calculate("income_tax", map_to="household", period=YEAR).sum())
    payroll = float(
        sim.calculate("employee_social_security_tax", map_to="household", period=YEAR).sum()
        + sim.calculate("employee_medicare_tax", map_to="household", period=YEAR).sum()
    )
    eitc = float(sim.calculate("eitc", map_to="household", period=YEAR).sum())
    ctc = float(sim.calculate("ctc", map_to="household", period=YEAR).sum())
    snap = float(sim.calculate("snap", map_to="household", period=YEAR).sum())
    return {
        "income_tax": income_tax,
        "payroll": payroll,
        "eitc": eitc,
        "ctc": ctc,
        "snap": snap,
    }


def net_fiscal_impact(components, baseline_components):
    """Net revenue change vs baseline (positive = government gains)."""
    delta_income_tax = components["income_tax"] - baseline_components["income_tax"]
    delta_payroll = components["payroll"] - baseline_components["payroll"]
    # Increases in EITC/CTC/SNAP are costs (negative for government)
    delta_eitc = -(components["eitc"] - baseline_components["eitc"])
    delta_ctc = -(components["ctc"] - baseline_components["ctc"])
    delta_snap = -(components["snap"] - baseline_components["snap"])
    return {
        "income_tax_change": delta_income_tax,
        "payroll_change": delta_payroll,
        "eitc_change": delta_eitc,
        "ctc_change": delta_ctc,
        "snap_change": delta_snap,
        "total_change": delta_income_tax + delta_payroll + delta_eitc + delta_ctc + delta_snap,
    }


def main():
    print("=" * 60)
    print("LABOR→CAPITAL SHIFT SWEEP")
    print("=" * 60)

    baseline = Microsimulation()

    # Create all branches BEFORE computing any downstream variables
    branches = {}
    for pct in SHIFT_LEVELS:
        if pct == 0.0:
            continue
        name = f"sweep_{int(pct * 100)}"
        print(f"Setting up {int(pct * 100)}% shift branch...")
        branch, freed = _apply_shift(baseline, name, pct)
        branches[pct] = branch

    # Now compute downstream variables
    print("\nComputing baseline metrics...")
    base_metrics = _extract_results(baseline, "Baseline")
    base_rev = _revenue_components(baseline)

    scenarios = []

    # Baseline (0% shift)
    scenarios.append({
        "shift_pct": 0,
        "label": "Baseline",
        "net_gini": base_metrics["net_gini"],
        "market_gini": base_metrics["market_gini"],
        "spm_poverty_rate": base_metrics["spm_poverty_rate"],
        "fed_revenue_b": base_metrics["fed_revenue"] / 1e9,
        "revenue_change_b": 0.0,
        "income_tax_change_b": 0.0,
        "payroll_change_b": 0.0,
        "eitc_change_b": 0.0,
        "ctc_change_b": 0.0,
        "snap_change_b": 0.0,
    })

    for pct in SHIFT_LEVELS:
        if pct == 0.0:
            continue
        branch = branches[pct]
        label = f"{int(pct * 100)}% shift"
        print(f"\nComputing {label} metrics...")

        metrics = _extract_results(branch, label)
        rev = _revenue_components(branch)
        delta = net_fiscal_impact(rev, base_rev)

        scenarios.append({
            "shift_pct": int(pct * 100),
            "label": label,
            "net_gini": metrics["net_gini"],
            "market_gini": metrics["market_gini"],
            "spm_poverty_rate": metrics["spm_poverty_rate"],
            "fed_revenue_b": metrics["fed_revenue"] / 1e9,
            "revenue_change_b": delta["total_change"] / 1e9,
            "income_tax_change_b": delta["income_tax_change"] / 1e9,
            "payroll_change_b": delta["payroll_change"] / 1e9,
            "eitc_change_b": delta["eitc_change"] / 1e9,
            "ctc_change_b": delta["ctc_change"] / 1e9,
            "snap_change_b": delta["snap_change"] / 1e9,
        })

        print(f"  Net Gini: {metrics['net_gini']:.4f}  Market Gini: {metrics['market_gini']:.4f}")
        print(f"  Poverty: {metrics['spm_poverty_rate']:.2%}")
        print(f"  Revenue change: ${delta['total_change']/1e9:+.1f}B")

    result = {"year": YEAR, "scenarios": scenarios}

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {OUTPUT_PATH}")

    # Print summary table
    print("\n" + "=" * 75)
    print(f"{'Shift':>7} {'Market Gini':>12} {'Net Gini':>10} {'Poverty':>9} {'Rev Chg':>10}")
    print("-" * 75)
    for s in scenarios:
        print(
            f"{s['shift_pct']:>6}%"
            f"  {s['market_gini']:.4f}"
            f"  {s['net_gini']:.4f}"
            f"  {s['spm_poverty_rate']:.2%}"
            f"  ${s['revenue_change_b']:>+.1f}B"
        )


if __name__ == "__main__":
    main()
