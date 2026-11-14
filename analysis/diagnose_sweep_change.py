"""Split the sweep rerun's change from the published sweep into its sources.

The published sweep (``src/data/shiftSweepData.json`` on main) ran on the
runtime and microdata the rerun pins: policyengine 5.0.1, policyengine-us
1.764.6 and build p. Its code differed from the rerun's in three ways that move
results, before this branch counted TANF once and counted health coverage:

- each shifted branch spread its state's fixed Medicaid spending over that
  branch's own enrollees (``medicaid_slcsp_state_denominator``), where
  ``health_tanf.price_medicaid_at_baseline`` now gives every branch the
  baseline's cost per enrollee;
- it counted Head Start and Early Head Start in household net income, which
  ``policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS`` now leaves out;
- its shift set only the built labor variables, ``employment_income`` and
  ``self_employment_income``, so the formulas that read their stored
  ``*_before_lsr`` inputs saw pre-shift earnings (see ``labor_inputs``).

From the repository root, on the pinned runtime:

    python -m analysis.diagnose_sweep_change run published OUT.json
    python -m analysis.diagnose_sweep_change run medicaid_at_baseline OUT.json
    python -m analysis.diagnose_sweep_change run head_start_excluded OUT.json
    python -m analysis.diagnose_sweep_change report RERUN.json PUBLISHED_RUN.json MEDICAID_AT_BASELINE_RUN.json HEAD_START_EXCLUDED_RUN.json [--published-ref REF]

``run`` runs ``run_shift_sweep`` at shifts of 0 and 10% with the published
code put back: ``published`` puts back all three differences,
``medicaid_at_baseline`` the last two and ``head_start_excluded`` only the
shift's. It saves the result with its decile impacts under
``metadata.baseline_facts``, where the sweep file keeps them. ``report``
checks that the ``published`` run reproduces the published sweep, then splits
each measure's change at those shifts into steps that add up to it, in this
order: pricing Medicaid at the baseline's cost per enrollee, excluding Head
Start, setting the stored labor inputs, counting TANF once and counting health
coverage. The deciles get one more
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
    "published": {"medicaid_at_baseline": False, "count_head_start": True, "stored_labor_inputs": False},
    "medicaid_at_baseline": {"medicaid_at_baseline": True, "count_head_start": True, "stored_labor_inputs": False},
    "head_start_excluded": {"medicaid_at_baseline": True, "count_head_start": False, "stored_labor_inputs": False},
}
#: The runs in order. Each code step is the change from one run to the next,
#: and the last step is the change from the last run to the rerun.
RUNS = ("published", "medicaid_at_baseline", "head_start_excluded")
CODE_STEPS = (
    ("medicaid_at_baseline", "Medicaid priced at baseline"),
    ("head_start", "Head Start left out"),
    ("labor_inputs", "Stored labor inputs"),
)
HEAD_START = ["early_head_start", "head_start"]
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


def _price_medicaid_over_own_enrollees(branch, denominator, year):
    """The published sweep's pricing: a branch spreads its state's spending over its own enrollees."""
    return None


def _set_built_labor_income_only(baseline, branch, variable, year, values):
    """The published shift's step: set the built labor variable alone."""
    import numpy as np

    branch.set_input(variable, year, np.asarray(values, dtype=float))
    return None


