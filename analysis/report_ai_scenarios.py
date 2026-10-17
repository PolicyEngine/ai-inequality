"""Turn ai_scenarios.json into the tables that go in the write-up."""

import json
import os
import sys

PATH = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(os.path.dirname(__file__), "outputs", "ai_scenarios.json")
)

with open(PATH) as handle:
    data = json.load(handle)

baseline = data["baseline"]
rows = data["scenarios"]
by_label = {row["scenario"]["label"]: row for row in rows}
meta = data["metadata"]

print("=" * 100)
print(f"AI SCENARIOS - PolicyEngine-US, {data['year']}")
print(
    f"{meta['country_model_package']} {meta['country_model_version']} | "
    f"policyengine {meta['policyengine_version']} | "
    f"{meta['data_package']} {meta['data_version']} | {meta['dataset_name']}"
)
print("=" * 100)

context = baseline["context"]
print(
    f"\nBaseline {data['year']}: labor ${context['positive_labor_income_t']:.2f}T, "
    f"capital ${context['positive_capital_income_t']:.2f}T "
    f"(modelled labor share {context['modelled_labor_share']:.1%}; "
    f"scenarios calibrated on a 55.5% national labor share)"
)
print(
    f"SPM poverty {baseline['spm_poverty_rate']:.2%} | "
    f"net Gini {baseline['net_gini']:.4f} | "
    f"market Gini {baseline['market_gini']:.4f} | "
    f"top 1% of net income {baseline['net_top_1_share']:.2%}"
)
print(
    f"Social Security cap ${context['social_security_cap']:,.0f}: "
    f"{context['share_of_wages_above_cap']:.1%} of wage income above it, "
    f"{context['share_of_workers_above_cap']:.1%} of workers"
)

header = (
    f"\n{'scenario':26s} {'revenue':>9s} {'incometax':>10s} {'payroll':>9s} "
    f"{'benefits':>9s} {'state':>8s} {'poverty':>8s} {'d_pov':>7s} "
    f"{'netGini':>8s} {'top1%':>7s}"
)
print(header)
print("-" * (len(header) - 1))
for row in rows:
    print(
        f"{row['scenario']['label']:26s} "
        f"{row['total_rev_change_b']:>+9,.0f} "
        f"{row['fed_income_tax_change_b']:>+10,.0f} "
        f"{row['payroll_change_b']:>+9,.0f} "
        f"{row['benefits_change_b']:>+9,.0f} "
        f"{row['state_tax_change_b']:>+8,.0f} "
        f"{row['spm_poverty_rate']:>7.2%} "
        f"{(row['spm_poverty_rate'] - baseline['spm_poverty_rate']) * 100:>+7.2f} "
        f"{row['net_gini']:>8.4f} "
        f"{row['net_top_1_share']:>7.2%}"
    )
print("\nAll figures $B, change vs the same-year current-law baseline.")
print("Revenue = household taxes + employer payroll - refundable credits - benefits.")
print("No corporate income tax: PolicyEngine-US models the household sector.")

print("\n\nWHAT THE TILT TOWARD CAPITAL COSTS (revenue, $B)")
line = f"{'scenario':12s} {'shares fixed':>13s} {'as forecast':>12s} {'kept':>7s} {'gap':>9s}"
print(line)
print("-" * len(line))
for name in ("Slow", "Moderate", "Rapid"):
    fixed = by_label.get(f"{name} / shares fixed")
    tilted = by_label.get(f"{name} / proportional")
    if not fixed or not tilted:
        continue
    a, b = fixed["total_rev_change_b"], tilted["total_rev_change_b"]
    print(f"{name:12s} {a:>+13,.0f} {b:>+12,.0f} {b / a:>6.0%} {b - a:>+9,.0f}")
print("\nThe Budget Lab (revised 2026-10-09) reports revenue gains nearly twice as")
print("large under Rapid with capital and labor shares held at 2026 levels (their")
print("grid: 1.79x, i.e. 'kept' 56%), and 82% lower in their most extreme case")
print("(Slow, compressive).")

for name in ("Slow", "Moderate", "Rapid"):
    print(f"\n\nTHE LABOR INEQUALITY CHANNEL ({name})")
    line = (
        f"{'variant':14s} {'lambda':>7s} {'crossover':>11s} {'revenue':>9s} "
        f"{'incometax':>10s} {'payroll':>9s} {'poverty':>8s} {'netGini':>8s}"
    )
    print(line)
    print("-" * len(line))
    for variant in ("compressive", "proportional", "expansive"):
        row = by_label.get(f"{name} / {variant}")
        if not row:
            continue
        crossover = row["diagnostics"].get("labor_crossover_income")
        print(
            f"{variant:14s} "
            f"{row['scenario']['inequality_lambda']:>7.4f} "
            f"{('-' if crossover is None else f'${crossover:,.0f}'):>11s} "
            f"{row['total_rev_change_b']:>+9,.0f} "
            f"{row['fed_income_tax_change_b']:>+10,.0f} "
            f"{row['payroll_change_b']:>+9,.0f} "
            f"{row['spm_poverty_rate']:>7.2%} "
            f"{row['net_gini']:>8.4f}"
        )
