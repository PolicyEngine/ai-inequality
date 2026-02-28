"""Diagnose why revenue flips positive despite employment MTR > capital MTR.

Computes the implied effective rate on ADDED capital income directly:
  effective_rate = income_tax_delta / capital_income_added

Then compares to the 28.5% dollar-weighted LTCG MTR to see if the
marginal estimate undershoots the realized rate at large shifts.
"""

import numpy as np
from policyengine_us import Microsimulation
from .constants import CAPITAL_INCOME_VARS, YEAR
from .labor_capital_shift import _apply_shift

SHIFTS = [0.10, 0.20, 0.30, 0.50, 1.00]


def main():
    print("=" * 65)
    print("EFFECTIVE RATE ON ADDED CAPITAL INCOME vs DOLLAR-WEIGHTED MTR")
    print("=" * 65)

    baseline = Microsimulation()

    # Set up all branches before computing downstream
    branches = {}
    freed_amounts = {}
    for pct in SHIFTS:
        branch, freed = _apply_shift(baseline, f"diag_{int(pct*100)}", pct)
        branches[pct] = branch
        freed_amounts[pct] = freed

    # Baseline income tax
    base_income_tax = float(
        baseline.calculate("income_tax", map_to="household", period=YEAR).sum()
    )

    # Total positive capital income added at each shift level
    cap_positive_totals = {}
    for var in CAPITAL_INCOME_VARS:
        vals = baseline.calculate(var, period=YEAR)
        raw = np.array(vals)
        w = np.array(vals.weights)
        cap_positive_totals[var] = float((np.where(raw >= 0, raw, 0) * w).sum())
    total_positive_cap = sum(cap_positive_totals.values())

    print(f"\nBaseline income tax:       ${base_income_tax/1e9:.1f}B")
    print(f"Total positive capital:    ${total_positive_cap/1e9:.1f}B")
    print(f"Dollar-weighted LTCG MTR:  28.5%  (from compute_mtrs.py)")
    print(f"Dollar-weighted emp MTR:   32.8%  (from compute_mtrs.py)")

    print(f"\n{'Shift':>6} {'Capital added':>14} {'IT delta':>10} "
          f"{'Payroll delta':>14} {'Eff rate on cap':>16} {'Net rev':>10}")
    print("-" * 75)

    for pct in SHIFTS:
        branch = branches[pct]
        freed = freed_amounts[pct]

        # Income tax delta
        shift_income_tax = float(
            branch.calculate("income_tax", map_to="household", period=YEAR).sum()
        )
        it_delta = shift_income_tax - base_income_tax

        # Payroll delta
        base_payroll = float(
            baseline.calculate("employee_social_security_tax", map_to="household", period=YEAR).sum()
            + baseline.calculate("employee_medicare_tax", map_to="household", period=YEAR).sum()
        )
        shift_payroll = float(
            branch.calculate("employee_social_security_tax", map_to="household", period=YEAR).sum()
            + branch.calculate("employee_medicare_tax", map_to="household", period=YEAR).sum()
        )
        payroll_delta = shift_payroll - base_payroll

        # Capital added: same logic as _apply_shift, but compute weighted total added
        capital_added = 0.0
        for var in CAPITAL_INCOME_VARS:
            original = baseline.calculate(var, period=YEAR)
            raw = np.array(original)
            w = np.array(original.weights)
            pos_total = cap_positive_totals[var]
            if pos_total > 0 and total_positive_cap > 0:
                share = pos_total / total_positive_cap
                scale = 1 + (share * freed) / pos_total
                added = float((np.where(raw >= 0, raw * (scale - 1), 0) * w).sum())
                capital_added += added

        # Effective income tax rate on added capital
        eff_rate = it_delta / capital_added if capital_added > 0 else float("nan")

        # Net revenue (income tax + payroll, ignoring benefits for simplicity)
        net_rev = it_delta + payroll_delta

        print(
            f"{int(pct*100):>5}%"
            f"  ${capital_added/1e9:>11.1f}B"
            f"  ${it_delta/1e9:>+8.1f}B"
            f"  ${payroll_delta/1e9:>+11.1f}B"
            f"  {eff_rate:>15.1%}"
            f"  ${net_rev/1e9:>+8.1f}B"
        )

    print(f"\nNote: 'Eff rate on cap' = income_tax_delta / capital_added.")
    print(f"If > 28.5%, the realized rate exceeds the marginal MTR estimate.")
    print(f"If ≈ 28.5%, the MTR correctly predicts the income tax response;")
    print(f"  the flip is purely mechanical (payroll loss < income tax gain).")


if __name__ == "__main__":
    main()
