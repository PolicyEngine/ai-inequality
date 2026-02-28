"""Diagnose why labor→capital shift increases revenue.

Quick script to check:
1. Total wages lost vs capital income gained (should be equal)
2. Breakdown of revenue change by component (income tax, EITC, CTC, etc.)
3. Revenue change by income decile
"""

import numpy as np
from policyengine_us import Microsimulation

from .constants import YEAR, CAPITAL_INCOME_VARS

SHIFT_PCT = 0.50


def main():
    print("Running baseline...")
    baseline = Microsimulation()

    # Create branch
    branch = baseline.get_branch("shift_50")

    emp_income = baseline.calculate("employment_income", period=YEAR)
    se_income = baseline.calculate("self_employment_income", period=YEAR)

    wage_cut = emp_income * SHIFT_PCT
    se_cut = se_income * SHIFT_PCT
    branch.set_input("employment_income", YEAR, emp_income - wage_cut)
    branch.set_input("self_employment_income", YEAR, se_income - se_cut)

    total_freed = float(wage_cut.sum() + se_cut.sum())
    print(f"\nTotal labor income freed: ${total_freed/1e9:,.1f}B")

    # Redistribute to capital using positive-only weighted totals
    cap_positive_totals = {}
    for var in CAPITAL_INCOME_VARS:
        vals = baseline.calculate(var, period=YEAR)
        raw = np.array(vals)
        w = np.array(vals.weights)
        cap_positive_totals[var] = float((np.where(raw >= 0, raw, 0) * w).sum())

    total_positive_cap = sum(cap_positive_totals.values())
    total_added = 0.0

    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        raw = np.array(original)
        w = np.array(original.weights)
        pos_total = cap_positive_totals[var]
        if pos_total > 0 and total_positive_cap > 0:
            share = pos_total / total_positive_cap
            scale = 1 + (share * total_freed) / pos_total
            scaled = np.where(raw >= 0, raw * scale, raw)
            branch.set_input(var, YEAR, scaled)
            added = float(((scaled - raw) * w).sum())
            total_added += added
            print(f"  {var}: +${added/1e9:,.1f}B (share={share:.1%}, scale={scale:.2f}x)")

    print(f"Total capital income added: ${total_added/1e9:,.1f}B")
    print(f"Difference (freed - added): ${(total_freed - total_added)/1e9:,.1f}B")

    # Revenue components
    print("\n" + "=" * 70)
    print("REVENUE COMPONENT BREAKDOWN")
    print("=" * 70)

    components = [
        ("income_tax", "household"),
        ("eitc", "household"),
        ("ctc", "household"),
        ("additional_ctc", "household"),
        ("snap", "spm_unit"),
    ]

    for var, entity in components:
        try:
            base_val = baseline.calculate(var, map_to="household", period=YEAR)
            shift_val = branch.calculate(var, map_to="household", period=YEAR)
            base_total = float(base_val.sum())
            shift_total = float(shift_val.sum())
            diff = shift_total - base_total
            print(f"  {var:30s}  Base: ${base_total/1e9:>8,.1f}B  "
                  f"Shift: ${shift_total/1e9:>8,.1f}B  "
                  f"Change: ${diff/1e9:>+8,.1f}B")
        except Exception as e:
            print(f"  {var:30s}  Error: {e}")

    # Check who loses/gains
    print("\n" + "=" * 70)
    print("WHO LOSES WAGES vs WHO GAINS CAPITAL INCOME")
    print("=" * 70)

    base_market = baseline.calculate("household_market_income", period=YEAR)
    base_net = baseline.calculate("household_net_income", period=YEAR)
    shift_net = branch.calculate("household_net_income", period=YEAR)

    weights = np.array(base_market.weights)
    values = np.array(base_market.values)

    # Sort by baseline market income
    idx = np.argsort(values)
    sorted_weights = weights[idx]
    sorted_base_net = np.array(base_net.values)[idx]
    sorted_shift_net = np.array(shift_net.values)[idx]

    cumw = np.cumsum(sorted_weights)
    total_w = cumw[-1]

    print(f"\n{'Decile':>8s}  {'Avg base net':>14s}  {'Avg shift net':>14s}  {'Change':>12s}")
    for i in range(10):
        lower = i / 10 * total_w
        upper = (i + 1) / 10 * total_w
        mask = (cumw > lower) & (cumw <= upper)
        if i == 0:
            mask = cumw <= upper

        w = sorted_weights[mask]
        w_sum = w.sum()
        if w_sum == 0:
            continue

        avg_base = (sorted_base_net[mask] * w).sum() / w_sum
        avg_shift = (sorted_shift_net[mask] * w).sum() / w_sum
        change = avg_shift - avg_base
        print(f"  D{i+1:>2d}      ${avg_base:>12,.0f}  ${avg_shift:>12,.0f}  ${change:>+10,.0f}")


if __name__ == "__main__":
    main()
