"""Check a rerun of the US income-shift sweep and split its change from an earlier run.

From the repository root:

    python -m analysis.compare_shift_sweeps NEW.json
        [--old OLD.json | --old-ref REF] [--expect-commit SHA] [--state CA]

``check_sweep`` tests a sweep that counts health coverage and TANF against the
identities that ``analysis/fiscal.py`` and ``analysis/compute_shift_sweep.py``
build into it, and returns every breach it finds. ``decompose`` splits each
shift's change in the total from an earlier run that counted neither into
three parts that add up to the change:

* ``same_definition``: the rerun's total on the earlier definition
  (``total_rev_change_published_definition_b``) less the earlier run's total.
  It holds everything else that differs between the runs: code, engine and
  data.
* ``tanf_counted_once``: ``tanf_in_state_benefits_change_b``, the copy of
  each state TANF program that ``household_state_benefits`` also lists, at the
  full amount for every eligible family. The earlier definition subtracts it
  on top of ``tanf``.
* ``health``: minus ``health_change_b``, what governments spend on health
  coverage.

``decompose_state`` splits one state's chart total the same way, with the TANF
charged to its state beyond that copy (``tanf_state_charge_change_b``) in place
of the copy.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DATA = "src/data/shiftSweepData.json"

SHIFT_GRID = list(range(0, 101, 10))

#: Row fields a sweep carries once it counts health coverage and TANF.
ROW_FIELDS = (
    "revenue_change_b",
    "total_rev_change_b",
    "total_rev_change_excluding_health_b",
    "total_rev_change_published_definition_b",
    "health_change_b",
    "federal_health_change_b",
    "state_health_change_b",
    "state_only_coverage_change_b",
    "healthier_oregon_overlap_change_b",
    "tanf_change_b",
    "tanf_state_charge_change_b",
    "tanf_in_state_benefits_change_b",
    "taxes_outside_charts_change_b",
    "chart_identity_residual_b",
)

#: Fields each state's row carries.
STATE_FIELDS = (
    "state_tax_before_refundable_credits_change_b",
    "state_refundable_credits_change_b",
    "state_benefits_change_b",
    "state_net_change_b",
    "state_net_excluding_health_tanf_change_b",
    "state_health_change_b",
    "federal_health_change_b",
    "health_change_b",
    "state_only_coverage_change_b",
    "healthier_oregon_overlap_change_b",
    "tanf_change_b",
    "tanf_state_charge_change_b",
    "tanf_in_state_benefits_change_b",
)

#: National row fields that add up the same field across the states' rows.
STATE_SUMS = (
    "state_tax_before_refundable_credits_change_b",
    "state_refundable_credits_change_b",
    "state_benefits_change_b",
    "tanf_change_b",
    "tanf_state_charge_change_b",
    "tanf_in_state_benefits_change_b",
    "state_health_change_b",
    "federal_health_change_b",
    "health_change_b",
    "state_only_coverage_change_b",
    "healthier_oregon_overlap_change_b",
)

#: Largest chart identity residual check_sweep accepts, in $B. policyengine-us
#: adds float32 values, so the identity holds to about a millionth of the
#: aggregates (analysis/tests/test_health_tanf.py's _float32_slack): tens of
#: millions of dollars on the full dataset. A band that left out a program
#: would miss by billions.
CHART_RESIDUAL_LIMIT_B = 0.1

#: Tolerance for the identities the sweep builds in float64, in $B ($1,000).
EXACT_B = 1e-6


def _close(a, b, tol=EXACT_B):
    return abs(a - b) <= tol


def _check_state(label, code, d):
    missing = [field for field in STATE_FIELDS if d.get(field) is None]
    if missing:
        return [f"{label} {code}: no {', '.join(missing)}"]
    problems = []
    excluding = (
        d["state_tax_before_refundable_credits_change_b"]
        - d["state_refundable_credits_change_b"]
        - d["state_benefits_change_b"]
    )
    if not _close(d["state_net_excluding_health_tanf_change_b"], excluding):
        problems.append(
            f"{label} {code}: state_net_excluding_health_tanf_change_b "
            f"{d['state_net_excluding_health_tanf_change_b']:.6f} differs from tax less "
            f"credits and benefits, {excluding:.6f}"
        )
    net = excluding - d["tanf_state_charge_change_b"] - d["state_health_change_b"]
    if not _close(d["state_net_change_b"], net):
        problems.append(
            f"{label} {code}: state_net_change_b {d['state_net_change_b']:.6f} differs "
            f"from its parts, {net:.6f}"
        )
    charge = d["tanf_change_b"] - d["tanf_in_state_benefits_change_b"]
    if not _close(d["tanf_state_charge_change_b"], charge):
        problems.append(
            f"{label} {code}: tanf_state_charge_change_b "
            f"{d['tanf_state_charge_change_b']:.6f} differs from TANF less the TANF "
            f"copy in state benefits, {charge:.6f}"
        )
    health = d["federal_health_change_b"] + d["state_health_change_b"]
    if not _close(d["health_change_b"], health):
        problems.append(
            f"{label} {code}: health_change_b {d['health_change_b']:.6f} differs from "
            f"federal plus state health spending, {health:.6f}"
        )
    return problems


def _check_row(row):
    label = f"{row.get('shift_pct')}%"
    missing = [field for field in ROW_FIELDS if row.get(field) is None]
    if missing:
        return [f"{label}: no {', '.join(missing)}"]
    problems = []
    if row["shift_pct"] == 0:
        nonzero = [field for field in ROW_FIELDS if not _close(row[field], 0.0)]
        if nonzero:
            problems.append(f"0%: nonzero {', '.join(nonzero)}")
        return problems
    identities = (
        ("revenue_change_b", row["total_rev_change_b"], "total_rev_change_b"),
        (
            "total_rev_change_b",
            row["total_rev_change_excluding_health_b"] - row["health_change_b"],
            "the total without health less health spending",
        ),
        (
            "total_rev_change_excluding_health_b",
            row["total_rev_change_published_definition_b"]
            + row["tanf_in_state_benefits_change_b"],
            "the earlier definition's total plus the TANF copy in state benefits",
        ),
        (
            "health_change_b",
            row["federal_health_change_b"] + row["state_health_change_b"],
            "federal plus state health spending",
        ),
        (
            "tanf_state_charge_change_b",
            row["tanf_change_b"] - row["tanf_in_state_benefits_change_b"],
            "TANF less the TANF copy in state benefits",
        ),
    )
    for field, expected, description in identities:
        if not _close(row[field], expected):
            problems.append(
                f"{label}: {field} {row[field]:.6f} differs from {description}, "
                f"{expected:.6f}"
            )
    residual = row["chart_identity_residual_b"]
    if abs(residual) >= CHART_RESIDUAL_LIMIT_B:
        problems.append(
            f"{label}: chart identity residual {residual:+.4f}B reaches the "
            f"{CHART_RESIDUAL_LIMIT_B}B limit"
        )
    states = row.get("state_deltas") or {}
    if not states:
        return problems + [f"{label}: no state rows"]
    for code, d in states.items():
        problems.extend(_check_state(label, code, d))
    for field in STATE_SUMS:
        value = row.get(field)
        if value is None:
            problems.append(f"{label}: no {field}")
            continue
        summed = sum(d.get(field) or 0.0 for d in states.values())
        if not _close(value, summed):
            problems.append(
                f"{label}: {field} {value:.6f} differs from the states' "
                f"{field} added up, {summed:.6f}"
            )
    return problems


def check_sweep(payload, expect_commit=None):
    """Every identity ``payload`` breaks, as messages; an empty list if none."""
    problems = []
    rows = payload.get("scenarios") or []
    shifts = [row.get("shift_pct") for row in rows]
    if shifts != SHIFT_GRID:
        problems.append(f"shift grid {shifts}, expected {SHIFT_GRID}")
    for row in rows:
        problems.extend(_check_row(row))
    metadata = payload.get("metadata") or {}
    bundle = metadata.get("policyengine_bundle") or {}
    if "net_income_excluded_benefits" not in bundle:
        problems.append(
            "metadata.policyengine_bundle records no net_income_excluded_benefits"
        )
    if not (metadata.get("baseline_facts") or {}).get("decile_impacts"):
        problems.append("metadata.baseline_facts carries no decile_impacts")
    if not metadata.get("health_tanf_programs"):
        problems.append("metadata carries no health_tanf_programs")
    if expect_commit is not None:
        commit = str(metadata.get("code_commit") or "")
        if not (commit and commit.startswith(expect_commit)):
            problems.append(
                f"metadata.code_commit {commit or 'missing'} doesn't match {expect_commit}"
            )
    return problems


def earlier_total(row):
    """A row's total on the definition the site used before it counted health and TANF."""
    value = row.get("total_rev_change_published_definition_b")
    return row["revenue_change_b"] if value is None else value


