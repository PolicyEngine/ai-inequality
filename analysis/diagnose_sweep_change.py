"""Split the sweep rerun's change from the published sweep into its sources.

The published sweep (``src/data/shiftSweepData.json`` on main) ran on the
runtime and microdata the rerun pins: policyengine 5.0.1, policyengine-us
1.764.6 and build p. Its code differed from the rerun's in two ways that move
results, before this branch counted TANF once and counted health coverage:

- it counted Head Start and Early Head Start in household net income, which
  ``policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS`` now leaves out;
- its shift set only the built labor variables, ``employment_income`` and
  ``self_employment_income``, so the formulas that read their stored
  ``*_before_lsr`` inputs saw pre-shift earnings (see ``labor_inputs``).

From the repository root, on the pinned runtime:

    python -m analysis.diagnose_sweep_change run published OUT.json
    python -m analysis.diagnose_sweep_change run head_start_excluded OUT.json
    python -m analysis.diagnose_sweep_change report RERUN.json PUBLISHED_RUN.json HEAD_START_RUN.json [--published-ref REF]

``run`` runs ``run_shift_sweep`` at shifts of 0 and 10% with the published
code put back: ``published`` puts back both differences, and
``head_start_excluded`` only the shift's. It saves the result with its decile
impacts under ``metadata.baseline_facts``, where the sweep file keeps them.
``report`` checks that the ``published`` run reproduces the published sweep,
then splits each measure's change at those shifts into steps that add up to
it, in this order: excluding Head Start, setting the stored labor inputs,
counting TANF once and counting health coverage. The deciles get one more
step first, for the published deciles' older tie-breaking.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import tempfile
from pathlib import Path

from .compare_shift_sweeps import _deciles_at, _load_old, earlier_state_total, earlier_total

SHIFT_LEVELS = (0.0, 0.1)
CONFIGURATIONS = {
    "published": {"count_head_start": True, "stored_labor_inputs": False},
    "head_start_excluded": {"count_head_start": False, "stored_labor_inputs": False},
}
#: A field moves in a step when it changes by more than this: $0.05B for
#: fields in $B, and 0.0001 for rates, shares and Gini coefficients.
SHOWN = {"b": 0.05, "rate": 1e-4}
#: The reproduction allows float noise only: $1,000 for fields in $B and
#: 1e-9 for the rest, plus one part in 10^12 of the value.
REPRODUCED = {"b": 1e-6, "rate": 1e-9}
#: Fields this branch redefined to count health coverage and TANF. The
#: published values match ``total_rev_change_published_definition_b`` and each
#: state's ``state_net_excluding_health_tanf_change_b``.
REDEFINED = ("total_rev_change_b", "revenue_change_b")
REDEFINED_STATE = ("state_net_change_b",)
DISTRIBUTION = (
    ("net_gini", "Net Gini"),
    ("net_gini_including_health_benefits", "Net Gini with health benefits"),
    ("market_gini", "Market Gini"),
    ("net_top_10_share", "Net top 10% share"),
    ("net_top_1_share", "Net top 1% share"),
    ("net_top_0_1_share", "Net top 0.1% share"),
    ("spm_poverty_rate", "SPM poverty rate"),
)


def _set_built_labor_income_only(baseline, branch, variable, year, values):
    """The published shift's step: set the built labor variable alone."""
    import numpy as np

    branch.set_input(variable, year, np.asarray(values, dtype=float))
    return None


@contextlib.contextmanager
def configuration(name):
    """Put back the published code that ``name`` calls for while the block runs."""
    from . import labor_capital_shift, policyengine_runtime

    settings = CONFIGURATIONS[name]
    saved = (
        policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS,
        labor_capital_shift.set_labor_income,
    )
    try:
        if settings["count_head_start"]:
            policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS = ()
        if not settings["stored_labor_inputs"]:
            labor_capital_shift.set_labor_income = _set_built_labor_income_only
        yield settings
    finally:
        (
            policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS,
            labor_capital_shift.set_labor_income,
        ) = saved


def run(name, out_path):
    """Run the sweep at 0 and 10% in configuration ``name``; save it to ``out_path``."""
    from .compute_decile_impacts import decile_impacts
    from .compute_shift_sweep import run_shift_sweep

    with tempfile.TemporaryDirectory(prefix="diagnose_sweep_change-") as folder:
        with configuration(name) as settings:
            result = run_shift_sweep(
                shift_levels=list(SHIFT_LEVELS), microdata_output_dir=folder
            )
        facts = result["metadata"].setdefault("baseline_facts", {})
        facts["decile_impacts"] = decile_impacts(folder)
    result["metadata"]["diagnose_configuration"] = {"name": name, **settings}
    Path(out_path).write_text(json.dumps(result, indent=2))
    return result


def _row(payload, shift_pct):
    return {row["shift_pct"]: row for row in payload["scenarios"]}[shift_pct]


