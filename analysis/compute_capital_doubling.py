"""Simulate AI-driven doubling of capital income.

Models a scenario where AI increases returns to capital by 100%:
all capital income variables are doubled while labor income is unchanged.
This represents a purely productivity-driven scenario (unlike the labor→capital
shift, total market income increases here).

Outputs: analysis/outputs/capital_doubling.json
"""

import json
import os
import numpy as np
from policyengine_us import Microsimulation

from .constants import CAPITAL_INCOME_VARS, YEAR
from .fiscal import net_fiscal_impact, revenue_components
from .metrics import extract_results as _extract_results

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "outputs", "capital_doubling.json")


def main():
    print("=" * 60)
    print("CAPITAL INCOME DOUBLING SCENARIO")
    print("=" * 60)

    baseline = Microsimulation()

    # Create branch and set all capital income inputs BEFORE computing
    branch = baseline.get_branch("doubled_capital")
    for var in CAPITAL_INCOME_VARS:
        original = baseline.calculate(var, period=YEAR)
        raw = np.array(original)
        branch.set_input(var, YEAR, np.where(raw >= 0, raw * 2, raw))

    print("\nComputing baseline metrics...")
    base_metrics = _extract_results(baseline, "Baseline")
    base_rev = revenue_components(baseline)

    print("\nComputing doubled capital metrics...")
    doubled_metrics = _extract_results(branch, "Doubled capital")
    doubled_rev = revenue_components(branch)
    delta = net_fiscal_impact(doubled_rev, base_rev)

    # Total capital income added (weighted sum of additions)
    total_cap_added = 0.0
    for var in CAPITAL_INCOME_VARS:
        vals = baseline.calculate(var, period=YEAR)
        raw = np.array(vals)
        w = np.array(vals.weights)
        total_cap_added += float((np.where(raw >= 0, raw, 0) * w).sum())

    def _fmt(metrics, rev, delta=None):
        row = {
            "market_gini": metrics["market_gini"],
            "net_gini": metrics["net_gini"],
            "spm_poverty_rate": metrics["spm_poverty_rate"],
            "mean_net_income": metrics["mean_net_income"],
            "fed_revenue_b": metrics["fed_revenue"] / 1e9,
            "state_revenue_b": metrics["state_revenue"] / 1e9,
            "fed_income_tax_before_refundable_credits_b": (
                rev["fed_income_tax_before_refundable_credits"] / 1e9
            ),
            "employee_payroll_b": (
                rev["employee_social_security_tax"]
                + rev["employee_medicare_tax"]
            ) / 1e9,
            "employer_payroll_b": rev["employer_payroll_tax"] / 1e9,
            "eitc_cost_b": rev["eitc"] / 1e9,
            "refundable_ctc_cost_b": rev["refundable_ctc"] / 1e9,
            "snap_cost_b": rev["snap"] / 1e9,
            "state_tax_before_refundable_credits_b": (
                rev["state_tax_before_refundable_credits"] / 1e9
            ),
            "decile_shares": metrics["decile_shares"],
        }
        if delta:
            row["revenue_change_b"] = delta["total_change"] / 1e9
            row["household_tax_change_b"] = (
                delta["household_tax_before_refundable_credits_change"] / 1e9
            )
            row["refundable_credits_change_b"] = (
                delta["household_refundable_tax_credits_change"] / 1e9
            )
            row["benefits_change_b"] = delta["household_benefits_change"] / 1e9
            row["employer_payroll_change_b"] = (
                delta["employer_payroll_tax_change"] / 1e9
            )
            row["fed_capital_gains_tax_change_b"] = (
                delta["fed_capital_gains_tax_change"] / 1e9
            )
            row["fed_niit_change_b"] = (
                delta["fed_net_investment_income_tax_change"] / 1e9
            )
            row["fed_amt_change_b"] = (
                delta["fed_alternative_minimum_tax_change"] / 1e9
            )
            row["state_tax_change_b"] = (
                delta["state_tax_before_refundable_credits_change"] / 1e9
            )
        return row

    result = {
        "year": YEAR,
        "total_capital_added_b": total_cap_added / 1e9,
        "baseline": _fmt(base_metrics, base_rev),
        "doubled": _fmt(doubled_metrics, doubled_rev, delta),
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {OUTPUT_PATH}")

    # Summary
    print("\n" + "=" * 55)
    print(f"{'Metric':<30} {'Baseline':>10} {'Doubled':>10}")
    print("-" * 55)
    def _fed_inc(rev):
        return rev["fed_income_tax_before_refundable_credits"] / 1e9

    def _ee_payroll(rev):
        return (
            rev["employee_social_security_tax"] + rev["employee_medicare_tax"]
        ) / 1e9

    for label, bv, dv in [
        ("Market Gini",        f"{base_metrics['market_gini']:.4f}",   f"{doubled_metrics['market_gini']:.4f}"),
        ("Net Gini",           f"{base_metrics['net_gini']:.4f}",      f"{doubled_metrics['net_gini']:.4f}"),
        ("SPM poverty rate",   f"{base_metrics['spm_poverty_rate']:.2%}", f"{doubled_metrics['spm_poverty_rate']:.2%}"),
        ("Fed inc tax bef ref ($B)", f"{_fed_inc(base_rev):.0f}",      f"{_fed_inc(doubled_rev):.0f}"),
        ("Employee payroll ($B)", f"{_ee_payroll(base_rev):.0f}",     f"{_ee_payroll(doubled_rev):.0f}"),
        ("Employer payroll ($B)", f"{base_rev['employer_payroll_tax']/1e9:.0f}", f"{doubled_rev['employer_payroll_tax']/1e9:.0f}"),
        ("EITC cost ($B)",     f"{base_rev['eitc']/1e9:.0f}",          f"{doubled_rev['eitc']/1e9:.0f}"),
        ("Net rev change ($B)", "",                                      f"{delta['total_change']/1e9:+.0f}"),
    ]:
        print(f"{label:<30} {bv:>10} {dv:>10}")


if __name__ == "__main__":
    main()
