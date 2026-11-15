"""The paper reads the mechanism sweep's net revenue under its own definition.

The paper's methodology section defines net government revenue as taxes less
refundable credits and benefit outlays. Sweeps that count health coverage and
TANF move that measure to ``total_rev_change_published_definition_b``, so
regenerating the paper from such a sweep keeps the paper's definition until the
paper itself changes it.
"""

import json
import os

import pytest

from analysis.compare_sweep_vintages import revenue
from analysis.emit_paper_values import sweep_net_revenue, sweep_table

#: A sweep row from before the site counted health coverage and TANF.
OLD_ROW = {"shift_pct": 10, "total_rev_change_b": -880.0, "revenue_change_b": -880.0}
#: A sweep row that counts them.
NEW_ROW = {
    "shift_pct": 10,
    "total_rev_change_b": -1_250.0,
    "revenue_change_b": -1_250.0,
    "total_rev_change_excluding_health_b": -868.0,
    "total_rev_change_published_definition_b": -870.0,
}


def test_sweep_net_revenue_keeps_the_papers_definition():
    assert sweep_net_revenue(OLD_ROW) == -880.0
    assert sweep_net_revenue(NEW_ROW) == -870.0


def test_the_sweep_table_prints_the_papers_definition():
    for row, revenue_cell in ((OLD_ROW, "-880"), (NEW_ROW, "-870")):
        sw = {
            pct: {
                **row,
                "shift_pct": pct,
                "income_tax_change_b": 12.0,
                "spm_poverty_rate": 0.125,
                "net_gini": 0.4321,
            }
            for pct in range(0, 101, 10)
        }
        table = sweep_table(sw)
        assert table[0] == r"\newcommand{\tabSweep}{%"
        assert f"10\\% & {revenue_cell} & +12 & 12.5\\% & 0.432 \\\\" in table
        # The redefined total, which counts health coverage, stays out.
        assert not any("-1250" in line for line in table)


def test_main_writes_the_table_sweep_table_builds(tmp_path, monkeypatch):
    # main() reads the replication workbook through openpyxl, which CI doesn't
    # install, so this runs only where openpyxl is installed.
    pytest.importorskip("openpyxl")
    from analysis import emit_paper_values as emit

    monkeypatch.setattr(emit, "PAPER", str(tmp_path))
    emit.main()
    with open(os.path.join(emit.ROOT, "src", "data", "shiftSweepData.json")) as fh:
        sweep = json.load(fh)
    sw = {row["shift_pct"]: row for row in sweep["scenarios"]}
    tables = (tmp_path / "tables_generated.tex").read_text()
    assert "\n".join(sweep_table(sw)) in tables


def test_vintage_comparison_reads_the_same_measure():
    for row in (OLD_ROW, NEW_ROW):
        assert revenue(row) == sweep_net_revenue(row)
