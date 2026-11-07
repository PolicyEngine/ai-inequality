"""Summarize a ``california_shift`` run and compare it with the published sweep.

Prints, for each shift level:

* California's net change, with and without its employee SDI contribution;
* all other states combined, every state, and federal net revenue;
* the federal split into income tax, payroll taxes, refundable credits and
  benefits;
* the labor income California households give up and the capital income they
  receive;
* California's change by within-state market-income group;

then the baseline concentration of California's labor and capital income, and
the drift from the site's published sweep at matching levels.

Usage:
    python -m analysis.california_summary PATH.json [--sweep src/data/shiftSweepData.json]
"""

from __future__ import annotations

import argparse
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP_PATH = os.path.join(REPO, "src", "data", "shiftSweepData.json")

EMPLOYEE_PAYROLL_KEYS = (
    "employee_social_security_tax_change",
    "employee_medicare_tax_change",
    "self_employment_tax_change",
)


def federal_split(components):
    """Split the federal net change ($B) into its parts.

    Federal net = all-government net less the states' net, so each federal part
    is the national aggregate less its state portion. ``residual`` holds any
    household tax outside federal income tax, payroll and state tax (local and
    flat taxes); it is zero when the decomposition is complete. Payroll takes
    the employer side from ``employer_payroll_tax``, the aggregate that
    ``fiscal.net_fiscal_impact`` counts, so the parts add up to the total.
    """
    c = components
    employee_payroll = sum(c.get(k, 0.0) for k in EMPLOYEE_PAYROLL_KEYS)
    employer_payroll = c.get("employer_payroll_tax_change", 0.0)
    payroll = employee_payroll + employer_payroll
    income_tax = c.get("fed_income_tax_before_refundable_credits_change", 0.0)
    state_tax = c.get("state_tax_before_refundable_credits_change", 0.0)
    residual = (
        c.get("household_tax_before_refundable_credits_change", 0.0)
        - income_tax
        - employee_payroll
        - state_tax
    )
    credits = c.get("household_refundable_tax_credits_change", 0.0) - c.get(
        "state_refundable_credits_change", 0.0
    )
    benefits = c.get("household_benefits_change", 0.0) - c.get("state_benefits_change", 0.0)
    states_net = (
        state_tax
        - c.get("state_refundable_credits_change", 0.0)
        - c.get("state_benefits_change", 0.0)
    )
    federal = income_tax + payroll + residual - credits - benefits
    return {
        "income_tax": income_tax,
        "payroll": payroll,
        "employee_payroll": employee_payroll,
        "employer_payroll": employer_payroll,
        "employer_social_security_and_medicare": c.get("employer_social_security_tax_change", 0.0)
        + c.get("employer_medicare_tax_change", 0.0),
        "residual": residual,
        "refundable_credits": credits,
        "federal_refundable_credits_reported": c.get(
            "income_tax_refundable_credits_change", float("nan")
        ),
        "benefits": benefits,
        "federal_net": federal,
        "states_net_national": states_net,
        "total": c.get("total_change", 0.0),
    }


def published_by_level(path=SWEEP_PATH):
    data = json.load(open(path))
    out = {}
    for row in data["scenarios"]:
        states = row.get("state_deltas") or {}
        if not states:
            continue
        ca = states["CA"]["state_net_change_b"]
        all_states = sum(v["state_net_change_b"] for v in states.values())
        out[row["shift_pct"]] = {
            "california": ca,
            "other_states": all_states - ca,
            "federal": row["total_rev_change_b"] - all_states,
            "total": row["total_rev_change_b"],
        }
    return out, data["metadata"]


def _pct(new, old):
    return float("nan") if old == 0 else 100 * (new - old) / abs(old)