def _kind(field):
    return "b" if field.endswith("_b") else "rate"


def _numbers(row):
    return {
        field: value
        for field, value in row.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        and field != "shift_pct"
    }


def _comparable(row):
    """A row's numbers, states included, on the published definitions."""
    numbers = _numbers(row)
    numbers["total_rev_change_published_definition_b"] = earlier_total(row)
    for field in REDEFINED:
        numbers.pop(field, None)
    for code, state in (row.get("state_deltas") or {}).items():
        values = _numbers(state)
        values["state_net_excluding_health_tanf_change_b"] = earlier_state_total(state)
        for field in REDEFINED_STATE:
            values.pop(field, None)
        numbers.update({f"state_deltas.{code}.{field}": value for field, value in values.items()})
    return numbers


def reproduction_gaps(published, published_run, shift_pcts=(0, 10)):
    """Each value the ``published`` run fails to reproduce, with both values.

    It compares every number both rows carry, each state's included, and
    compares the redefined totals on the published definition.
    """
    gaps = []
    for shift_pct in shift_pcts:
        before = _comparable(_row(published, shift_pct))
        again = _comparable(_row(published_run, shift_pct))
        for field in sorted(before.keys() & again.keys()):
            allowed = REPRODUCED[_kind(field)] + 1e-12 * abs(before[field])
            if abs(again[field] - before[field]) > allowed:
                gaps.append(
                    {
                        "shift_pct": shift_pct,
                        "field": field,
                        "published": before[field],
                        "reproduced": again[field],
                    }
                )
    return gaps


def configuration_problems(published_run, head_start_run):
    """Ways the two runs' metadata show a configuration that didn't take."""
    problems = []
    for payload, name, excluded in (
        (published_run, "published", []),
        (head_start_run, "head_start_excluded", ["early_head_start", "head_start"]),
    ):
        metadata = payload["metadata"]
        recorded = (metadata.get("diagnose_configuration") or {}).get("name")
        if recorded != name:
            problems.append(f"the {name} run records configuration {recorded!r}")
        bundle = metadata.get("policyengine_bundle") or {}
        if bundle.get("net_income_excluded_benefits") != excluded:
            problems.append(
                f"the {name} run left {bundle.get('net_income_excluded_benefits')} "
                f"out of net income, not {excluded}"
            )
    return problems


def total_steps(published, published_run, head_start_run, rerun, shift_pct=10):
    """The net revenue change at ``shift_pct``, in $B, from the published sweep to the rerun."""
    reproduced = earlier_total(_row(published_run, shift_pct))
    head_start = earlier_total(_row(head_start_run, shift_pct))
    row = _row(rerun, shift_pct)
    steps = {
        "published": earlier_total(_row(published, shift_pct)),
        "reproduced": reproduced,
        "head_start": head_start - reproduced,
        "labor_inputs": earlier_total(row) - head_start,
        "tanf_counted_once": row["tanf_in_state_benefits_change_b"],
        "health": -row["health_change_b"],
        "rerun": row["total_rev_change_b"],
    }
    steps["unexplained"] = steps["rerun"] - (
        steps["reproduced"]
        + sum(steps[name] for name in ("head_start", "labor_inputs", "tanf_counted_once", "health"))
    )
    return steps


def field_steps(published_run, head_start_run, rerun, shift_pct=10):
    """Every field the Head Start or labor-input step moves at ``shift_pct``."""
    first = _numbers(_row(published_run, shift_pct))
    second = _numbers(_row(head_start_run, shift_pct))
    third = _numbers(_row(rerun, shift_pct))
    out = []
    for field in sorted(first.keys() & second.keys() & third.keys()):
        head_start, labor = second[field] - first[field], third[field] - second[field]
        if max(abs(head_start), abs(labor)) > SHOWN[_kind(field)]:
            out.append(
                {
                    "field": field,
                    "reproduced": first[field],
                    "head_start": head_start,
                    "labor_inputs": labor,
                    "rerun": third[field],
                }
            )
    return out


def distribution_steps(published, published_run, head_start_run, rerun, shift_pct):
    """Each distribution measure at ``shift_pct``, step by step."""
    rows = [_row(payload, shift_pct) for payload in (published, published_run, head_start_run, rerun)]
    out = []
    for field, label in DISTRIBUTION:
        if any(row.get(field) is None for row in rows):
            continue
        before, again, head_start, after = (row[field] for row in rows)
        out.append(
            {
                "field": field,
                "label": label,
                "published": before,
                "reproduced": again,
                "head_start": head_start - again,
                "labor_inputs": after - head_start,
                "rerun": after,
            }
        )
    return out


