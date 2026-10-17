"""The paper's words about its generated numbers must stay true.

Every number in the paper is a macro from ``paper/values_generated.tex``, so a
rerun cannot leave a stale figure behind. A rerun can still leave a stale
*word*: "flips sign", "always positive", "halves", "the first decade". Each
test here states one such claim, cites where the prose makes it, and checks it
against the committed macros, so new outputs that falsify a sentence fail CI
instead of shipping under it.

The site's scenario panel restates one paper value in its copy (the federal
keep-rate); the last test holds it to the macro.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALUES = ROOT / "paper" / "values_generated.tex"
PANEL = ROOT / "src" / "components" / "AIScenarios.jsx"


def _macros():
    text = VALUES.read_text()
    return dict(re.findall(r"\\newcommand\{\\gen(\w+)\}\{([^}]*)\}", text))


@pytest.fixture(scope="module")
def v():
    raw = _macros()

    class Values(dict):
        def num(self, name):
            return float(self[name].replace("−", "-").replace(",", ""))

        def triplet(self, name):
            return [float(x) for x in self[name].split("/")]

    return Values(raw)


def test_tilt_erodes_most_of_the_poverty_gain(v):
    """Abstract, intro, conclusion: shares-fixed Rapid cuts poverty, and the
    as-forecast tilt keeps only a minority of that cut ("erodes most of
    growth's poverty gain"). On the July inputs it reversed the sign."""
    assert v.num("RapidFixedPovPp") < v.num("RapidPropPovPp") < 0
    assert 0 < v.num("RapidPovGainKeptPct") < 50


def test_wage_spread_flips_the_poverty_sign_but_not_the_revenue_sign(v):
    """Abstract, intro, discussion: Rapid revenue stays positive across the
    compressive-to-expansive span while poverty changes sign."""
    assert v.num("RapidCompPovPp") < 0 < v.num("RapidExpPovPp")
    revenues = [v.num(f"Rapid{x}Rev") for x in ("Comp", "Prop", "Exp")]
    assert min(revenues) > 0
    assert revenues == sorted(revenues)


def test_state_take_nearly_doubles_across_the_wage_spread(v):
    """Abstract, intro, results, discussion: the state take nearly doubles from
    compressive to expansive."""
    assert 1.6 <= v.num("RapidStateSpanRatio") < 1.95


def test_state_net_is_roughly_a_sixth_of_the_bridged_take(v):
    """Results: on the bridge cell, net state tax adds roughly a sixth."""
    assert 0.12 <= v.num("RapidExpStateNet") / v.num("BridgeOursTotal") <= 0.21


def test_revenue_stays_positive_at_every_realized_share(v):
    """Abstract, intro, sensitivity: the household sector still gains at a 0%
    realized share, so there is no breakeven to cite; on the July inputs
    there was one."""
    assert v.num("RealZeroRev") > 0
    assert "RealBreakevenPct" not in v
    assert 0 < v.num("RevRealBreakevenOldPct") < 100
    assert v.num("RevRealZeroRevOld") < 0


def test_realization_sweep_is_linear_and_moves_a_quarter_trillion(v):
    """Sensitivity, discussion: linear to within a percent; roughly a
    quarter-trillion dollars of revenue; poverty flat."""
    assert v.num("RealLineMaxGapPct") < 1
    assert 225 <= v.num("RealFullLessZeroB") <= 275
    assert v.num("RealPovSpanPp") < 0.1


def test_the_corporate_wedge_lifts_the_all_in_total(v):
    """Sensitivity: at a 0% realized share their wedge lifts the all-in total
    above the household figure."""
    assert v.num("RealZeroAllIn") > v.num("RealZeroRev") > 0


def test_excluding_retirement_cuts_rapid_by_a_third_and_flips_slow(v):
    """Intro, sensitivity, site: cuts Rapid by about a third, flips Slow."""
    assert 30 <= v.num("RapidScopeCutPct") <= 40
    assert v.num("SlowScopeFull") > 0 > v.num("SlowScopeExcl")


def test_realization_spans_nearly_the_scenario_range(v):
    """Intro, sensitivity, memo: realization alone moves the Rapid estimate
    nearly as much as moving from Slow to Rapid (more than it, on the July
    inputs), and the retirement-scope case lies inside that range."""
    ratio = v.num("RealFullLessZeroB") / v.num("ScenarioSpanB")
    assert 0.8 <= ratio < 1
    assert v.num("RealZeroRev") < v.num("RapidScopeExcl") < v.num("RealFullRev")


def test_average_tax_rates_on_a_matched_numerator(v):
    """Sensitivity, memo: their Rapid band (21% to 32%) reproduces from their
    grid, and on the same numerator ours is higher in every cell."""
    ours = v.triplet("AtrOursMatchedTriplet")
    theirs = v.triplet("AtrTheirsTriplet")
    assert theirs[0] == 21 and theirs[2] == 32
    assert all(o > t for o, t in zip(ours, theirs))
    assert ours == sorted(ours) and theirs == sorted(theirs)


def test_tilt_takes_back_more_of_the_poverty_gain_than_of_revenue(v):
    """Intro: the tilt takes back much of what growth delivers, and more of its
    poverty gain than of its revenue."""
    assert v.num("RapidPovGainKeptPct") < v.num("KeptHouseholdRapidPct") < 60


def test_payroll_level_response_differs_with_shares_fixed(v):
    """Reconciliation, memo: payroll agrees in the as-forecast cells, but with
    shares fixed ours is about 1.4 times theirs."""
    assert 1.3 <= v.num("PayrollFixedRapidRatio") <= 1.5
    assert v.num("PayrollFixedRapidOurs") > v.num("PayrollFixedRapidTheirs") > 0


def test_forecast_range_is_the_first_decade_of_the_sweep(v):
    """Methodology, results: the scenarios sit in the sweep's first tenth."""
    shifts = [v.num(f"ForecastShift{x}Pct") for x in ("Slow", "Mod", "Rapid")]
    assert shifts == sorted(shifts)
    assert 0 < shifts[0] and shifts[-1] < 10


def test_household_keep_rate_is_below_the_federal_one_because_of_the_wedge(v):
    """Intro, results, reconciliation: the household keep-rate is lower mainly
    because that basis has no corporate wedge; states and transfers barely move
    it. Without the wedge, the federal keep-rate is the household one."""
    household = v.num("KeptHouseholdRapidPct")
    assert household < v.num("KeptMatchedRapidPct")
    assert abs(v.num("KeptFederalNoWedgeRapidPct") - household) <= 3
    assert v.num("KeptMatchedRapidPct") - household >= 5


def test_tilt_ratios_have_the_same_ordering_in_both_models(v):
    """Reconciliation: agreement on the tilt with the same ordering."""
    ours = [v.num(f"TiltOursMatched{x}") for x in ("Slow", "Mod", "Rapid")]
    theirs = [v.num(f"TiltTheirs{x}") for x in ("Slow", "Mod", "Rapid")]
    order = lambda xs: sorted(range(3), key=lambda i: xs[i])  # noqa: E731
    assert order(ours) == order(theirs)
    assert all(x > 1 for x in ours + theirs)


def test_payroll_rises_under_compression_and_falls_under_expansion(v):
    """Results, reconciliation: every Rapid variant grows labor income by the
    same amount; payroll rises under compression and turns into a loss under
    expansion, in both models."""
    assert v.num("RapidCompLaborPct") > 0
    assert v.num("RapidExpPayroll") < 0 < v.num("RapidCompPayroll")
    for name in ("PayrollTripletOurs", "PayrollTripletTheirs"):
        compressive, proportional, expansive = v.triplet(name)
        assert compressive > 0 > expansive, name
        assert expansive < proportional < compressive, name


def test_income_tax_gap_is_nearly_constant_across_rapid_cells(v):
    """Intro, reconciliation: the IIT gap is nearly constant in absolute terms
    across the three Rapid wage-spread cells."""
    gaps = v.triplet("IITGapTriplet")
    mean = sum(gaps) / 3
    assert mean > 0
    assert (max(gaps) - min(gaps)) / mean < 0.15


def test_slow_compressive_reproduces_in_direction(v):
    """Reconciliation: their extreme case reproduces in direction."""
    assert v.num("SlowCompOursLowerPct") > 0
    assert v.num("SlowCompTheirsLowerPct") > 0


def test_washington_collects_while_the_seven_zero_states_collect_nothing(v):
    """Results, memo: Washington collects; the seven zero states collect
    nothing."""
    assert int(v["NZeroStates"]) == 7
    assert v.num("WAState") > 0


def test_payroll_agrees_to_about_five_billion(v):
    """Abstract, intro, reconciliation: payroll agrees to about $5B."""
    assert 4 <= v.num("PayrollMaxCellGap") <= 6


def test_site_panel_federal_keep_rate_matches_the_paper(v):
    """The scenario panel states the federal-basis keep-rate in its copy."""
    text = PANEL.read_text()
    match = re.search(r"and (\d+)% on the narrower federal basis", text)
    assert match, "keep-rate sentence not found in AIScenarios.jsx"
    assert match.group(1) == v["KeptMatchedRapidPct"]


def test_revision_note_findings(v):
    """Revision note: the tilt reversed the poverty gain on the July inputs and
    erodes it on the revised ones; Rapid labor income turned from falling to
    growing."""
    assert v.num("RevRapidPropPovPpOld") > 0 > v.num("RevRapidPropPovPpNew")
    assert v.num("RevRapidLaborGrowthOld") < 0 < v.num("RevRapidLaborGrowthNew")
    assert v.num("RevRealZeroRevOld") < 0 < v.num("RevRealZeroRevNew")
