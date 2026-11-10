"""The paper reads the mechanism sweep's net revenue under its own definition.

The paper's methodology section defines net government revenue as taxes less
refundable credits and benefit outlays. Sweeps that count health coverage and
TANF move that measure to ``total_rev_change_published_definition_b``, so
regenerating the paper from such a sweep keeps the paper's definition until the
paper itself changes it.
"""

from analysis.compare_sweep_vintages import revenue
from analysis.emit_paper_values import sweep_net_revenue

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


def test_vintage_comparison_reads_the_same_measure():
    for row in (OLD_ROW, NEW_ROW):
        assert revenue(row) == sweep_net_revenue(row)