def decile_steps(published, published_run, head_start_run, rerun, shift_pct=10):
    """Each decile's change in mean net income at ``shift_pct``, in percent, step by step."""
    deciles = [_deciles_at(payload, shift_pct) for payload in (published, published_run, head_start_run, rerun)]
    out = []
    for decile in sorted(set.intersection(*(set(d) for d in deciles))):
        before, again, head_start, after = (d[decile]["pct_change"] for d in deciles)
        out.append(
            {
                "decile": decile,
                "published": before,
                "ties": again - before,
                "head_start": head_start - again,
                "labor_inputs": after - head_start,
                "rerun": after,
            }
        )
    return out


def _signed(value, spec):
    """``value`` with its sign, rounded first so float noise never prints -0."""
    digits = int(spec.rsplit(".", 1)[1].rstrip("f"))
    return f"{round(value, digits) + 0.0:+{spec}}"


def report(published, published_run, head_start_run, rerun):
    """Markdown for the pull request."""
    lines = []
    problems = configuration_problems(published_run, head_start_run)
    gaps = reproduction_gaps(published, published_run)
    if problems:
        lines += ["Configuration problems:", ""] + [f"- {problem}" for problem in problems] + [""]
    if gaps:
        lines += [f"The published configuration misses {len(gaps)} of the published values:", ""]
        lines += [
            f"- {gap['shift_pct']}%: `{gap['field']}` {gap['published']!r} published, {gap['reproduced']!r} reproduced"
            for gap in gaps
        ]
    else:
        lines.append(
            "The published configuration reproduces every published value at 0% and 10% "
            "(within $1,000, or 1e-9 for rates)."
        )
    steps = total_steps(published, published_run, head_start_run, rerun)
    lines += [
        "",
        "Net revenue change at a 10% shift ($B, 2026):",
        "",
        "| Published | Head Start left out | Stored labor inputs | TANF counted once | Health coverage | Rerun |",
        "|---:|---:|---:|---:|---:|---:|",
        "| "
        + " | ".join(
            [f"{steps['published']:,.2f}"]
            + [_signed(steps[name], ",.2f") for name in ("head_start", "labor_inputs", "tanf_counted_once", "health")]
            + [f"{steps['rerun']:,.2f}"]
        )
        + " |",
        "",
        f"The steps leave ${_signed(steps['unexplained'], '.4f')}B unexplained.",
        "",
        "Fields the first two steps move by more than $0.05B (or 0.0001) at 10%:",
        "",
        "| Field | Published configuration | Head Start left out | Stored labor inputs | Rerun |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in field_steps(published_run, head_start_run, rerun):
        spec = ",.2f" if _kind(row["field"]) == "b" else ".4f"
        lines.append(
            f"| `{row['field']}` | {row['reproduced']:{spec}} | {_signed(row['head_start'], spec)} "
            f"| {_signed(row['labor_inputs'], spec)} | {row['rerun']:{spec}} |"
        )
    for shift_pct in (0, 10):
        lines += [
            "",
            f"Distribution at a {shift_pct}% shift:",
            "",
            "| Measure | Published | Head Start left out | Stored labor inputs | Rerun |",
            "|---|---:|---:|---:|---:|",
        ]
        for row in distribution_steps(published, published_run, head_start_run, rerun, shift_pct):
            lines.append(
                f"| {row['label']} | {row['published']:.4f} | {_signed(row['head_start'], '.4f')} "
                f"| {_signed(row['labor_inputs'], '.4f')} | {row['rerun']:.4f} |"
            )
    lines += [
        "",
        "Change in mean net income by decile at a 10% shift (%):",
        "",
        "| Decile | Published | Tie-breaking | Head Start left out | Stored labor inputs | Rerun |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in decile_steps(published, published_run, head_start_run, rerun):
        lines.append(
            f"| {row['decile']} | {row['published']:+.2f} | {_signed(row['ties'], '.2f')} "
            f"| {_signed(row['head_start'], '.2f')} | {_signed(row['labor_inputs'], '.2f')} | {row['rerun']:+.2f} |"
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="run the sweep at shifts of 0 and 10%% in one configuration")
    run_parser.add_argument("configuration", choices=sorted(CONFIGURATIONS))
    run_parser.add_argument("out")
    report_parser = commands.add_parser("report", help="split the rerun's change into its sources")
    report_parser.add_argument("rerun")
    report_parser.add_argument("published_run")
    report_parser.add_argument("head_start_run")
    report_parser.add_argument(
        "--published-ref", default="origin/main", help="git ref whose site data hold the published sweep"
    )
    args = parser.parse_args(argv)
    if args.command == "run":
        run(args.configuration, args.out)
        return 0
    payloads = []
    for path in (args.rerun, args.published_run, args.head_start_run):
        with open(path) as f:
            payloads.append(json.load(f))
    rerun, published_run, head_start_run = payloads
    published = _load_old(None, args.published_ref)
    print(report(published, published_run, head_start_run, rerun))
    if configuration_problems(published_run, head_start_run) or reproduction_gaps(published, published_run):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