@contextlib.contextmanager
def configuration(name):
    """Put back the published code that ``name`` calls for while the block runs."""
    from . import health_tanf, labor_capital_shift, policyengine_runtime

    settings = CONFIGURATIONS[name]
    saved = (
        health_tanf.price_medicaid_at_baseline,
        policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS,
        labor_capital_shift.set_labor_income,
    )
    try:
        if not settings["medicaid_at_baseline"]:
            health_tanf.price_medicaid_at_baseline = _price_medicaid_over_own_enrollees
        if settings["count_head_start"]:
            policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS = ()
        if not settings["stored_labor_inputs"]:
            labor_capital_shift.set_labor_income = _set_built_labor_income_only
        yield settings
    finally:
        (
            health_tanf.price_medicaid_at_baseline,
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


def configuration_problems(runs):
    """Ways the runs' metadata show a configuration that didn't take.

    ``runs`` holds one run per name in ``RUNS``, in that order.
    """
    problems = []
    for payload, name in zip(runs, RUNS):
        excluded = [] if CONFIGURATIONS[name]["count_head_start"] else HEAD_START
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


def _code_steps(values):
    """Each code step's change, from one run's value to the next's."""
    return {key: after - before for (key, _), before, after in zip(CODE_STEPS, values, values[1:])}


def total_steps(published, runs, rerun, shift_pct=10):
    """The net revenue change at ``shift_pct``, in $B, from the published sweep to the rerun."""
    totals = [earlier_total(_row(payload, shift_pct)) for payload in (*runs, rerun)]
    row = _row(rerun, shift_pct)
    steps = {
        "published": earlier_total(_row(published, shift_pct)),
        "reproduced": totals[0],
        **_code_steps(totals),
        "tanf_counted_once": row["tanf_in_state_benefits_change_b"],
        "health": -row["health_change_b"],
        "rerun": row["total_rev_change_b"],
    }
    explained = [key for key, _ in CODE_STEPS] + ["tanf_counted_once", "health"]
    steps["unexplained"] = steps["rerun"] - (
        steps["reproduced"] + sum(steps[name] for name in explained)
    )
    return steps


def field_steps(runs, rerun, shift_pct=10):
    """Every field a code step moves at ``shift_pct``."""
    numbers = [_numbers(_row(payload, shift_pct)) for payload in (*runs, rerun)]
    out = []
    for field in sorted(set.intersection(*(set(n) for n in numbers))):
        values = [n[field] for n in numbers]
        steps = _code_steps(values)
        if max(abs(change) for change in steps.values()) > SHOWN[_kind(field)]:
            out.append({"field": field, "reproduced": values[0], **steps, "rerun": values[-1]})
    return out


def distribution_steps(published, runs, rerun, shift_pct):
    """Each distribution measure at ``shift_pct``, step by step."""
    rows = [_row(payload, shift_pct) for payload in (published, *runs, rerun)]
    out = []
    for field, label in DISTRIBUTION:
        if any(row.get(field) is None for row in rows):
            continue
        values = [row[field] for row in rows]
        out.append(
            {
                "field": field,
                "label": label,
                "published": values[0],
                "reproduced": values[1],
                **_code_steps(values[1:]),
                "rerun": values[-1],
            }
        )
    return out


def decile_steps(published, runs, rerun, shift_pct=10):
    """Each decile's change in mean net income at ``shift_pct``, in percent, step by step."""
    deciles = [_deciles_at(payload, shift_pct) for payload in (published, *runs, rerun)]
    out = []
    for decile in sorted(set.intersection(*(set(d) for d in deciles))):
        values = [d[decile]["pct_change"] for d in deciles]
        out.append(
            {
                "decile": decile,
                "published": values[0],
                "ties": values[1] - values[0],
                **_code_steps(values[1:]),
                "rerun": values[-1],
            }
        )
    return out


def _signed(value, spec):
    """``value`` with its sign, rounded first so float noise never prints -0."""
    digits = int(spec.rsplit(".", 1)[1].rstrip("f"))
    return f"{round(value, digits) + 0.0:+{spec}}"


def _header(names, label_column=True):
    """A table's header and alignment rows; numbers align right, a label column left."""
    align = ["---" if label_column and i == 0 else "---:" for i in range(len(names))]
    return ["| " + " | ".join(names) + " |", "|" + "|".join(align) + "|"]


def report(published, runs, rerun):
    """Markdown for the pull request."""
    labels = [label for _, label in CODE_STEPS]
    keys = [key for key, _ in CODE_STEPS]
    lines = []
    problems = configuration_problems(runs)
    gaps = reproduction_gaps(published, runs[0])
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
    steps = total_steps(published, runs, rerun)
    lines += ["", "Net revenue change at a 10% shift ($B, 2026):", ""]
    lines += _header(["Published", *labels, "TANF counted once", "Health coverage", "Rerun"], False)
    lines.append(
        "| "
        + " | ".join(
            [f"{steps['published']:,.2f}"]
            + [_signed(steps[name], ",.2f") for name in keys + ["tanf_counted_once", "health"]]
            + [f"{steps['rerun']:,.2f}"]
        )
        + " |"
    )
    lines += [
        "",
        f"The steps leave ${_signed(steps['unexplained'], '.4f')}B unexplained.",
        "",
        f"Fields the first {len(CODE_STEPS)} steps move by more than $0.05B (or 0.0001) at 10%:",
        "",
    ]
    lines += _header(["Field", "Published configuration", *labels, "Rerun"])
    for row in field_steps(runs, rerun):
        spec = ",.2f" if _kind(row["field"]) == "b" else ".4f"
        lines.append(
            f"| `{row['field']}` | {row['reproduced']:{spec}} | "
            + " | ".join(_signed(row[key], spec) for key in keys)
            + f" | {row['rerun']:{spec}} |"
        )
    for shift_pct in (0, 10):
        lines += ["", f"Distribution at a {shift_pct}% shift:", ""]
        lines += _header(["Measure", "Published", *labels, "Rerun"])
        for row in distribution_steps(published, runs, rerun, shift_pct):
            lines.append(
                f"| {row['label']} | {row['published']:.4f} | "
                + " | ".join(_signed(row[key], ".4f") for key in keys)
                + f" | {row['rerun']:.4f} |"
            )
    lines += ["", "Change in mean net income by decile at a 10% shift (%):", ""]
    lines += _header(["Decile", "Published", "Tie-breaking", *labels, "Rerun"], False)
    for row in decile_steps(published, runs, rerun):
        lines.append(
            f"| {row['decile']} | {row['published']:+.2f} | {_signed(row['ties'], '.2f')} | "
            + " | ".join(_signed(row[key], ".2f") for key in keys)
            + f" | {row['rerun']:+.2f} |"
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
    for name in RUNS:
        report_parser.add_argument(f"{name}_run", help=f"the {name} run's output")
    report_parser.add_argument(
        "--published-ref", default="origin/main", help="git ref whose site data hold the published sweep"
    )
    args = parser.parse_args(argv)
    if args.command == "run":
        run(args.configuration, args.out)
        return 0
    payloads = []
    for path in [args.rerun] + [getattr(args, f"{name}_run") for name in RUNS]:
        with open(path) as f:
            payloads.append(json.load(f))
    rerun, runs = payloads[0], payloads[1:]
    published = _load_old(None, args.published_ref)
    print(report(published, runs, rerun))
    if configuration_problems(runs) or reproduction_gaps(published, runs[0]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