def earlier_state_total(d):
    """A state's chart total on the definition the site used before it counted health and TANF."""
    value = d.get("state_net_excluding_health_tanf_change_b")
    if value is not None:
        return value
    return (
        d["state_tax_before_refundable_credits_change_b"]
        - d["state_refundable_credits_change_b"]
        - d["state_benefits_change_b"]
    )


def _with_unexplained(part, earlier, parts):
    part["unexplained"] = part["total"] - (earlier + sum(part[name] for name in parts))
    return part


def decompose(new, old):
    """Each shift's change in the total from ``old`` to ``new``, in $B, by part."""
    old_rows = {row["shift_pct"]: row for row in old["scenarios"]}
    out = []
    for row in new["scenarios"]:
        earlier = earlier_total(old_rows[row["shift_pct"]])
        part = {
            "shift_pct": row["shift_pct"],
            "earlier_total": earlier,
            "same_definition": row["total_rev_change_published_definition_b"] - earlier,
            "tanf_counted_once": row["tanf_in_state_benefits_change_b"],
            "health": -row["health_change_b"],
            "total": row["total_rev_change_b"],
        }
        out.append(
            _with_unexplained(
                part, earlier, ("same_definition", "tanf_counted_once", "health")
            )
        )
    return out


def decompose_state(new, old, code):
    """Each shift's change in ``code``'s chart total from ``old`` to ``new``, in $B, by part."""
    old_rows = {row["shift_pct"]: row for row in old["scenarios"]}
    out = []
    for row in new["scenarios"]:
        d = (row.get("state_deltas") or {}).get(code)
        before = (old_rows[row["shift_pct"]].get("state_deltas") or {}).get(code)
        if d is None or before is None:
            continue
        earlier = earlier_state_total(before)
        part = {
            "shift_pct": row["shift_pct"],
            "earlier_total": earlier,
            "same_definition": d["state_net_excluding_health_tanf_change_b"] - earlier,
            "tanf": -d["tanf_state_charge_change_b"],
            "health": -d["state_health_change_b"],
            "total": d["state_net_change_b"],
        }
        out.append(
            _with_unexplained(part, earlier, ("same_definition", "tanf", "health"))
        )
    return out


