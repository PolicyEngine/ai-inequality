"""Compare AI scenario results across two populace data builds.

Both runs use the same policyengine-us version, so every difference here is
attributable to the data build alone — the decomposition the o->p step makes
possible that the vintage change from policyengine-us-data could not. That
holds only for a pair that also shares scenario inputs and net-income
accounting, so the default pair is build o against build p as first
published (the pair the paper's stability section uses); the script warns
when a given pair differs in either.

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


def scenario_inputs(payload):
    return sorted(
        (
            row["scenario"]["label"],
            row["scenario"].get("target_labor_share"),
            row["scenario"].get("gdp_growth"),
        )
        for row in payload.get("scenarios", [])
    )


def excluded_benefits(payload):
    return sorted((payload.get("metadata") or {}).get("net_income_excluded_benefits") or ())


def build_id(payload):
    return (payload.get("metadata") or {}).get("certified_data_build_id", "?")


def model_version(payload):
    return (payload.get("metadata") or {}).get("country_model_version", "?")


def by_label(payload):
    return {row["scenario"]["label"]: row for row in payload.get("scenarios", [])}


def main():
    with open(OLD) as handle:
        old = json.load(handle)
    with open(NEW) as handle:
        new = json.load(handle)

    print("=" * 96)
    print("AI SCENARIOS ACROSS DATA BUILDS (same model version -> data-only diff)")
    print(f"  old: {build_id(old)}  @ policyengine-us {model_version(old)}")
    print(f"  new: {build_id(new)}  @ policyengine-us {model_version(new)}")
    if model_version(old) != model_version(new):
        print("  WARNING: model versions differ; this is NOT a data-only diff.")
    if scenario_inputs(old) != scenario_inputs(new):
        print("  WARNING: scenario inputs differ; this is NOT a data-only diff.")
    if excluded_benefits(old) != excluded_benefits(new):
        print("  WARNING: net-income accounting differs; this is NOT a data-only diff.")
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
