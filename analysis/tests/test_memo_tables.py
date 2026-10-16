"""The memo's tables must be the committed run, to the digit they print.

``ai-scenarios-memo.md`` (published at /budget-lab through
``src/data/memoContent.js``) is written by hand, unlike the paper. Its tables
are checked here against ``analysis/outputs/ai_scenarios.json`` at the
precision each column prints, so a rerun that changes a cell fails CI until the
memo is updated. The memo's generated copy must also match its source.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MEMO = ROOT / "ai-scenarios-memo.md"
MEMO_JS = ROOT / "src" / "data" / "memoContent.js"
RUN = ROOT / "analysis" / "outputs" / "ai_scenarios.json"

HELD_BANNER = (
    "*Draft — HELD, not sent.*\n\n"
    "*PolicyEngine · prepared with the AV Tax Policy Roundtable of 30 July 2026 in mind*"
)
BYLINE = "*July 30, 2026 · Max Ghenis*"


def _num(text):
    """Parse '+$47B', '−0.14', '12.13%', '$118,287' and the like."""
    cleaned = (
        text.replace("−", "-").replace("$", "").replace(",", "").replace("B", "")
    )
    cleaned = cleaned.replace("%", "").strip()
    return float(cleaned)


def _table(section_heading_or_header):
    """Rows of the first markdown table whose header contains the text."""
    lines = MEMO.read_text().splitlines()
    for start, line in enumerate(lines):
        if line.startswith("|") and section_heading_or_header in line:
            rows = []
            for row in lines[start + 2 :]:
                if not row.startswith("|"):
                    break
                rows.append([cell.strip() for cell in row.strip("|").split("|")])
            return rows
    raise AssertionError(f"no table with header {section_heading_or_header!r}")


@pytest.fixture(scope="module")
def run():
    return json.loads(RUN.read_text())


def _grid_row(run, label):
    for row in run["scenarios"]:
        if row["scenario"]["label"] == label:
            return row
    raise KeyError(label)


def test_baseline_line(run):
    text = MEMO.read_text()
    match = re.search(
        r"Baseline SPM\s+poverty ([\d.]+)%, net Gini ([\d.]+)\.", text
    )
    assert match
    assert float(match.group(1)) == round(100 * run["baseline"]["spm_poverty_rate"], 2)
    assert float(match.group(2)) == round(run["baseline"]["net_gini"], 4)


def test_scenario_results_table(run):
    rows = _table("| Scenario | Revenue | Income tax |")
    assert len(rows) == len(run["scenarios"])
    base = run["baseline"]
    for cells in rows:
        label, revenue, income_tax, payroll, state, poverty, pp, gini = cells
        row = _grid_row(run, label)
        assert _num(revenue) == round(row["total_rev_change_b"]), label
        assert _num(income_tax) == round(row["fed_income_tax_change_b"]), label
        assert _num(payroll) == round(row["payroll_change_b"]), label
        assert _num(state) == round(row["state_tax_change_b"]), label
        assert _num(poverty) == round(100 * row["spm_poverty_rate"], 2), label
        assert _num(pp) == round(
            100 * (row["spm_poverty_rate"] - base["spm_poverty_rate"]), 2
        ), label
        assert _num(gini) == round(row["net_gini"], 4), label


def test_tilt_table(run):
    rows = _table("| Scenario | Shares fixed | As forecast | Share kept |")
    assert [r[0] for r in rows] == ["Slow", "Moderate", "Rapid"]
    for name, fixed, forecast, kept in rows:
        f = _grid_row(run, f"{name} / shares fixed")["total_rev_change_b"]
        p = _grid_row(run, f"{name} / proportional")["total_rev_change_b"]
        assert _num(fixed) == round(f), name
        assert _num(forecast) == round(p), name
        assert _num(kept) == round(100 * p / f), name


def test_realization_table(run):
    rows = _table("| Realized share | Revenue |")
    by_rate = {
        r["scenario"]["realization_rate"]: r["total_rev_change_b"]
        for r in run["sensitivities"]["realization"]
    }
    assert len(rows) == len(by_rate)
    for share, revenue in rows:
        rate = _num(share.split("(")[0]) / 100
        assert _num(revenue) == round(by_rate[rate]), share


def test_capital_scope_table(run):
    rows = _table("| Scenario | Full capital set | Excl. retirement |")
    scope = {
        r["scenario"]["name"]: r["total_rev_change_b"]
        for r in run["sensitivities"]["capital_scope_excluding_retirement"]
    }
    for name, full, excluded, difference in rows:
        f = _grid_row(run, f"{name} / proportional")["total_rev_change_b"]
        assert _num(full) == round(f), name
        assert _num(excluded) == round(scope[name]), name
        assert _num(difference.split(",")[0]) == round(scope[name] - f), name


def test_crossover_table(run):
    rows = _table("| Rapid variant | λ | Crossover |")
    for variant, lam, crossover in rows:
        row = _grid_row(run, f"Rapid / {variant.lower()}")
        assert float(lam) == round(row["diagnostics"]["inequality_lambda"], 3)
        income = _num(crossover.split("—")[0])
        assert income == round(row["diagnostics"]["labor_crossover_income"])


def test_site_copy_is_generated_from_the_memo():
    source = MEMO.read_text()
    assert HELD_BANNER in source
    expected = source.replace(HELD_BANNER, BYLINE)
    js = MEMO_JS.read_text()
    payload = js[js.index("export const memoMarkdown = ") + len("export const memoMarkdown = ") :]
    assert json.loads(payload.rstrip().rstrip(";")) == expected


VALUES = ROOT / "paper" / "values_generated.tex"


@pytest.fixture(scope="module")
def paper():
    text = VALUES.read_text()
    raw = dict(re.findall(r"\\newcommand\{\\gen(\w+)\}\{([^}]*)\}", text))
    return {k: v for k, v in raw.items()}


def _memo_has(pattern):
    match = re.search(pattern, MEMO.read_text(), flags=re.S)
    assert match, pattern
    return match.groups()


def _pnum(paper, name):
    return float(paper[name].replace(",", ""))


def test_headline_findings_match_the_paper(paper):
    fixed, prop = _memo_has(
        r"poverty falls ([\d.]+)\s+points if the gains split at today's factor "
        r"shares, and only ([\d.]+) points with"
    )
    assert -float(fixed) == _pnum(paper, "RapidFixedPovPp")
    assert -float(prop) == _pnum(paper, "RapidPropPovPp")
    move, span = _memo_has(r"revenue moves (\d+)% while poverty moves \*\*([\d.]+) points\*\*")
    assert move == paper["RapidRevRelMovePct"]
    assert span == paper["RapidPovSpanPp"]


def test_bridge_table_and_ratio_match_the_paper(paper):
    rows = _table("| Rapid + expansive | Fed income tax (net) |")
    ours, theirs = rows
    assert [_num(c) for c in ours[1:4]] == [
        _pnum(paper, "BridgeOursIIT"),
        _pnum(paper, "BridgeOursPayroll"),
        _pnum(paper, "BridgeWedge"),
    ]
    assert _num(ours[4].strip("*")) == _pnum(paper, "BridgeOursTotal")
    assert _num(theirs[4]) == _pnum(paper, "BridgeTheirsTotal")
    ratio, ours_pct, theirs_pct = _memo_has(
        r"\*\*We are ([\d.]+)× their estimate\*\* — ([\d.]+)% of CBO 2030 revenue "
        r"against their ([\d.]+)%"
    )
    assert ratio == paper["BridgeRatio"]
    assert ours_pct == paper["BridgeOursCboPct"]
    assert theirs_pct == paper["BridgeTheirsCboPct"]


def test_realization_prose_matches_the_paper(paper):
    wedge, all_in = _memo_has(
        r"would still collect about \$(\d+)B\s+on the same shock.*?to about \+\$(\d+)B"
    )
    assert float(wedge) == _pnum(paper, "TheirRapidCit")
    assert float(all_in) == _pnum(paper, "RealZeroAllIn")
    low, high = _memo_has(r"Poverty is flat across the entire sweep, ([\d.]+)% to ([\d.]+)%")
    assert low == paper["RealPovMinPct"]
    assert high == paper["RealPovMaxPct"]


def test_tilt_ratios_match_the_paper(paper):
    ours, theirs = _memo_has(
        r"our ratios are ([\d.]+× / [\d.]+× / [\d.]+×) against\s+their "
        r"([\d.]+× / [\d.]+× / [\d.]+×)"
    )
    names = ("Slow", "Mod", "Rapid")
    assert ours == " / ".join(f"{paper['TiltOursMatched' + n]}×" for n in names)
    assert theirs == " / ".join(f"{paper['TiltTheirs' + n]}×" for n in names)