def chart_totals(row):
    """The federal chart, the state charts and the taxes outside them, in $B.

    The state charts add up each state's ``state_net_change_b``; the federal
    chart is what the total leaves after them, the taxes outside the charts and
    the chart identity residual. ``src/utils/sweepRevenue.test.js`` checks the
    federal chart's bands against the same total.
    """
    states = sum(
        d["state_net_change_b"] for d in (row.get("state_deltas") or {}).values()
    )
    outside = row["taxes_outside_charts_change_b"]
    federal = (
        row["total_rev_change_b"] - states - outside - row["chart_identity_residual_b"]
    )
    return {"federal": federal, "states": states, "outside": outside}


#: Metadata entries that hold results or nested records rather than run facts.
_NOT_RUN_FACTS = ("policyengine_bundle", "baseline_facts", "health_tanf_programs")


def metadata_differences(new, old):
    """Run facts whose value differs between ``old`` and ``new``, as (key, old, new).

    Covers the top-level metadata and the ``policyengine_bundle`` record.
    """
    old_meta, new_meta = old.get("metadata") or {}, new.get("metadata") or {}
    scopes = (
        ("metadata", old_meta, new_meta),
        (
            "policyengine_bundle",
            old_meta.get("policyengine_bundle") or {},
            new_meta.get("policyengine_bundle") or {},
        ),
    )
    out = []
    for scope, a, b in scopes:
        for key in sorted(set(a) | set(b)):
            if scope == "metadata" and key in _NOT_RUN_FACTS:
                continue
            if a.get(key) != b.get(key):
                out.append((f"{scope}.{key}", a.get(key), b.get(key)))
    return out


