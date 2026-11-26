"""Write src/data/revenueLines.json, the revenue lines the policy-analysis page draws.

Reads src/data/shiftSweepData.json, which compute_shift_sweep.py writes, and
stores, for each shift from 0% to 100% in 10-point steps:

* the federal line and the states combined, each counting and not counting
  health coverage;
* all governments, counting (``total_rev_change_b``) and not counting
  (``total_rev_change_excluding_health_b``) health coverage;
* the taxes outside both lines (``taxes_outside_charts_change_b``) and its
  parts: the Additional Medicare Tax, workers' state payroll taxes and local
  taxes on occupations;
* health spending by payer (``federal_health_change_b`` and
  ``state_health_change_b``);
* California's income and use tax after refundable credits, and its net
  counting health coverage.

The counting lines mirror ``src/utils/sweepRevenue.js`` with
``withHealthTanf=true``: the federal line is ``federalRow(scenario,
true).revenue``, a state's is ``stateDeltaRow(delta, true).revenue``, and the
states combined add up every state in ``state_deltas``. A line not counting
health coverage is the counting line plus that government's own health
spending: ``federal_health_change_b`` for the federal line and each state's
``state_health_change_b`` for the states. It never uses ``federalRow(_,
false)`` or ``state_net_excluding_health_tanf_change_b``, which also drop
TANF.

Unlike the JavaScript, which reads a missing field as zero, this reads every
field strictly: a missing or null field raises.

Standard library only, so CI's analysis job runs it without the engine.

Usage, from the repository root:
    python3 -I analysis/revenue_lines.py           # write the file
    python3 -I analysis/revenue_lines.py --check   # fail if it is stale
"""

import argparse
import hashlib
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP = "src/data/shiftSweepData.json"
OUTPUT = "src/data/revenueLines.json"

SHIFT_GRID = list(range(0, 101, 10))
DECIMALS = 6

#: The state whose revenue the page draws on its own.
CALIFORNIA = "CA"

#: Run facts copied from the sweep's metadata. The sweep's dataset fields keep
#: Microcosm's pre-August release ids, which the site never prints, so they
#: stay out.
PROVENANCE_FIELDS = (
    "code_commit",
    "country_model_version",
    "policyengine_us_version",
    "year",
)

#: Row fields copied as they are.
COPIED_FIELDS = (
    "additional_medicare_tax_change_b",
    "employee_state_payroll_tax_change_b",
    "federal_health_change_b",
    "local_occupational_tax_change_b",
    "state_health_change_b",
    "taxes_outside_charts_change_b",
    "total_rev_change_b",
    "total_rev_change_excluding_health_b",
)

#: Row fields federalRow(scenario, true) reads.
FEDERAL_FIELDS = (
    "fed_income_tax_before_refundable_credits_change_b",
    "refundable_credits_change_b",
    "state_refundable_credits_change_b",
    "employer_payroll_change_b",
    "employee_ss_tax_change_b",
    "employee_medicare_tax_change_b",
    "self_employment_tax_change_b",
    "benefits_change_b",
    "state_benefits_change_b",
    "tanf_change_b",
    "federal_health_change_b",
)


class SweepError(ValueError):
    """The sweep lacks a field the lines need, or holds one they can't use."""


def field(record, key, where):
    """``record[key]`` as a float; raises SweepError if missing or not a number."""
    if not isinstance(record, dict) or key not in record:
        raise SweepError(f"{where}: no {key}")
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SweepError(f"{where}: {key} is {value!r}, not a number")
    if not math.isfinite(value):
        raise SweepError(f"{where}: {key} is {value!r}")
    return float(value)


def total(bands):
    """Add bands from zero in order, as sweepRevenue.js's withTotal does."""
    out = 0.0
    for value in bands:
        out += value
    return out


def federal_counting(row, where):
    """federalRow(row, true).revenue in sweepRevenue.js, in $B."""
    f = {key: field(row, key, where) for key in FEDERAL_FIELDS}
    income_tax = f["fed_income_tax_before_refundable_credits_change_b"] - (
        f["refundable_credits_change_b"] - f["state_refundable_credits_change_b"]
    )
    payroll = (
        f["employer_payroll_change_b"]
        + f["employee_ss_tax_change_b"]
        + f["employee_medicare_tax_change_b"]
        + f["self_employment_tax_change_b"]
    )
    benefits = (
        f["benefits_change_b"] - f["state_benefits_change_b"] - f["tanf_change_b"]
    )
    return total([income_tax, payroll, -benefits, -f["federal_health_change_b"]])


def state_income_tax(delta, where):
    """A state's income and use tax after refundable credits, in $B."""
    return field(
        delta, "state_tax_before_refundable_credits_change_b", where
    ) - field(delta, "state_refundable_credits_change_b", where)