print("\nCrossover = the wage at which the spread transform leaves a worker")
print("unchanged. Below it workers lose, above it they gain.")

sensitivities = data.get("sensitivities", {})

if "realization" in sensitivities:
    print("\n\nREALIZATION SENSITIVITY (Rapid / proportional)")
    line = (
        f"{'realized share':>15s} {'revenue':>9s} {'incometax':>10s} "
        f"{'poverty':>8s} {'netGini':>8s} {'top1%':>7s}"
    )
    print(line)
    print("-" * len(line))
    for row in sensitivities["realization"]:
        print(
            f"{row['scenario']['realization_rate']:>14.0%} "
            f"{row['total_rev_change_b']:>+9,.0f} "
            f"{row['fed_income_tax_change_b']:>+10,.0f} "
            f"{row['spm_poverty_rate']:>7.2%} "
            f"{row['net_gini']:>8.4f} "
            f"{row['net_top_1_share']:>7.2%}"
        )
    print("\n100% is the Budget Lab assumption: the realized share of capital")
    print("income is unchanged by AI.")

if "capital_scope_excluding_retirement" in sensitivities:
    print("\n\nCAPITAL SCOPE: EXCLUDING TAXABLE RETIREMENT DISTRIBUTIONS")
    line = f"{'scenario':12s} {'full set':>10s} {'excl. retire':>13s} {'difference':>11s}"
    print(line)
    print("-" * len(line))
    for row in sensitivities["capital_scope_excluding_retirement"]:
        name = row["scenario"]["name"]
        full = by_label.get(f"{name} / proportional")
        if not full:
            continue
        a, b = full["total_rev_change_b"], row["total_rev_change_b"]
        print(f"{name:12s} {a:>+10,.0f} {b:>+13,.0f} {b - a:>+11,.0f}")

rapid = by_label.get("Rapid / proportional")
if rapid:
    print("\n\nEFFECTIVE RATE ON THE INCREMENT (Rapid / proportional)")
    gross = rapid["market_income_change_b"]
    if gross:
        print(
            f"market income {gross:+,.0f}B -> revenue "
            f"{rapid['total_rev_change_b']:+,.0f}B = "
            f"{rapid['total_rev_change_b'] / gross:.1%} of the increment"
        )
        print("The Budget Lab reports 21%-32% for Rapid: federal revenue including")
        print("their corporate wedge over gross factor income. The bases differ;")
        print("emit_paper_values.py states both on a matched numerator.")

    print("\n\nSTATE FISCAL IMPACT, Rapid / proportional (top and bottom 8, $B)")
    states = sorted(
        rapid["state_deltas"].items(),
        key=lambda kv: kv[1]["state_net_change_b"],
        reverse=True,
    )
    line = (
        f"{'state':>6s} {'net':>8s} {'tax':>8s} {'benefits':>9s}    "
        f"{'state':>6s} {'net':>8s} {'tax':>8s} {'benefits':>9s}"
    )
    print(line)
    print("-" * len(line))
    for (code_a, a), (code_b, b) in zip(states[:8], states[-8:][::-1]):
        print(
            f"{code_a:>6s} {a['state_net_change_b']:>+8.1f} "
            f"{a['state_tax_change_b']:>+8.1f} {a['state_benefits_change_b']:>+9.1f}    "
            f"{code_b:>6s} {b['state_net_change_b']:>+8.1f} "
            f"{b['state_tax_change_b']:>+8.1f} {b['state_benefits_change_b']:>+9.1f}"
        )

print("\n\nDIAGNOSTICS (should be ~0)")
worst = max(rows, key=lambda r: abs(r["identity_residual_b"]))
print(
    f"largest |net-income identity residual| = ${abs(worst['identity_residual_b']):.3f}B "
    f"({worst['scenario']['label']})"
)
worst_labor = max(rows, key=lambda r: abs(r["diagnostics"]["labor_growth_error"]))
print(
    f"largest labor-growth targeting error = "
    f"{worst_labor['diagnostics']['labor_growth_error']:.2e} "
    f"({worst_labor['scenario']['label']})"
)
