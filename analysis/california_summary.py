"""Summarize a ``california_shift`` run and compare it with the published sweep.

Prints, for each shift level:

* California's net change, with and without its employee SDI contribution;
* the same once health spending and TANF count: California's share of
  Medi-Cal, CHIP and Medicare Savings Program costs, the state-only coverage it
  pays for in full, its premium subsidy and CalWORKs, with the other states and
  federal lines on the same basis (runs without these fields skip the lines);
* all other states combined, every state, and federal net revenue;
* the federal split into income tax, federal payroll taxes, refundable credits
  and benefits, and the state payroll and local taxes that the all-government
  total counts outside every state's line and the federal line;
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

#: Federal payroll taxes on the employee and self-employed side, inside
#: ``household_tax_before_refundable_credits``.
EMPLOYEE_PAYROLL_KEYS = (
    "employee_social_security_tax_change",
    "employee_medicare_tax_change",
    "additional_medicare_tax_change",
    "self_employment_tax_change",
)
#: Federal payroll taxes on the employer side, inside ``employer_payroll_tax``.
EMPLOYER_PAYROLL_KEYS = (
    "employer_social_security_tax_change",
    "employer_medicare_tax_change",
    "employer_federal_unemployment_tax_change",
)
#: State payroll and local taxes, with the aggregate each sits in.
HOUSEHOLD_STATE_LOCAL_KEYS = (
    "employee_state_payroll_tax_change",
    "local_income_tax_before_refundable_credits_change",
    "local_occupational_tax_change",
)
EMPLOYER_STATE_LOCAL_KEYS = (
    "employer_state_payroll_tax_change",
    "employer_local_payroll_tax_change",
)


#: The limit on the TANF lines, printed with any run that reports them.
BEFORE_LSR_NOTE = (
    "Note: the shift sets employment_income and self_employment_income on each branch, so "
    "programs that read their *_before_lsr inputs see pre-shift earnings. The default TANF "
    "earned-income list and Massachusetts's, Montana's and South Carolina's lists read them, "
    "so those states' TANF responds to the added capital income and not to the wage cut, and "
    "can fall. The TANF, other-states and all-government lines and the study measure's federal "
    "lines miss the response to the wage cut. California's CalWORKs list reads the shifted "
    "variables."
)


def federal_split(components):
    """Split the federal net change ($B) into its parts.

    Federal net = all-government net less the states' net and less the state
    payroll and local taxes no state's line holds, so each federal part is the
    national aggregate less its state and local portions. ``payroll`` holds
    federal payroll taxes only. ``residual`` holds household tax outside
    federal income tax, federal payroll, state tax, state payroll and local
    taxes (the flat tax), and ``employer_residual`` employer payroll tax outside
    its federal, state and local parts; both are zero when the decomposition is
    complete. A run that predates the state payroll and local lines reports
    none of them, so its residuals hold those taxes and its federal line is all
    governments less the states.
    """
    c = components

    def get(key):
        return c.get(key, 0.0)

    employee_payroll = sum(get(k) for k in EMPLOYEE_PAYROLL_KEYS)
    employer_payroll = sum(get(k) for k in EMPLOYER_PAYROLL_KEYS)
    payroll = employee_payroll + employer_payroll
    household_state_local = sum(get(k) for k in HOUSEHOLD_STATE_LOCAL_KEYS)
    employer_state_local = sum(get(k) for k in EMPLOYER_STATE_LOCAL_KEYS)
    income_tax = get("fed_income_tax_before_refundable_credits_change")
    state_tax = get("state_tax_before_refundable_credits_change")
    residual = (
        get("household_tax_before_refundable_credits_change")
        - income_tax
        - employee_payroll
        - state_tax
        - household_state_local
    )
    employer_residual = (
        get("employer_payroll_tax_change") - employer_payroll - employer_state_local
    )
    credits = get("household_refundable_tax_credits_change") - get("state_refundable_credits_change")
    benefits = get("household_benefits_change") - get("state_benefits_change")
    states_net = state_tax - get("state_refundable_credits_change") - get("state_benefits_change")
    federal = income_tax + payroll + residual + employer_residual - credits - benefits
    return {
        "income_tax": income_tax,
        "payroll": payroll,
        "employee_payroll": employee_payroll,
        "employer_payroll": employer_payroll,
        "employer_social_security_and_medicare": get("employer_social_security_tax_change")
        + get("employer_medicare_tax_change"),
        "residual": residual,
        "employer_residual": employer_residual,
        "state_payroll": get("employee_state_payroll_tax_change")
        + get("employer_state_payroll_tax_change"),
        "local": get("local_income_tax_before_refundable_credits_change")
        + get("local_occupational_tax_change")
        + get("employer_local_payroll_tax_change"),
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
        inside = ""
        if "mental_health_services_tax_change_b" in ca:
            inside = (
                f" (of which use tax {ca['state_use_tax_change_b']:+.2f}B and the 1% mental health "
                f"services tax {ca['mental_health_services_tax_change_b']:+.2f}B)"
            )
        lines.append(
            f"  California parts: state tax {ca['state_tax_before_refundable_credits_change_b']:+.2f}B{inside}, "
            f"refundable credits {ca['state_refundable_credits_change_b']:+.2f}B, "
            f"benefits {ca['state_benefits_change_b']:+.2f}B"
        )
        lines.extend(_health_tanf_lines(row))
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
            f"+ payroll {split['payroll']:+.1f}B + other tax "
            f"{split['residual'] + split['employer_residual']:+.2f}B "
            f"- refundable credits {split['refundable_credits']:+.1f}B - benefits {split['benefits']:+.1f}B "
            f"(sum {split['federal_net']:+.1f}B; reported federal refundable credits "
            f"{split['federal_refundable_credits_reported']:+.1f}B)"
        )
        lines.append(
            f"  Federal payroll: employee and self-employment {split['employee_payroll']:+.1f}B, employer "
            f"{split['employer_payroll']:+.1f}B (employer Social Security and Medicare "
            f"{split['employer_social_security_and_medicare']:+.1f}B)"
        )
        lines.append(
            f"  Outside every state's line and the federal line: state payroll taxes "
            f"{split['state_payroll']:+.2f}B, local taxes {split['local']:+.2f}B"
        )
        lines.append(f"  All governments {row['all_government_change_b']:+.1f}B")
        total_tax = ca["state_tax_before_refundable_credits_change_b"]
        for g in row["california_by_group"]:
            share = float("nan") if total_tax == 0 else 100 * g["state_tax_before_refundable_credits_change_b"] / total_tax
            full = g.get("state_net_with_health_tanf_change_b")
            lines.append(
                f"    {g['group']:<26} state tax {g['state_tax_before_refundable_credits_change_b']:+.2f}B "
                f"({share:5.1f}% of the change), net {g['state_net_change_b']:+.2f}B"
                + ("" if full is None else f" (with health and TANF {full:+.2f}B)")
                + f", labor {g['labor_income_change_b']:+.1f}B, capital {g['capital_income_change_b']:+.1f}B"
            )
        if published and row["shift_pct"] in published:
            p = published[row["shift_pct"]]
            # The published sweep's split: all governments less the states.
            federal_published = row.get(
                "federal_net_published_definition_change_b", row["federal_net_change_b"]
            )
            lines.append(
                f"  Published: California {p['california']:+.2f}B ({_pct(ca['state_net_change_b'], p['california']):+.1f}%), "
                f"other states {p['other_states']:+.2f}B, federal as all governments less the states {p['federal']:+.1f}B "
                f"({_pct(federal_published, p['federal']):+.1f}%)"
            )
    lines.extend(_within_state_lines(run))
    if any("state_net_with_health_tanf_change_b" in r["california"] for r in run["levels"]):
        lines.extend(["", BEFORE_LSR_NOTE])
    return "\n".join(lines)


def _health_tanf_lines(row):
    """California, the other states and federal once health spending and TANF count."""
    ca = row["california"]
    if "state_net_with_health_tanf_change_b" not in ca:
        return []
    tanf = row["tanf_change_b"]
    twice = row.get("tanf_counted_twice_change_b", 0.0)
    oregon = row.get("healthier_oregon_overlap_change_b", 0.0)
    return [
        f"  California with health and TANF {ca['state_net_with_health_tanf_change_b']:+.2f}B; with SDI "
        f"{ca['state_net_with_health_tanf_including_sdi_change_b']:+.2f}B. Spending changes: state health "
        f"{ca['state_health_change_b']:+.2f}B (matched shares {ca['state_health_split_change_b']:+.2f}B, "
        f"state-only coverage {ca['state_only_coverage_change_b']:+.2f}B, premium subsidy "
        f"{ca['state_health_programs_change_b']:+.2f}B), CalWORKs {ca['tanf_change_b']:+.2f}B",
        f"  With health and TANF: other states {row['other_states_net_with_health_tanf_change_b']:+.2f}B "
        f"({row['states_losing_with_health_tanf_count']} losing); federal "
        f"{row['federal_net_with_health_tanf_change_b']:+.1f}B; all governments "
        f"{row['all_government_with_health_change_b']:+.1f}B. Health spending changes: federal "
        f"{row['health_federal_change_b']:+.1f}B, states {row['health_state_change_b']:+.2f}B; TANF "
        f"{tanf:+.2f}B leaves the federal line: {tanf - twice:+.2f}B to the states and {twice:+.2f}B "
        f"(TANF household_state_benefits already counts) out of the all-government total; "
        f"Healthier Oregon cost for Medicaid enrollees dropped {oregon:+.3f}B",
    ]


def _within_state_lines(run):
    """The within-state variant, and how much of California's gain it keeps."""
    within = run.get("within_state_levels") or []
    if not within:
        return []
    national = {row["shift_pct"]: row for row in run["levels"]}
    lines = ["", "Within-state variant: each state's freed labor income goes to its own capital holders"]
    for row in within:
        ca = row["california"]
        lines.append("")
        lines.append(
            f"{row['shift_pct']}% shift: California net {ca['state_net_change_b']:+.2f}B; with SDI "
            f"{ca['state_net_including_sdi_change_b']:+.2f}B; households: labor "
            f"{ca['labor_income_change_b']:+.1f}B, capital {ca['capital_income_change_b']:+.1f}B, "
            f"market income {ca['market_income_change_b']:+.2f}B"
        )
        lines.append(
            f"  Other states {row['other_states_net_change_b']:+.2f}B; gaining: "
            f"{', '.join(row['states_gaining'])}; {row['states_losing_count']} losing; federal "
            f"{row['federal_net_change_b']:+.1f}B; all governments {row['all_government_change_b']:+.1f}B"
        )
        lines.extend(_health_tanf_lines(row))
        n = national.get(row["shift_pct"])
        if n:
            nat = n["california"]["state_net_change_b"]
            lines.append(
                f"  California under the national allocation {nat:+.2f}B: "
                f"{ca['state_net_change_b']:+.2f}B from income moving within the state and "
                f"{nat - ca['state_net_change_b']:+.2f}B from income moving between states "
                f"(market income {n['california']['market_income_change_b']:+.1f}B)"
            )
        total_tax = ca["state_tax_before_refundable_credits_change_b"]
        for g in row["california_by_group"]:
            share = float("nan") if total_tax == 0 else 100 * g["state_tax_before_refundable_credits_change_b"] / total_tax
            lines.append(
                f"    {g['group']:<26} state tax {g['state_tax_before_refundable_credits_change_b']:+.2f}B "
                f"({share:5.1f}% of the change), labor {g['labor_income_change_b']:+.1f}B, capital "
                f"{g['capital_income_change_b']:+.1f}B"
            )
        ranked = sorted(row["state_net_change_b"].items(), key=lambda kv: kv[1])
        lines.append(
            "  Five lowest changes: " + ", ".join(f"{s} {v:+.2f}B" for s, v in ranked[:5])
        )
        lines.append(
            "  Five highest changes: " + ", ".join(f"{s} {v:+.2f}B" for s, v in ranked[::-1][:5])
        )
    return lines


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