def _b(value):
    return f"{value:+,.1f}"


def _short(value, width=70):
    text = json.dumps(value) if not isinstance(value, str) else value
    return text if len(text) <= width else text[: width - 1] + "…"


def report(new, old, state="CA"):
    """Markdown tables for a pull request: the rerun, its change from ``old``, and one state."""
    lines = [
        (
            "Rerun by shift ($B, 2026). The health and TANF columns flip the sign "
            "of the spending change, as the charts do."
        ),
        "",
    ]
    lines.append(
        "| Shift | Total | Federal chart | State charts | Taxes outside the charts "
        "| Federal health | State health | TANF | Without health | Earlier definition |"
    )
    lines.append("|" + "---:|" * 10)
    for row in new["scenarios"]:
        charts = chart_totals(row)
        lines.append(
            f"| {row['shift_pct']}% | {_b(row['total_rev_change_b'])} "
            f"| {_b(charts['federal'])} | {_b(charts['states'])} | {_b(charts['outside'])} "
            f"| {_b(-row['federal_health_change_b'])} | {_b(-row['state_health_change_b'])} "
            f"| {_b(-row['tanf_change_b'])} | {_b(row['total_rev_change_excluding_health_b'])} "
            f"| {_b(row['total_rev_change_published_definition_b'])} |"
        )
    trough = min(new["scenarios"], key=lambda row: row["total_rev_change_b"])
    lines += [
        "",
        f"Lowest total: {_b(trough['total_rev_change_b'])}B at a {trough['shift_pct']}% shift.",
        "",
        "Change from the earlier run ($B):",
        "",
        (
            "| Shift | Earlier run | Same definition | TANF counted once "
            "| Health coverage | Rerun |"
        ),
        "|" + "---:|" * 6,
    ]
    for part in decompose(new, old):
        lines.append(
            f"| {part['shift_pct']}% | {_b(part['earlier_total'])} "
            f"| {_b(part['same_definition'])} | {_b(part['tanf_counted_once'])} "
            f"| {_b(part['health'])} | {_b(part['total'])} |"
        )
    if state:
        lines += [
            "",
            f"{state} chart ($B):",
            "",
            "| Shift | Earlier run | Same definition | TANF | Health coverage | Rerun |",
            "|" + "---:|" * 6,
        ]
        for part in decompose_state(new, old, state):
            lines.append(
                f"| {part['shift_pct']}% | {_b(part['earlier_total'])} "
                f"| {_b(part['same_definition'])} | {_b(part['tanf'])} "
                f"| {_b(part['health'])} | {_b(part['total'])} |"
            )
    differences = metadata_differences(new, old)
    if differences:
        lines += ["", "Run metadata that differs (earlier → rerun):", ""]
        lines += [f"- `{key}`: {_short(a)} → {_short(b)}" for key, a, b in differences]
    return "\n".join(lines)


def _load_old(path, ref):
    if path:
        with open(path) as f:
            return json.load(f)
    text = subprocess.run(
        ["git", "show", f"{ref}:{SITE_DATA}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("new", help="the rerun's sweep JSON")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--old", help="an earlier sweep JSON")
    source.add_argument(
        "--old-ref",
        default="origin/main",
        help=f"git ref whose {SITE_DATA} holds the earlier run (default origin/main)",
    )
    parser.add_argument(
        "--expect-commit", help="the analysis commit the rerun should record"
    )
    parser.add_argument("--state", default="CA", help="state to split (default CA)")
    args = parser.parse_args(argv)
    with open(args.new) as f:
        new = json.load(f)
    old = _load_old(args.old, args.old_ref)
    problems = check_sweep(new, expect_commit=args.expect_commit)
    residuals = [
        abs(row.get("chart_identity_residual_b") or 0.0) for row in new["scenarios"]
    ]
    print(f"Largest chart identity residual: {max(residuals):.4f}B")
    if problems:
        print(f"{len(problems)} problems:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("Every identity holds.\n")
    print(report(new, old, args.state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
