"""Decompose what drives revenue change in labor→capital shift.

The shift shows revenue INCREASING despite employment having a higher
dollar-weighted MTR than capital. This script investigates why:
  1. Decompose revenue change into income tax vs benefit reductions
  2. Check EITC specifically (known cliff at investment income ~$12K)
  3. Compare who loses wages vs who gains capital income
  4. Sanity-check the STCG 72% MTR
"""

import numpy as np
from policyengine_us import Microsimulation
from .labor_capital_shift import CAPITAL_INCOME_VARS, YEAR, _apply_shift

SHIFT_PCT = 0.50


def main():
    print("=" * 70)
    print("REVENUE DECOMPOSITION: 50% LABOR→CAPITAL SHIFT")
    print("=" * 70)

    baseline = Microsimulation()
    branch, total_freed = _apply_shift(baseline, "shift_50", SHIFT_PCT)
    print(f"\nTotal freed (wages + employer payroll): ${total_freed/1e12:.2f}T")

    # --- Revenue decomposition ---
    print("\n--- Revenue decomposition ---")

    base_income_tax = float(baseline.calculate("income_tax", map_to="household", period=YEAR).sum())
    shift_income_tax = float(branch.calculate("income_tax", map_to="household", period=YEAR).sum())

    base_ee_payroll = float(baseline.calculate("employee_social_security_tax", map_to="household", period=YEAR).sum()
                           + baseline.calculate("employee_medicare_tax", map_to="household", period=YEAR).sum())
    shift_ee_payroll = float(branch.calculate("employee_social_security_tax", map_to="household", period=YEAR).sum()
                            + branch.calculate("employee_medicare_tax", map_to="household", period=YEAR).sum())
    base_er_payroll = float(baseline.calculate("employer_social_security_tax", map_to="household", period=YEAR).sum()
                           + baseline.calculate("employer_medicare_tax", map_to="household", period=YEAR).sum())
    shift_er_payroll = float(branch.calculate("employer_social_security_tax", map_to="household", period=YEAR).sum()
                            + branch.calculate("employer_medicare_tax", map_to="household", period=YEAR).sum())

    base_eitc = float(baseline.calculate("eitc", map_to="household", period=YEAR).sum())
    shift_eitc = float(branch.calculate("eitc", map_to="household", period=YEAR).sum())

    base_ctc = float(baseline.calculate("ctc", map_to="household", period=YEAR).sum())
    shift_ctc = float(branch.calculate("ctc", map_to="household", period=YEAR).sum())

    base_snap = float(baseline.calculate("snap", map_to="household", period=YEAR).sum())
    shift_snap = float(branch.calculate("snap", map_to="household", period=YEAR).sum())

    print(f"{'Component':<30} {'Baseline':>12} {'Shift':>12} {'Change':>12}")
    print("-" * 70)
    for label, b, s in [
        ("Federal income tax",    base_income_tax, shift_income_tax),
        ("Payroll tax (employee)", base_ee_payroll, shift_ee_payroll),
        ("Payroll tax (employer)", base_er_payroll, shift_er_payroll),
        ("EITC (negative)",       -base_eitc,      -shift_eitc),
        ("Child tax credit (neg)", -base_ctc,      -shift_ctc),
        ("SNAP (negative)",       -base_snap,      -shift_snap),
    ]:
        chg = s - b
        print(f"{label:<30} ${b/1e9:>10,.0f}B ${s/1e9:>10,.0f}B ${chg/1e9:>+10,.0f}B")

    print()
    net_income_tax_chg = shift_income_tax - base_income_tax
    net_ee_payroll_chg = shift_ee_payroll - base_ee_payroll
    net_er_payroll_chg = shift_er_payroll - base_er_payroll
    net_eitc_chg = -(shift_eitc - base_eitc)  # reduction in EITC = revenue gain
    net_ctc_chg = -(shift_ctc - base_ctc)
    net_snap_chg = -(shift_snap - base_snap)
    total_chg = (net_income_tax_chg + net_ee_payroll_chg + net_er_payroll_chg
                 + net_eitc_chg + net_ctc_chg + net_snap_chg)
    print(f"{'Total net revenue change':<30} ${total_chg/1e9:>+10,.0f}B")

    # --- STCG sanity check ---
    print("\n--- STCG MTR sanity check ---")
    stcg_branch = baseline.get_branch("mtr_stcg")
    stcg_orig = baseline.calculate("short_term_capital_gains", period=YEAR)
    raw = np.array(stcg_orig)
    w = np.array(stcg_orig.weights)
    total_stcg = float((raw * w).sum())
    stcg_branch.set_input("short_term_capital_gains", YEAR, raw * 1.01)

    base_net = float(baseline.calculate("household_net_income", period=YEAR).sum())
    stcg_net = float(stcg_branch.calculate("household_net_income", period=YEAR).sum())
    delta_net = stcg_net - base_net
    delta_gross = total_stcg * 0.01
    mtr = 1 - delta_net / delta_gross

    pw = baseline.calculate("person_weight", period=YEAR)
    n_nonzero_stcg = float((np.array(stcg_orig) > 0).sum())
    n_people = float(np.array(pw).sum())
    print(f"Total STCG (weighted): ${total_stcg/1e9:.1f}B")
    print(f"Microdata records with STCG > 0: {n_nonzero_stcg:,.0f} of {len(raw):,.0f}")
    print(f"Dollar-weighted MTR: {mtr:.1%}")
    print(f"Delta net income: ${delta_net/1e6:.1f}M on ${delta_gross/1e6:.1f}M gross bump")

    # --- Income distribution of who loses wages vs gains capital ---
    print("\n--- Who loses wages vs gains capital income? ---")
    hh_net = baseline.calculate("household_net_income", period=YEAR)
    hh_emp = baseline.calculate("employment_income", map_to="household", period=YEAR)
    hh_cap = sum(
        baseline.calculate(var, map_to="household", period=YEAR)
        for var in CAPITAL_INCOME_VARS
    )
    hh_w = baseline.calculate("household_weight", period=YEAR)

    raw_net = np.array(hh_net)
    raw_emp = np.array(hh_emp)
    raw_cap = np.array(hh_cap)
    raw_w = np.array(hh_w)

    # Sort by net income into deciles
    idx = np.argsort(raw_net)
    sorted_net = raw_net[idx]
    sorted_emp = raw_emp[idx]
    sorted_cap = raw_cap[idx]
    sorted_w = raw_w[idx]

    cum_w = np.cumsum(sorted_w)
    total_w = cum_w[-1]

    print(f"\n{'Decile':<10} {'Emp income':>12} {'Cap income':>12} {'Cap/Emp':>10}")
    print("-" * 50)
    for i in range(10):
        lower = i / 10 * total_w
        upper = (i + 1) / 10 * total_w
        mask = (cum_w > lower) & (cum_w <= upper)
        if i == 0:
            mask = cum_w <= upper
        emp_d = float((sorted_emp[mask] * sorted_w[mask]).sum()) / 1e9
        cap_d = float((sorted_cap[mask] * sorted_w[mask]).sum()) / 1e9
        ratio = cap_d / emp_d if emp_d > 0 else float("nan")
        print(f"D{i+1:<9} ${emp_d:>10.1f}B ${cap_d:>10.1f}B {ratio:>9.2f}x")


if __name__ == "__main__":
    main()
