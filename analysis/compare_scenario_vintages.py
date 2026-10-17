"""Compare the AI scenario run on the Budget Lab's July inputs with the current one.

The Budget Lab revised "How potential AI futures would play out in the current
tax system" on 2026-10-09 (AI-Fiscal v1.0.1): the Moderate and Rapid 2030 labor
shares moved from 53.8% and 51.3% to 54.0% and 52.0%. This module repeated the
scenario grid with those inputs and with the CBO growth factor taken from the
stated CBO path, (1.022)(1.018)^4, instead of the four-decimal 1.0976 that the
July table had been inverted for. Both runs use the same runtime and data, so
every difference between them is one of those two input changes.

`vintage_rows` pairs the two files row by row; the tests in
`tests/test_scenario_vintages.py` hold the pairing to that claim, and `main`
prints the before/after table.

Usage:
    python -m analysis.compare_scenario_vintages [before.json] [after.json]
"""

from __future__ import annotations

import json
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
BEFORE_PATH = os.path.join(OUT, "ai_scenarios_v1_0_0_inputs.json")
AFTER_PATH = os.path.join(OUT, "ai_scenarios.json")

#: The July (v1.0.0) labor shares the revision replaced. Slow did not move.
JULY_TARGET_LABOR_SHARES = {"Slow": 0.550, "Moderate": 0.538, "Rapid": 0.513}

#: The four-decimal CBO growth factor this module used before the revision.
JULY_CBO_GROWTH_FACTOR = 1.0976


def load(path):
    with open(path) as handle:
        return json.load(handle)


def rows(doc):
    """(key, row) for the baseline, every grid cell and every sensitivity."""
    yield "baseline", doc["baseline"]
    for row in doc["scenarios"]:
        yield f"grid:{row['scenario']['label']}", row
    for group, items in (doc.get("sensitivities") or {}).items():
        for index, row in enumerate(items):
            yield f"{group}[{index}]:{row['scenario']['label']}", row


def vintage_rows(before, after):
    """Pair rows by key; raises if the two runs do not hold the same rows."""
    old = dict(rows(before))
    new = dict(rows(after))
    if list(old) != list(new):
        raise ValueError(
            "The two runs do not hold the same rows in the same order: "
            f"{sorted(set(old) ^ set(new))}"
        )
    return [(key, old[key], new[key]) for key in old]


def labor_share_moved(row):
    """True for a reallocated Moderate or Rapid cell, the cells the erratum moves."""
    scenario = row.get("scenario", {})
    if "target_labor_share" not in scenario or scenario.get("hold_shares_fixed"):
        return False
    return scenario["name"] in ("Moderate", "Rapid")


def _fmt_b(value):
    return f"{value:+.1f}"


def _fmt_pp(value):
    return f"{100 * value:+.2f}"


def table(before, after):
    """Markdown before/after table of the headline fields, one row per cell."""
    base_old = before["baseline"]
    base_new = after["baseline"]
    lines = [
        "| Cell | Labor share | Revenue $B | Payroll $B | SPM poverty Δ pp | Net Gini Δ |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key, old, new in vintage_rows(before, after):
        if key == "baseline":
            continue
        s_old, s_new = old["scenario"], new["scenario"]
        if s_new.get("hold_shares_fixed"):
            share = "fixed"
        else:
            share = (
                f"{100 * s_old['target_labor_share']:.1f}% → "
                f"{100 * s_new['target_labor_share']:.1f}%"
            )
        pov_old = old["spm_poverty_rate"] - base_old["spm_poverty_rate"]
        pov_new = new["spm_poverty_rate"] - base_new["spm_poverty_rate"]
        gini_old = old["net_gini"] - base_old["net_gini"]
        gini_new = new["net_gini"] - base_new["net_gini"]
        label = key.split(":", 1)[1]
        if not key.startswith("grid:"):
            label = f"{key.split('[')[0]}: {label}"
        lines.append(
            f"| {label} | {share} "
            f"| {_fmt_b(old['total_rev_change_b'])} → {_fmt_b(new['total_rev_change_b'])} "
            f"| {_fmt_b(old['payroll_change_b'])} → {_fmt_b(new['payroll_change_b'])} "
            f"| {_fmt_pp(pov_old)} → {_fmt_pp(pov_new)} "
            f"| {gini_old:+.4f} → {gini_new:+.4f} |"
        )
    return lines


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    before = load(argv[0] if len(argv) > 0 else BEFORE_PATH)
    after = load(argv[1] if len(argv) > 1 else AFTER_PATH)
    fp_old = before["metadata"]["runtime_fingerprint"]["digest"]
    fp_new = after["metadata"]["runtime_fingerprint"]["digest"]
    print(f"runtime fingerprint: {fp_old} → {fp_new}")
    print(
        "baseline identical:",
        json.dumps(before["baseline"], sort_keys=True)
        == json.dumps(after["baseline"], sort_keys=True),
    )
    unmoved = [
        abs(new["total_rev_change_b"] - old["total_rev_change_b"])
        for key, old, new in vintage_rows(before, after)
        if key != "baseline" and not labor_share_moved(new)
    ]
    print(f"largest revenue move in cells the erratum does not touch: {max(unmoved):.4f} $B")
    print()
    for line in table(before, after):
        print(line)


if __name__ == "__main__":
    main()
