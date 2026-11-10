"""Compare the published shift sweep against a freshly computed one.

The site ships a sweep built on an older model and the archived
policyengine-us-data package. Refreshing it on the current certified bundle
changes the numbers; this prints by how much, so the change can be reviewed
rather than silently republished.

Usage:
    python analysis/compare_sweep_vintages.py [shipped.json] [refreshed.json]
"""

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIPPED = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(REPO, "src", "data", "shiftSweepData.json")
)
REFRESHED = (
    sys.argv[2]
    if len(sys.argv) > 2
    else os.path.join(REPO, "analysis", "outputs", "shift_sweep.json")
)


def revenue(row):
    """Net revenue as the site defined it before it counted health coverage and TANF.

    Sweeps that count them keep that measure in
    ``total_rev_change_published_definition_b``, so a sweep from either side of
    that change compares with one from the other.
    """
    if "total_rev_change_published_definition_b" in row:
        return row["total_rev_change_published_definition_b"]
    return row.get("total_rev_change_b", row.get("revenue_change_b", 0.0))


def provenance(payload):
    meta = payload.get("metadata", {})
    return (
        f"{meta.get('country_model_package')} {meta.get('country_model_version')}"
        f" | policyengine {meta.get('policyengine_version')}"
        f" | {meta.get('data_package')} {meta.get('data_version')}"
        f" | {meta.get('dataset_name') or '-'}"
    )


def main():
    with open(SHIPPED) as handle:
        shipped = json.load(handle)
    with open(REFRESHED) as handle:
        refreshed = json.load(handle)

    print("=" * 92)
    print("SHIFT SWEEP: PUBLISHED vs REFRESHED")
    print("=" * 92)
    print(f"published: {provenance(shipped)}")
    print(f"refreshed: {provenance(refreshed)}")

    old = {row["shift_pct"]: row for row in shipped["scenarios"]}
    new = {row["shift_pct"]: row for row in refreshed["scenarios"]}

    header = (
        f"\n{'shift':>6} {'rev old':>10} {'rev new':>10} {'delta':>9} "
        f"{'pov old':>9} {'pov new':>9} {'delta pp':>9} "
        f"{'gini old':>9} {'gini new':>9}"
    )
    print(header)
    print("-" * (len(header) - 1))
    for pct in sorted(set(old) & set(new)):
        a, b = old[pct], new[pct]
        print(
            f"{pct:>5}% "
            f"{revenue(a):>+10.1f} {revenue(b):>+10.1f} "
            f"{revenue(b) - revenue(a):>+9.1f} "
            f"{a['spm_poverty_rate']:>9.2%} {b['spm_poverty_rate']:>9.2%} "
            f"{(b['spm_poverty_rate'] - a['spm_poverty_rate']) * 100:>+9.2f} "
            f"{a['net_gini']:>9.4f} {b['net_gini']:>9.4f}"
        )

    print("\nPoverty and Gini are LEVELS, which move with threshold revisions and")
    print("calibration; the sweep's own baseline is the 0% row in each vintage.")

    print(f"\n{'shift':>6} {'pov vs own 0% (old)':>21} {'pov vs own 0% (new)':>21}")
    print("-" * 50)
    base_old = old[0]["spm_poverty_rate"]
    base_new = new[0]["spm_poverty_rate"]
    for pct in sorted(set(old) & set(new)):
        print(
            f"{pct:>5}% "
            f"{(old[pct]['spm_poverty_rate'] - base_old) * 100:>+20.2f} "
            f"{(new[pct]['spm_poverty_rate'] - base_new) * 100:>+20.2f}"
        )
    print("\nIf these two columns agree, the vintage change moved levels but left")
    print("the modelled effect of the shift intact.")


if __name__ == "__main__":
    main()