def state_counting(delta, where):
    """stateDeltaRow(delta, true).revenue in sweepRevenue.js, in $B."""
    benefits = field(delta, "state_benefits_change_b", where) - field(
        delta, "tanf_in_state_benefits_change_b", where
    )
    return total(
        [
            state_income_tax(delta, where),
            -benefits,
            -field(delta, "tanf_change_b", where),
            -field(delta, "state_health_change_b", where),
        ]
    )


def rounded(value):
    """``value`` to DECIMALS places, with -0.0 written as 0.0."""
    out = round(value, DECIMALS)
    return 0.0 if out == 0 else out


def baseline_line(row):
    """The 0% row's lines. It is the baseline every change is measured from.

    compute_shift_sweep.py writes the 0% row with every change at 0.0 and no
    state rows, so every line is zero there. Raises if the row says otherwise.
    """
    where = "0%"
    deltas = row.get("state_deltas")
    if deltas not in ({}, None):
        raise SweepError(f"{where}: state rows {sorted(deltas)}, expected none")
    for key in FEDERAL_FIELDS + COPIED_FIELDS:
        if field(row, key, where) != 0.0:
            raise SweepError(f"{where}: {key} is {row[key]!r}, expected 0.0")
    line = {key: 0.0 for key in COPIED_FIELDS}
    line.update(
        {
            "california_income_and_use_tax_change_b": 0.0,
            "california_net_counting_health_change_b": 0.0,
            "federal_counting_health_change_b": 0.0,
            "federal_not_counting_health_change_b": 0.0,
            "shift_pct": 0,
            "states_counting_health_change_b": 0.0,
            "states_not_counting_health_change_b": 0.0,
        }
    )
    return line


def shift_line(row):
    """One nonzero shift's lines, unrounded."""
    shift = row["shift_pct"]
    where = f"{shift}%"
    deltas = row.get("state_deltas")
    if not isinstance(deltas, dict) or not deltas:
        raise SweepError(f"{where}: no state rows")
    if CALIFORNIA not in deltas:
        raise SweepError(f"{where}: no {CALIFORNIA} state row")

    federal = federal_counting(row, where)
    states = 0.0
    states_health = 0.0
    for code, delta in deltas.items():
        states += state_counting(delta, f"{where} {code}")
        states_health += field(delta, "state_health_change_b", f"{where} {code}")
    california = deltas[CALIFORNIA]
    line = {key: field(row, key, where) for key in COPIED_FIELDS}
    line.update(
        {
            "california_income_and_use_tax_change_b": state_income_tax(
                california, f"{where} {CALIFORNIA}"
            ),
            "california_net_counting_health_change_b": state_counting(
                california, f"{where} {CALIFORNIA}"
            ),
            "federal_counting_health_change_b": federal,
            "federal_not_counting_health_change_b": federal
            + line["federal_health_change_b"],
            "shift_pct": shift,
            "states_counting_health_change_b": states,
            "states_not_counting_health_change_b": states + states_health,
        }
    )
    return line


def build(sweep_bytes):
    """The revenue lines for a sweep file's bytes, as a JSON-ready dict."""
    payload = json.loads(sweep_bytes)
    rows = payload.get("scenarios")
    if not isinstance(rows, list):
        raise SweepError("no scenarios")
    shifts = [row.get("shift_pct") for row in rows]
    if shifts != SHIFT_GRID:
        raise SweepError(f"shift grid {shifts}, expected {SHIFT_GRID}")
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise SweepError("no metadata")
    provenance = {}
    for key in PROVENANCE_FIELDS:
        if metadata.get(key) is None:
            raise SweepError(f"metadata: no {key}")
        provenance[key] = metadata[key]
    provenance["sweep_file"] = SWEEP
    provenance["sweep_sha256"] = hashlib.sha256(sweep_bytes).hexdigest()

    lines = []
    for row in rows:
        line = baseline_line(row) if row["shift_pct"] == 0 else shift_line(row)
        lines.append(
            {
                key: value if key == "shift_pct" else rounded(value)
                for key, value in line.items()
            }
        )
    return {"lines": lines, "provenance": provenance}


def render(sweep_bytes):
    """The text of revenueLines.json for a sweep file's bytes."""
    return json.dumps(build(sweep_bytes), sort_keys=True, indent=2) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help=f"exit 1 if {OUTPUT} differs from what the sweep gives",
    )
    args = parser.parse_args(argv)
    with open(os.path.join(ROOT, SWEEP), "rb") as f:
        text = render(f.read())
    path = os.path.join(ROOT, OUTPUT)
    if args.check:
        try:
            with open(path, encoding="utf-8", newline="") as f:
                current = f.read()
        except FileNotFoundError:
            current = None
        if current != text:
            print(
                f"{OUTPUT} is stale: run python3 -I analysis/revenue_lines.py",
                file=sys.stderr,
            )
            return 1
        return 0
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
