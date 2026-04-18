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
from .constants import CAPITAL_INCOME_VARS, YEAR
from .labor_capital_shift import _apply_shift
from .fiscal import net_fiscal_impact, revenue_components

SHIFT_PCT = 0.50


def main():
    print("=" * 70)
    print("REVENUE DECOMPOSITION: 50% LABOR→CAPITAL SHIFT")
    print("=" * 70)

    baseline = Microsimulation()
    branch, total_freed = _apply_shift(baseline, "shift_50", SHIFT_PCT)
    print(f"\nTotal freed labor income: ${total_freed/1e12:.2f}T")

    # --- Revenue decomposition ---
    print("\n--- Revenue decomposition ---")

    base_rev = revenue_components(baseline)
    shift_rev = revenue_components(branch)
    delta = net_fiscal_impact(shift_rev, base_rev)

    print(f"{'Component':<40} {'Baseline':>12} {'Shift':>12} {'Change':>12}")
    print("-" * 82)
    # Non-overlapping aggregates (these sum to the total).
    for label, key, sign in [
        ("Fed income tax (before ref credits)",
         "fed_income_tax_before_refundable_credits", 1),
        ("  of which main rates",                "fed_income_tax_main_rates", 1),
        ("  of which capital gains tax",         "fed_capital_gains_tax", 1),
        ("  of which AMT",                       "fed_alternative_minimum_tax", 1),
        ("  of which NIIT",                      "fed_net_investment_income_tax", 1),
        ("  less nonrefundable credits",         "fed_nonrefundable_credits", 1),
        ("Employee payroll (SS)",                "employee_social_security_tax", 1),
        ("Employee payroll (Medicare)",          "employee_medicare_tax", 1),
        ("Employer payroll (SS)",                "employer_social_security_tax", 1),
        ("Employer payroll (Medicare)",          "employer_medicare_tax", 1),
        ("Self-employment tax",                  "self_employment_tax", 1),
        ("State tax before refundable credits",  "state_tax_before_refundable_credits", 1),
        ("Fed refundable credits (negative)",    "income_tax_refundable_credits", -1),
        ("  of which EITC",                      "eitc", -1),
        ("  of which refundable CTC",            "refundable_ctc", -1),
        ("State refundable credits (negative)",  "state_refundable_credits", -1),
        ("Benefits (negative)",                  "household_benefits", -1),
        ("  of which SNAP",                      "snap", -1),
        ("  of which SSI",                       "ssi", -1),
        ("  of which TANF",                      "tanf", -1),
        ("  of which health",                    "health_benefits", -1),
        ("  of which state",                     "state_benefits", -1),
    ]:
        b = base_rev[key] * sign
        s = shift_rev[key] * sign
        chg = s - b
        print(f"{label:<40} ${b/1e9:>10,.0f}B ${s/1e9:>10,.0f}B ${chg/1e9:>+10,.0f}B")

    print()
    print(f"{'Total net revenue change':<40} ${delta['total_change']/1e9:>+10,.0f}B")
    print(f"{'Identity residual (should ~ 0)':<40} ${delta['_identity_residual']/1e9:>+10,.2f}B")

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