def summarize(run, published=None):
    lines = []
    meta = run["metadata"]
    lines.append(
        f"Run: policyengine {meta['policyengine_version']}, policyengine-us "
        f"{meta['policyengine_us_version']}, year {run['year']}"
    )
    base = run["baseline_california"]
    lines.append(
        f"California baseline: {base['households_m']:.2f}M households, labor income "
        f"${base['labor_income_b']:,.0f}B, capital income ${base['capital_income_b']:,.0f}B, "
        f"net state revenue ${base['state_net_revenue_b']:,.1f}B, SDI ${base['sdi_b']:,.1f}B"
    )
    lines.append("Shares of California's positive labor and capital income by market-income group:")
    for g in base["groups"]:
        lines.append(
            f"  {g['group']:<26} labor {100 * g['labor_income_share']:5.1f}%  "
            f"capital {100 * g['capital_income_share']:5.1f}%  "
            f"mean market income ${g['mean_market_income']:,.0f}"
        )
    for row in run["levels"]:
        ca = row["california"]
        split = federal_split(row["national_components_b"])
        lines.append("")
        lines.append(f"{row['shift_pct']}% shift (${row['labor_income_moved_b']:,.0f}B of labor income moves)")
        lines.append(
            f"  California net {ca['state_net_change_b']:+.2f}B; with SDI "
            f"{ca['state_net_including_sdi_change_b']:+.2f}B (SDI {ca['sdi_change_b']:+.2f}B)"
        )
        lines.append(
            f"  California parts: state tax {ca['state_tax_before_refundable_credits_change_b']:+.2f}B, "
            f"refundable credits {ca['state_refundable_credits_change_b']:+.2f}B, "
            f"benefits {ca['state_benefits_change_b']:+.2f}B"
        )
        lines.append(
            f"  California households: labor {ca['labor_income_change_b']:+.1f}B, capital "
            f"{ca['capital_income_change_b']:+.1f}B, market income {ca['market_income_change_b']:+.1f}B"
        )
        pipeline_ca = row["state_net_change_b"].get("CA")
        lines.append(
            f"  Check: pipeline CA {pipeline_ca:+.4f}B vs household frame "
            f"{ca['state_net_change_b']:+.4f}B; per-state sum {row['all_states_net_change_b']:+.3f}B vs "
            f"national state lines {split['states_net_national']:+.3f}B"
        )
        lines.append(
            f"  Other states {row['other_states_net_change_b']:+.2f}B; all states "
            f"{row['all_states_net_change_b']:+.2f}B; gaining: {', '.join(row['states_gaining'])}; "
            f"{row['states_losing_count']} losing"
        )
        lines.append(
            f"  Federal net {row['federal_net_change_b']:+.1f}B = income tax {split['income_tax']:+.1f}B "
            f"+ payroll {split['payroll']:+.1f}B + other household tax {split['residual']:+.2f}B "
            f"- refundable credits {split['refundable_credits']:+.1f}B - benefits {split['benefits']:+.1f}B "
            f"(sum {split['federal_net']:+.1f}B; reported federal refundable credits "
            f"{split['federal_refundable_credits_reported']:+.1f}B)"
        )
        lines.append(
            f"  Payroll: employee and self-employment {split['employee_payroll']:+.1f}B, employer "
            f"{split['employer_payroll']:+.1f}B (employer Social Security and Medicare lines "
            f"{split['employer_social_security_and_medicare']:+.1f}B)"
        )
        lines.append(f"  All governments {row['all_government_change_b']:+.1f}B")
        total_tax = ca["state_tax_before_refundable_credits_change_b"]
        for g in row["california_by_group"]:
            share = float("nan") if total_tax == 0 else 100 * g["state_tax_before_refundable_credits_change_b"] / total_tax
            lines.append(
                f"    {g['group']:<26} state tax {g['state_tax_before_refundable_credits_change_b']:+.2f}B "
                f"({share:5.1f}% of the change), net {g['state_net_change_b']:+.2f}B, labor "
                f"{g['labor_income_change_b']:+.1f}B, capital {g['capital_income_change_b']:+.1f}B"
            )
        if published and row["shift_pct"] in published:
            p = published[row["shift_pct"]]
            lines.append(
                f"  Published: California {p['california']:+.2f}B ({_pct(ca['state_net_change_b'], p['california']):+.1f}%), "
                f"other states {p['other_states']:+.2f}B, federal {p['federal']:+.1f}B "
                f"({_pct(row['federal_net_change_b'], p['federal']):+.1f}%)"
            )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run")
    parser.add_argument("--sweep", default=SWEEP_PATH)
    args = parser.parse_args()
    run = json.load(open(args.run))
    published, meta = published_by_level(args.sweep)
    print(summarize(run, published))
    print(
        f"\nPublished sweep: policyengine-us {meta['country_model_version']}, "
        f"policyengine {meta['policyengine_version']}"
    )


if __name__ == "__main__":
    main()
