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


def test_tilt_turns_the_poverty_gain_into_a_loss(v):
    """Abstract, intro, conclusion: shares-fixed Rapid cuts poverty, the
    as-forecast tilt turns that into a marginal increase."""
    assert v.num("RapidFixedPovPp") < 0 < v.num("RapidPropPovPp")


def test_wage_spread_flips_the_poverty_sign_but_not_the_revenue_sign(v):
    """Abstract, intro, discussion: Rapid revenue stays positive across the
    compressive-to-expansive span while poverty changes sign."""
    assert v.num("RapidCompPovPp") < 0 < v.num("RapidExpPovPp")
    revenues = [v.num(f"Rapid{x}Rev") for x in ("Comp", "Prop", "Exp")]
    assert min(revenues) > 0
    assert revenues == sorted(revenues)


def test_state_take_roughly_doubles_across_the_wage_spread(v):
    """Intro, results, discussion: the state take doubles from compressive to
    expansive."""
    ratio = v.num("RapidExpState") / v.num("RapidCompState")
    assert 1.7 <= ratio <= 2.3


def test_low_realization_turns_household_revenue_negative(v):
    """Intro, sensitivity: below a breakeven realized share the household
    sector loses revenue, and the breakeven sits inside the first grid step."""
    assert v.num("RealZeroRev") < 0 < v.num("RealQuarterRev")
    assert 0 < v.num("RealBreakevenPct") < v.num("RealGridStepPct")


def test_realization_moves_more_than_a_quarter_trillion_and_poverty_not_at_all(v):
    """Sensitivity, discussion: hundreds of billions of revenue, poverty flat."""
    assert v.num("RealFullRev") - v.num("RealZeroRev") > 250
    assert v.num("RealPovSpanPp") < 0.1


def test_the_corporate_wedge_keeps_the_all_in_total_positive(v):
    """Sensitivity: even at a 0% realized share, adding their corporate wedge
    leaves the all-in total positive."""
    assert v.num("RealZeroAllIn") > 0


def test_excluding_retirement_halves_rapid_and_flips_slow(v):
    """Intro, sensitivity, site: halves Rapid, flips Slow negative."""
    assert 0.4 <= v.num("RapidScopeExcl") / v.num("RapidScopeFull") <= 0.6
    assert v.num("SlowScopeFull") > 0 > v.num("SlowScopeExcl")


def test_forecast_range_is_the_first_decade_of_the_sweep(v):
    """Methodology, results: the scenarios sit in the sweep's first tenth."""
    shifts = [v.num(f"ForecastShift{x}Pct") for x in ("Slow", "Mod", "Rapid")]
    assert shifts == sorted(shifts)
    assert 0 < shifts[0] and shifts[-1] < 10


def test_household_keep_rate_is_below_the_federal_one(v):
    """Intro, results, reconciliation: the household keep-rate is lower
    (mainly the missing corporate wedge)."""
    assert v.num("KeptHouseholdRapidPct") < v.num("KeptMatchedRapidPct")


def test_tilt_ratios_have_the_same_ordering_in_both_models(v):
    """Reconciliation: agreement on the tilt with the same ordering."""
    ours = [v.num(f"TiltOursMatched{x}") for x in ("Slow", "Mod", "Rapid")]
    theirs = [v.num(f"TiltTheirs{x}") for x in ("Slow", "Mod", "Rapid")]
    order = lambda xs: sorted(range(3), key=lambda i: xs[i])  # noqa: E731
    assert order(ours) == order(theirs)
    assert all(x > 1 for x in ours + theirs)


def test_payroll_reverses_sign_under_compression_in_both_models(v):
    """Reconciliation: both models show the sign reversal under compression."""
    for name in ("PayrollTripletOurs", "PayrollTripletTheirs"):
        compressive, proportional, expansive = v.triplet(name)
        assert compressive > 0, name
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


def test_washington_out_collects_the_zero_states(v):
    """Results: Washington's capital-gains excise collects more than the
    zero-collecting states, which collect nothing."""
    assert int(v["NZeroStates"]) >= 1
    assert v.num("WAState") > 0


def test_site_panel_federal_keep_rate_matches_the_paper(v):
    """The scenario panel states the federal-basis keep-rate in its copy."""
    text = PANEL.read_text()
    match = re.search(r"and (\d+)% on the narrower federal basis", text)
    assert match, "keep-rate sentence not found in AIScenarios.jsx"
    assert match.group(1) == v["KeptMatchedRapidPct"]
