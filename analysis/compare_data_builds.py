"""Compare AI scenario results across two Microcosm data builds.

By default this compares build o with the published build p results. Both ran
on policyengine-us 1.764.6 and count Head Start in net income, while the
policyengine.py runner moved from 4.22.3 to 5.0.1 between them. The header
warns when a pair differs in country model version or in the benefits it keeps
out of net income.

Usage:
    python analysis/compare_data_builds.py [old.json] [new.json]
"""

import json
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
OLD = (
    sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "ai_scenarios_buildo.json")
)
NEW = (
    sys.argv[2]
    if len(sys.argv) > 2
    else os.path.join(OUT, "ai_scenarios_buildp_published.json")
)


def build_id(payload):
    return (payload.get("metadata") or {}).get("certified_data_build_id", "?")


def model_version(payload):
    return (payload.get("metadata") or {}).get("country_model_version", "?")


def runner_version(payload):
    return (payload.get("metadata") or {}).get("policyengine_version", "?")


def net_income_exclusions(payload):
    """Benefits a run kept out of net income, or None for runs that predate the
    Head Start correction and so record none."""
    metadata = payload.get("metadata") or {}
    bundle = metadata.get("policyengine_bundle") or {}
    for record in (metadata, bundle):
        if "net_income_excluded_benefits" in record:
            return sorted(record["net_income_excluded_benefits"])
    return None


def by_label(payload):
    return {row["scenario"]["label"]: row for row in payload.get("scenarios", [])}


def main():
    with open(OLD) as handle:
        old = json.load(handle)
    with open(NEW) as handle:
        new = json.load(handle)

    print("=" * 96)
    print("AI SCENARIOS ACROSS DATA BUILDS")
    for name, payload in (("old", old), ("new", new)):
        print(
            f"  {name}: {build_id(payload)}  @ policyengine-us "
            f"{model_version(payload)}, policyengine.py {runner_version(payload)}"
        )
    if model_version(old) != model_version(new):
        print("  WARNING: the country model versions differ, so model changes")
        print("  mix into these differences.")
    if net_income_exclusions(old) != net_income_exclusions(new):
        print("  WARNING: the runs keep different benefits out of net income,")
        print("  so that accounting change mixes into these differences.")
    print("=" * 96)

    old_base, new_base = old["baseline"], new["baseline"]
    old_ctx = old_base.get("context", {})
    new_ctx = new_base.get("context", {})
    print("\nBASELINE 2030")
    rows = [
        ("positive labor income $T", "positive_labor_income_t", old_ctx, new_ctx, 2),
        (
            "positive capital income $T",
            "positive_capital_income_t",
            old_ctx,
            new_ctx,
            2,
        ),
        (
            "share of wages above SS cap",
            "share_of_wages_above_cap",
            old_ctx,
            new_ctx,
            3,
        ),
        ("SPM poverty", "spm_poverty_rate", old_base, new_base, 4),
        ("net Gini", "net_gini", old_base, new_base, 4),
        ("market Gini", "market_gini", old_base, new_base, 4),
        ("top 1% net income share", "net_top_1_share", old_base, new_base, 4),
    ]
    for label, key, source_old, source_new, digits in rows:
        a, b = source_old.get(key), source_new.get(key)
        if a is None or b is None:
            continue
        print(
            f"  {label:30s} {a:>10.{digits}f} -> {b:>10.{digits}f}   ({b - a:+.{digits}f})"
        )

    old_rows, new_rows = by_label(old), by_label(new)
    print("\nSCENARIO GRID (revenue $B | poverty delta pp vs own baseline)")
    header = (
        f"  {'scenario':26s} {'rev old':>9s} {'rev new':>9s} {'diff':>7s}"
        f"   {'pov old':>8s} {'pov new':>8s}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for label in old_rows:
        if label not in new_rows:
            continue
        a, b = old_rows[label], new_rows[label]
        pov_a = (a["spm_poverty_rate"] - old_base["spm_poverty_rate"]) * 100
        pov_b = (b["spm_poverty_rate"] - new_base["spm_poverty_rate"]) * 100
        print(
            f"  {label:26s} {a['total_rev_change_b']:>+9.1f} "
            f"{b['total_rev_change_b']:>+9.1f} "
            f"{b['total_rev_change_b'] - a['total_rev_change_b']:>+7.1f}"
            f"   {pov_a:>+8.2f} {pov_b:>+8.2f}"
        )

    def sens(payload, key):
        return {
            (row["scenario"].get("realization_rate"), row["scenario"].get("name")): row
            for row in (payload.get("sensitivities") or {}).get(key, [])
        }

    old_real, new_real = (sens(p, "realization") for p in (old, new))
    if old_real and new_real:
        print("\nREALIZATION SWEEP (Rapid / proportional, revenue $B)")
        for key in sorted(old_real, key=lambda k: k[0] or 0):
            if key not in new_real:
                continue
            a = old_real[key]["total_rev_change_b"]
            b = new_real[key]["total_rev_change_b"]
            print(f"  {key[0]:>5.0%}  {a:>+9.1f} -> {b:>+9.1f}   ({b - a:+.1f})")

    print("\nHEADLINES (Rapid)")
    for metric, fmt in (
        ("total_rev_change_b", "+.1f"),
        ("payroll_change_b", "+.1f"),
        ("fed_capital_gains_tax_change_b", "+.1f"),
    ):
        pairs = []
        for variant in ("shares fixed", "proportional", "expansive"):
            label = f"Rapid / {variant}"
            if label in old_rows and label in new_rows:
                pairs.append(
                    f"{variant}: {old_rows[label][metric]:{fmt}} -> "
                    f"{new_rows[label][metric]:{fmt}}"
                )
        print(f"  {metric:32s} " + " | ".join(pairs))


if __name__ == "__main__":
    main()
