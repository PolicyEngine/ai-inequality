"""Emit paper/values_generated.tex and paper/tables_generated.tex.

Every number that appears in the paper's prose or tables is generated here from
the canonical result files — analysis/outputs/ai_scenarios.json (2030
scenarios), src/data/shiftSweepData.json (2026 mechanism sweep) and
analysis/outputs/yale_publishable_2030.xlsx (The Budget Lab's committed result
grid) — so the text cannot drift from the results. Mirrors the
emit-values pattern of the UK sister paper (PolicyEngine/uk-ai-study).

Three committed comparison files feed the stability and correction values:
analysis/outputs/ai_scenarios_buildo.json (build o),
analysis/outputs/ai_scenarios_buildp_published.json (build p as first
published, with Head Start and Early Head Start still counted in household net
income) and analysis/outputs/transfer_detail_buildp_published.json
(compute_transfer_detail.py on that published runtime: program-by-program
benefit totals, including the two Head Start programs). The data-build
comparison pairs the first two, because both count net income the same way;
the correction values compare the published build-p run with the corrected
one and take the Head Start amounts from the transfer detail.

Usage:
    python analysis/emit_paper_values.py
"""

import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "outputs")
PAPER = os.path.join(ROOT, "paper")

#: CBO 2030 corporate income tax anchor, from their corporate_tax sheet.
CBO_CIT_ANCHOR_B = 486.0

VARIANT = {"Slow": "S", "Moderate": "M", "Rapid": "R"}
LABOR = {"proportional": "S0", "compressive": "S2", "expansive": "S3"}

STATE_NAMES = {
    "FL": "Florida",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "WY": "Wyoming",
}


def our_row(data, name, variant, shares_fixed=False):
    for row in data["scenarios"]:
        s = row["scenario"]
        if (
            s["name"] == name
            and bool(s.get("hold_shares_fixed")) == shares_fixed
            and (shares_fixed or s["inequality"] == variant)
        ):
            return row
    return None


def our_side(row):
    """Federal-only decomposition on their accounting basis, $B."""
    fed_refundable = row["refundable_credits_change_b"] - row.get(
        "state_refundable_credits_change_b", 0.0
    )
    iit_net = row["fed_income_tax_change_b"] - fed_refundable
    payroll = row["payroll_change_b"]
    return {"iit_net": iit_net, "payroll": payroll, "total": iit_net + payroll}


def transfers(row):
    """Transfer outlays (refundable credits + benefits) and gross taxes, $B."""
    tr = row["refundable_credits_change_b"] + row["benefits_change_b"]
    gross = row["total_rev_change_b"] + tr
    return {"transfers": tr, "gross_tax": gross}


def state_net(deltas):
    return {
        k: v["state_net_change_b"]
        for k, v in deltas.items()
        if isinstance(v, dict) and "state_net_change_b" in v
    }


def net_income_accounting(metadata):
    """What a run counted in household net income, as a comparable key.

    The model version plus the benefit programs the run kept out of net
    income. Runs from before the Head Start correction carry no
    ``net_income_excluded_benefits`` and kept nothing out.
    """
    return (
        metadata.get("country_model_version"),
        tuple(sorted(metadata.get("net_income_excluded_benefits") or ())),
    )


def fmt(x, nd=1):
    return f"{x:.{nd}f}"


def sfmt(x, nd=0):
    return f"{x:+.{nd}f}"


def main():
    with open(os.path.join(OUT, "ai_scenarios.json")) as fh:
        sc = json.load(fh)
    with open(os.path.join(ROOT, "src", "data", "shiftSweepData.json")) as fh:
        sweep = json.load(fh)
    xlsx = os.path.join(OUT, "yale_publishable_2030.xlsx")
    theirs = pd.read_excel(
        xlsx, sheet_name="revenue_grid_wide", engine="openpyxl"
    ).set_index("scenario_id")
    # Their committed anchors: CBO 2030 total revenue (revenue_to_gdp sheet)
    # and their baseline realized taxable capital base (cell_params sheet).
    rev_gdp = pd.read_excel(xlsx, sheet_name="revenue_to_gdp", engine="openpyxl")
    their_cbo_rev = float(rev_gdp["baseline_revenue_B_cbo"].dropna().unique()[0])
    cell_params = pd.read_excel(xlsx, sheet_name="cell_params", engine="openpyxl")
    their_y0k = float(cell_params["y0_k_B"].dropna().unique()[0])

    V = {}  # macro name -> string value
    base = sc["baseline"]
    meta = sc["metadata"]

    # --- Baseline (2030) ---
    V["BaselinePovertyPct"] = fmt(100 * base["spm_poverty_rate"], 2)
    V["BaselineGini"] = fmt(base["net_gini"], 4)

    # --- Scenario grid rows ---
    rows = {}
    for name in ("Slow", "Moderate", "Rapid"):
        rows[(name, "fixed")] = our_row(sc, name, "none", shares_fixed=True)
        for var in ("compressive", "proportional", "expansive"):
            rows[(name, var)] = our_row(sc, name, var)

    rp = rows[("Rapid", "proportional")]
    rc = rows[("Rapid", "compressive")]
    re_ = rows[("Rapid", "expansive")]
    rf = rows[("Rapid", "fixed")]

    V["RapidFixedRev"] = sfmt(rf["total_rev_change_b"])
    V["RapidPropRev"] = sfmt(rp["total_rev_change_b"])
    V["RapidExpRev"] = sfmt(re_["total_rev_change_b"])
    V["RapidCompRev"] = sfmt(rc["total_rev_change_b"])
    V["RapidShareKeptPct"] = fmt(
        100 * rp["total_rev_change_b"] / rf["total_rev_change_b"], 0
    )
    V["RapidFixedPovPp"] = sfmt(
        100 * (rf["spm_poverty_rate"] - base["spm_poverty_rate"]), 2
    )
    V["RapidPropPovPp"] = sfmt(
        100 * (rp["spm_poverty_rate"] - base["spm_poverty_rate"]), 2
    )
    V["RapidCompPovPp"] = sfmt(
        100 * (rc["spm_poverty_rate"] - base["spm_poverty_rate"]), 2
    )
    V["RapidExpPovPp"] = sfmt(
        100 * (re_["spm_poverty_rate"] - base["spm_poverty_rate"]), 2
    )
    V["RapidPovSpanPp"] = fmt(
        100 * (re_["spm_poverty_rate"] - rc["spm_poverty_rate"]), 2
    )
    V["RapidRevRelMovePct"] = fmt(
        100 * (re_["total_rev_change_b"] / rc["total_rev_change_b"] - 1), 0
    )

    # Wage crossovers (Rapid).
    V["RapidCompLambda"] = fmt(rc["diagnostics"]["inequality_lambda"], 3)
    V["RapidExpLambda"] = fmt(re_["diagnostics"]["inequality_lambda"], 3)
    V["RapidCompCrossover"] = f"{rc['diagnostics']['labor_crossover_income']:,.0f}"
    V["RapidExpCrossover"] = f"{re_['diagnostics']['labor_crossover_income']:,.0f}"

    # Social Security cap diagnostics: baseline shares from baseline.context.
    ctx = base["context"]
    V["SSCap"] = f"{ctx['social_security_cap']:,.0f}"
    V["ShareWagesAboveCapPct"] = fmt(100 * ctx["share_of_wages_above_cap"], 1)
    V["ShareWorkersAboveCapPct"] = fmt(100 * ctx["share_of_workers_above_cap"], 1)
    V["ModelledLaborShareT"] = fmt(ctx["positive_labor_income_t"], 1)
    V["ModelledCapitalShareT"] = fmt(ctx["positive_capital_income_t"], 1)
    V["RapidCompPayroll"] = sfmt(rc["payroll_change_b"])
    V["RapidPropPayroll"] = sfmt(rp["payroll_change_b"])
    V["RapidExpPayroll"] = sfmt(re_["payroll_change_b"])
    V["RapidCompLaborPct"] = fmt(100 * rc["scenario"]["labor_growth"], 2)

    # --- Transfer decomposition across Rapid lambda variants ---
    tc, te = transfers(rc), transfers(re_)
    V["GrossTaxSwing"] = fmt(te["gross_tax"] - tc["gross_tax"], 0)
    V["TransferSwing"] = fmt(te["transfers"] - tc["transfers"], 0)
    V["TransferAbsorbPct"] = fmt(
        100
        * (te["transfers"] - tc["transfers"])
        / (te["gross_tax"] - tc["gross_tax"]),
        0,
    )
    V["BenefitSwing"] = fmt(
        re_["benefits_change_b"] - rc["benefits_change_b"], 0
    )
    V["RapidCompBenefits"] = sfmt(rc["benefits_change_b"])
    V["RapidExpBenefits"] = sfmt(re_["benefits_change_b"])
    V["SnapSwing"] = fmt(re_["snap_change_b"] - rc["snap_change_b"], 0)
    V["RapidCompSnap"] = sfmt(rc["snap_change_b"])
    V["RapidExpSnap"] = sfmt(re_["snap_change_b"])
    V["SsiSwing"] = fmt(re_["ssi_change_b"] - rc["ssi_change_b"], 0)
    V["CreditSwing"] = fmt(
        re_["refundable_credits_change_b"] - rc["refundable_credits_change_b"], 0
    )
    mc = rows[("Moderate", "compressive")]
    me = rows[("Moderate", "expansive")]
    V["ModCompBenefits"] = sfmt(mc["benefits_change_b"])
    V["ModExpBenefits"] = sfmt(me["benefits_change_b"])
    V["NetRevSwing"] = fmt(
        re_["total_rev_change_b"] - rc["total_rev_change_b"], 0
    )

    # --- States ---
    V["RapidCompState"] = sfmt(rc["state_tax_change_b"])
    V["RapidPropState"] = sfmt(rp["state_tax_change_b"])
    V["RapidExpState"] = sfmt(re_["state_tax_change_b"])
    exp_state_net = (
        re_["state_tax_change_b"] - re_["state_refundable_credits_change_b"]
    )
    V["RapidExpStateNet"] = sfmt(exp_state_net)
    sn = state_net(rp["state_deltas"])
    top5 = sorted(sn.items(), key=lambda kv: kv[1], reverse=True)[:5]
    V["StateTopFiveSharePct"] = fmt(
        100 * sum(v for _, v in top5) / sum(sn.values()), 0
    )
    for (code, val), macro in zip(
        top5, ("StateFirst", "StateSecond", "StateThird", "StateFourth", "StateFifth")
    ):
        V[macro] = f"{code} {val:+.1f}"
    V["WAState"] = sfmt(sn["WA"], 1)
    # Zero-collecting states are derived from the data, not asserted.
    zero_states = sorted(k for k, v in sn.items() if v == 0.0)
    n_zero = len(zero_states)
    V["NZeroStates"] = str(n_zero)
    names = [STATE_NAMES.get(s, s) for s in zero_states]
    V["ZeroStatesList"] = ", ".join(names[:-1]) + " and " + names[-1]
    V["ZeroStatesCodes"] = ", ".join(zero_states)

    # --- Realization sweep ---
    real = sorted(
        sc["sensitivities"]["realization"],
        key=lambda r: r["scenario"]["realization_rate"],
    )
    revs = {
        r["scenario"]["realization_rate"]: r["total_rev_change_b"] for r in real
    }
    revs[1.0] = rp["total_rev_change_b"]
    V["RealZeroRev"] = sfmt(revs[0.0])
    V["RealFullRev"] = sfmt(revs[1.0])
    # Linear interpolation for the breakeven realized share.
    grid = sorted(revs.items())
    breakeven = None
    for (x0, y0), (x1, y1) in zip(grid, grid[1:]):
        if y0 <= 0 <= y1:
            breakeven = x0 + (0 - y0) * (x1 - x0) / (y1 - y0)
            break
    V["RealBreakevenPct"] = fmt(100 * breakeven, 1)
    V["RealGridStepPct"] = fmt(100 * (grid[1][0] - grid[0][0]), 0)
    V["RealQuarterRev"] = sfmt(revs[0.25])
    povs = [r["spm_poverty_rate"] for r in real] + [rp["spm_poverty_rate"]]
    V["RealPovMinPct"] = fmt(100 * min(povs), 2)
    V["RealPovMaxPct"] = fmt(100 * max(povs), 2)
    V["RealPovSpanPp"] = fmt(100 * (max(povs) - min(povs)), 2)
    their_rapid_cit = theirs.loc["ai_R_R_S0_V1", "macro_cit_delta"]
    V["TheirRapidCit"] = sfmt(their_rapid_cit)
    # Their wedge equals g_K x $486B on every committed cell (the base cancels):
    # verify against their own per-cell g_k rather than asserting it.
    n_cells = len(cell_params)
    cit_dev = max(
        abs(row.delta_R_CIT_B - row.g_k * CBO_CIT_ANCHOR_B)
        for row in cell_params.itertuples()
    )
    V["CitWedgeMaxDevB"] = fmt(cit_dev, 3)
    V["TheirNCells"] = str(n_cells)
    V["RealZeroAllIn"] = sfmt(revs[0.0] + their_rapid_cit)

    # --- Capital scope ---
    scope = {
        r["scenario"]["name"]: r
        for r in sc["sensitivities"]["capital_scope_excluding_retirement"]
    }
    for name, macro in (("Slow", "Slow"), ("Moderate", "Mod"), ("Rapid", "Rapid")):
        full = rows[(name, "proportional")]["total_rev_change_b"]
        excl = scope[name]["total_rev_change_b"]
        V[f"{macro}ScopeFull"] = sfmt(full)
        V[f"{macro}ScopeExcl"] = sfmt(excl)
    scope_diff = (
        scope["Rapid"]["total_rev_change_b"]
        - rows[("Rapid", "proportional")]["total_rev_change_b"]
    )
    V["RapidScopeDiff"] = sfmt(scope_diff)
    V["RapidScopeDiffAbs"] = fmt(abs(scope_diff), 0)

    # --- Average tax rate cross-check ---
    V["RapidPropMarketDelta"] = sfmt(rp["market_income_change_b"])
    V["RapidPropATRPct"] = fmt(
        100 * rp["total_rev_change_b"] / rp["market_income_change_b"], 1
    )

    # --- Reconciliation with their committed grid ---
    us = our_side(re_)
    them_cell = theirs.loc["ai_R_R_S3_V1"]
    them_iit_net = them_cell.revenues_income_tax - them_cell.outlays_tax_credits
    bridged = us["total"] + them_cell.macro_cit_delta
    V["BridgeOursIIT"] = sfmt(us["iit_net"])
    V["BridgeOursPayroll"] = sfmt(us["payroll"])
    V["BridgeWedge"] = sfmt(them_cell.macro_cit_delta)
    V["BridgeOursTotal"] = sfmt(bridged)
    V["BridgeTheirsIIT"] = sfmt(them_iit_net)
    V["BridgeTheirsPayroll"] = sfmt(them_cell.revenues_payroll_tax)
    V["BridgeTheirsTotal"] = sfmt(them_cell.total_with_macro_cit)
    V["BridgeRatio"] = fmt(bridged / them_cell.total_with_macro_cit, 2)
    V["TheirCBORevB"] = f"{their_cbo_rev:,.0f}"
    V["BridgeOursCboPct"] = fmt(100 * bridged / their_cbo_rev, 1)
    V["BridgeTheirsCboPct"] = fmt(
        100 * them_cell.total_with_macro_cit / their_cbo_rev, 1
    )
    V["TheirYZeroKT"] = fmt(their_y0k / 1000, 2)
    V["BaseGapPct"] = fmt(
        100 * (ctx["positive_capital_income_t"] * 1000 / their_y0k - 1), 0
    )
    V["IITRatio"] = fmt(us["iit_net"] / them_iit_net, 2)
    prop_us = our_side(rp)
    prop_cell = theirs.loc["ai_R_R_S0_V1"]
    prop_them_iit = prop_cell.revenues_income_tax - prop_cell.outlays_tax_credits
    V["IITRatioProp"] = fmt(prop_us["iit_net"] / prop_them_iit, 2)

    pay_ours, pay_theirs, iit_gaps = [], [], []
    for var in ("compressive", "proportional", "expansive"):
        u = our_side(rows[("Rapid", var)])
        cell = theirs.loc[f"ai_R_R_{LABOR[var]}_V1"]
        pay_ours.append(u["payroll"])
        pay_theirs.append(cell.revenues_payroll_tax)
        iit_gaps.append(
            u["iit_net"] - (cell.revenues_income_tax - cell.outlays_tax_credits)
        )
    V["PayrollTripletOurs"] = "/".join(f"{x:+.0f}" for x in pay_ours)
    V["PayrollTripletTheirs"] = "/".join(f"{x:+.0f}" for x in pay_theirs)
    V["IITGapTriplet"] = "/".join(f"{x:+.0f}" for x in iit_gaps)
    V["PayrollMaxCellGap"] = fmt(
        max(
            abs(
                our_side(rows[(n, v)])["payroll"]
                - theirs.loc[f"ai_{VARIANT[n]}_R_{LABOR[v]}_V1"].revenues_payroll_tax
            )
            for n in ("Slow", "Moderate", "Rapid")
            for v in ("compressive", "proportional", "expansive")
        ),
        0,
    )

    # Market-income deltas behind the tilt (Section: national vs modelled shares).
    V["RapidFixedMarketDelta"] = sfmt(rf["market_income_change_b"])

    # Tilt ratios: shares fixed / as forecast (proportional), publishable basis
    # for them; matched federal+CIT basis for ours; household basis separately.
    for name, macro in (("Slow", "Slow"), ("Moderate", "Mod"), ("Rapid", "Rapid")):
        v = VARIANT[name]
        tf = theirs.loc[f"ai_{v}_F_S0_V1", "total_with_macro_cit"]
        tr = theirs.loc[f"ai_{v}_R_S0_V1", "total_with_macro_cit"]
        V[f"TiltTheirs{macro}"] = fmt(tf / tr, 2)
        of_ = our_side(rows[(name, "fixed")])
        or_ = our_side(rows[(name, "proportional")])
        of_tot = of_["total"] + theirs.loc[f"ai_{v}_F_S0_V1", "macro_cit_delta"]
        or_tot = or_["total"] + theirs.loc[f"ai_{v}_R_S0_V1", "macro_cit_delta"]
        V[f"TiltOursMatched{macro}"] = fmt(of_tot / or_tot, 2)
        V[f"TiltOursHousehold{macro}"] = fmt(
            rows[(name, "fixed")]["total_rev_change_b"]
            / rows[(name, "proportional")]["total_rev_change_b"],
            2,
        )
        # Keep-rates (inverse tilt ratios), so the paper can state the basis.
        V[f"KeptMatched{macro}Pct"] = fmt(100 * or_tot / of_tot, 0)
        V[f"KeptTheirs{macro}Pct"] = fmt(100 * tr / tf, 0)
        V[f"KeptHousehold{macro}Pct"] = fmt(
            100
            * rows[(name, "proportional")]["total_rev_change_b"]
            / rows[(name, "fixed")]["total_rev_change_b"],
            0,
        )

    # Slow / compressive extreme case: percent below shares-and-distribution
    # unchanged (their S_F_S0 vs S_R_S2; ours shares-fixed vs compressive).
    them_low = 1 - (
        theirs.loc["ai_S_R_S2_V1", "total_with_macro_cit"]
        / theirs.loc["ai_S_F_S0_V1", "total_with_macro_cit"]
    )
    ours_low = 1 - (
        rows[("Slow", "compressive")]["total_rev_change_b"]
        / rows[("Slow", "fixed")]["total_rev_change_b"]
    )
    V["SlowCompTheirsLowerPct"] = fmt(100 * them_low, 0)
    V["SlowCompOursLowerPct"] = fmt(100 * ours_low, 0)

    # --- Mechanism sweep (2026) ---
    sw = {r["shift_pct"]: r for r in sweep["scenarios"]}
    V["SweepYear"] = str(sweep["metadata"]["year"])
    V["SweepBaseGini"] = fmt(sw[0]["net_gini"], 3)
    V["SweepFullGini"] = fmt(sw[100]["net_gini"], 3)
    V["SweepBasePovPct"] = fmt(100 * sw[0]["spm_poverty_rate"], 1)
    V["SweepFullPovPct"] = fmt(100 * sw[100]["spm_poverty_rate"], 1)
    trough = min(sweep["scenarios"], key=lambda r: r["total_rev_change_b"])
    V["SweepTroughRev"] = sfmt(trough["total_rev_change_b"])
    V["SweepTroughShift"] = str(trough["shift_pct"])
    V["SweepFullRev"] = sfmt(sw[100]["total_rev_change_b"])
    ten = sw[10]
    V["SweepTenIIT"] = sfmt(ten["income_tax_change_b"])
    V["SweepTenPayroll"] = sfmt(
        ten["employee_ss_tax_change_b"]
        + ten["employee_medicare_tax_change_b"]
        + ten["employer_payroll_change_b"]
        + ten.get("self_employment_tax_change_b", 0.0)
    )
    bf = sweep["metadata"]["baseline_facts"]
    V["SweepLaborT"] = fmt(bf["positive_labor_income_t"], 1)
    V["SweepCapitalT"] = fmt(bf["positive_capital_income_t"], 1)
    V["SweepHHCapSharePct"] = fmt(
        100 * bf["households_with_positive_capital_income_share"], 0
    )
    dec = {
        s["shift_pct"]: s for s in bf["decile_impacts"]["scenarios"]
    }
    d100 = {d["decile"]: d["pct_change"] for d in dec[100]["deciles"]}
    V["SweepTopDecilePct"] = sfmt(d100[10], 0)
    V["SweepBottomDecilePct"] = sfmt(d100[1], 1)
    worst = min((v, k) for k, v in d100.items() if k != 10)
    V["SweepWorstDecilePct"] = fmt(worst[0], 1)
    V["SweepWorstDecile"] = str(worst[1])

    # --- Forecast-equivalence mapping (sweep axis position of scenarios) ---
    for name, macro in (("Slow", "Slow"), ("Moderate", "Mod"), ("Rapid", "Rapid")):
        s = rows[(name, "proportional")]["scenario"]
        k = 1 - (1 + s["labor_growth"]) / (1 + s["gdp_growth"])
        V[f"ForecastShift{macro}Pct"] = fmt(100 * k, 1)

    # --- Calibration constants and identity diagnostics ---
    V["IdentityMaxResidual"] = fmt(
        max(abs(r["identity_residual_b"]) for r in sc["scenarios"]), 3
    )
    err = max(abs(r["diagnostics"]["labor_growth_error"]) for r in sc["scenarios"])
    mant, exp = f"{err:.0e}".split("e")
    V["LaborTargetMaxErr"] = rf"${mant}\times10^{{{int(exp)}}}$"
    V["ModelVersion"] = meta["country_model_version"]
    V["RunnerVersion"] = meta["policyengine_version"]
    V["DataBuild"] = meta["certified_data_build_id"]
    # e.g. populace-us-2024-buildp-sparse-rmloss100-cae8640-20260728T011454Z
    parts = V["DataBuild"].split("-")
    V["DataBuildShort"] = parts[-2]
    stamp = parts[-1]
    V["DataBuildDate"] = f"{stamp[6:8]} {['','January','February','March','April','May','June','July','August','September','October','November','December'][int(stamp[4:6])]} {stamp[:4]}"

    # --- Stability across data builds (build o vs build p, same model) ---
    # A data-only comparison needs the same model and the same net-income
    # accounting on both builds. Build o was run while Head Start and Early
    # Head Start were still counted in net income, so it is compared with
    # build p as published, which counted them the same way, rather than with
    # the corrected build-p run in ai_scenarios.json.
    with open(os.path.join(OUT, "ai_scenarios_buildo.json")) as fh:
        old = json.load(fh)
    with open(os.path.join(OUT, "ai_scenarios_buildp_published.json")) as fh:
        pub = json.load(fh)
    assert net_income_accounting(old["metadata"]) == net_income_accounting(
        pub["metadata"]
    ), "build-o and build-p stability runs count net income differently"
    assert pub["metadata"]["certified_data_build_id"] == V["DataBuild"]
    assert pub["metadata"]["country_model_version"] == V["ModelVersion"]

    def skey(r):
        s = r["scenario"]
        return (s["name"], s["inequality"], bool(s.get("hold_shares_fixed")))

    orows = {skey(r): r for r in old["scenarios"]}
    obase = old["baseline"]
    prows = {skey(r): r for r in pub["scenarios"]}
    pbase = pub["baseline"]
    max_abs = max_rel = max_rel_mr = max_pov = 0.0
    for r in pub["scenarios"]:
        o = orows[skey(r)]
        d = abs(r["total_rev_change_b"] - o["total_rev_change_b"])
        rel = d / abs(o["total_rev_change_b"])
        max_abs = max(max_abs, d)
        max_rel = max(max_rel, rel)
        if r["scenario"]["name"] != "Slow":
            max_rel_mr = max(max_rel_mr, rel)
        dpov = abs(
            (r["spm_poverty_rate"] - pbase["spm_poverty_rate"])
            - (o["spm_poverty_rate"] - obase["spm_poverty_rate"])
        )
        max_pov = max(max_pov, dpov)
    V["StabMaxAbsRevB"] = fmt(max_abs, 1)
    V["StabMaxRelPct"] = fmt(100 * max_rel, 0)
    V["StabMaxRelModRapidPct"] = fmt(100 * max_rel_mr, 1)
    V["StabMaxPovChangePp"] = fmt(100 * max_pov, 2)
    V["StabTopOneOld"] = fmt(100 * obase["net_top_1_share"], 2)
    V["StabTopOneNew"] = fmt(100 * pbase["net_top_1_share"], 2)
    V["BaselineTopOnePct"] = fmt(100 * base["net_top_1_share"], 2)
    ny_old = orows[("Rapid", "proportional", False)]["state_deltas"]["NY"][
        "state_net_change_b"
    ]
    ny_pub = prows[("Rapid", "proportional", False)]["state_deltas"]["NY"][
        "state_net_change_b"
    ]
    V["StabNYOld"] = fmt(ny_old, 1)
    V["StabNYNew"] = fmt(ny_pub, 1)

    # --- Head Start correction (build p as published vs this run) ---
    V["CorrMaxRevMoveB"] = fmt(
        max(
            abs(r["total_rev_change_b"] - prows[skey(r)]["total_rev_change_b"])
            for r in sc["scenarios"]
        ),
        0,
    )
    ptc = transfers(prows[("Rapid", "compressive", False)])
    pte = transfers(prows[("Rapid", "expansive", False)])
    V["PubTransferSwing"] = fmt(pte["transfers"] - ptc["transfers"], 0)
    V["PubTransferAbsorbPct"] = fmt(
        100
        * (pte["transfers"] - ptc["transfers"])
        / (pte["gross_tax"] - ptc["gross_tax"]),
        0,
    )
    V["PubBaselineGini"] = fmt(pbase["net_gini"], 4)

    # The Head Start amounts the published run counted, from the transfer
    # detail on the same runtime and data. Its benefit changes must equal the
    # published scenario file's, so it cannot come from a different run.
    with open(os.path.join(OUT, "transfer_detail_buildp_published.json")) as fh:
        pub_detail = json.load(fh)
    assert net_income_accounting(pub_detail["metadata"]) == net_income_accounting(
        pub["metadata"]
    ), "published transfer detail counts net income differently"
    assert pub_detail["metadata"]["certified_data_build_id"] == V["DataBuild"]
    for variant, detail in pub_detail["scenarios"].items():
        published_benefits = prows[("Rapid", variant, False)]["benefits_change_b"]
        assert (
            abs(detail["deltas_b"]["household_benefits"] - published_benefits) < 1e-6
        ), f"transfer detail and published run differ on Rapid / {variant}"
    pub_totals = pub_detail["baseline_totals"]
    V["PubEarlyHeadStartB"] = fmt(pub_totals["early_head_start"] / 1e9, 0)
    V["PubHeadStartB"] = fmt(pub_totals["head_start"] / 1e9, 0)

    # ---------------- values_generated.tex ----------------
    lines = [
        "% values_generated.tex — machine-generated by analysis/emit_paper_values.py",
        "% from analysis/outputs/ai_scenarios.json, src/data/shiftSweepData.json and",
        "% analysis/outputs/yale_publishable_2030.xlsx. DO NOT EDIT BY HAND.",
    ]
    for k, v in V.items():
        lines.append(rf"\newcommand{{\gen{k}}}{{{v}}}")
    os.makedirs(PAPER, exist_ok=True)
    with open(os.path.join(PAPER, "values_generated.tex"), "w") as fh:
        fh.write("\n".join(lines) + "\n")

    # ---------------- tables_generated.tex ----------------
    T = []
    T.append("% tables_generated.tex — machine-generated by analysis/emit_paper_values.py.")
    T.append("% DO NOT EDIT BY HAND.")

    def pov(row):
        return 100 * (row["spm_poverty_rate"] - base["spm_poverty_rate"])

    # Scenario grid.
    T.append(r"\newcommand{\tabScenarioGrid}{%")
    T.append(r"\begin{tabular}{lrrrrrrr}")
    T.append(r"\toprule")
    T.append(
        r"Scenario & Revenue & Income tax & Payroll & State & Poverty & $\Delta$pp & Net Gini \\"
    )
    T.append(r"\midrule")
    for name in ("Slow", "Moderate", "Rapid"):
        for var, label in (
            ("fixed", "shares fixed"),
            ("compressive", "compressive"),
            ("proportional", "proportional"),
            ("expansive", "expansive"),
        ):
            r = rows[(name, var)]
            T.append(
                f"{name} / {label} & {r['total_rev_change_b']:+.0f} & "
                f"{r['fed_income_tax_change_b']:+.0f} & {r['payroll_change_b']:+.0f} & "
                f"{r['state_tax_change_b']:+.0f} & {100 * r['spm_poverty_rate']:.2f}\\% & "
                f"{pov(r):+.2f} & {r['net_gini']:.4f} \\\\"
            )
        if name != "Rapid":
            T.append(r"\addlinespace")
    T.append(r"\bottomrule")
    T.append(r"\end{tabular}}")

    # Tilt table.
    T.append(r"\newcommand{\tabTilt}{%")
    T.append(r"\begin{tabular}{lrrr}")
    T.append(r"\toprule")
    T.append(r"Scenario & Shares fixed & As forecast & Share kept \\")
    T.append(r"\midrule")
    for name in ("Slow", "Moderate", "Rapid"):
        a = rows[(name, "fixed")]["total_rev_change_b"]
        b = rows[(name, "proportional")]["total_rev_change_b"]
        T.append(
            f"{name} & {a:+.0f} & {b:+.0f} & {100 * b / a:.0f}\\% \\\\"
        )
    T.append(r"\bottomrule")
    T.append(r"\end{tabular}}")

    # Realization table.
    T.append(r"\newcommand{\tabRealization}{%")
    T.append(r"\begin{tabular}{lr}")
    T.append(r"\toprule")
    T.append(r"Realized share & Revenue \\")
    T.append(r"\midrule")
    for rate, rev in sorted(revs.items()):
        note = " (their assumption)" if rate == 1.0 else ""
        T.append(f"{100 * rate:.0f}\\%{note} & {rev:+.0f} \\\\")
    T.append(r"\bottomrule")
    T.append(r"\end{tabular}}")

    # Capital-scope table.
    T.append(r"\newcommand{\tabCapitalScope}{%")
    T.append(r"\begin{tabular}{lrrr}")
    T.append(r"\toprule")
    T.append(r"Scenario & Full capital set & Excl.\ retirement & Difference \\")
    T.append(r"\midrule")
    for name in ("Slow", "Moderate", "Rapid"):
        full = rows[(name, "proportional")]["total_rev_change_b"]
        excl = scope[name]["total_rev_change_b"]
        T.append(f"{name} & {full:+.0f} & {excl:+.0f} & {excl - full:+.0f} \\\\")
    T.append(r"\bottomrule")
    T.append(r"\end{tabular}}")

    # Bridge table.
    T.append(r"\newcommand{\tabBridge}{%")
    T.append(r"\begin{tabular}{lrrrr}")
    T.append(r"\toprule")
    T.append(
        r"Rapid / expansive & IIT (net) & Payroll & Corporate wedge & Total \\"
    )
    T.append(r"\midrule")
    T.append(
        f"This paper & {us['iit_net']:+.0f} & {us['payroll']:+.0f} & "
        f"{them_cell.macro_cit_delta:+.0f} & {bridged:+.0f} \\\\"
    )
    T.append(
        f"Budget Lab & {them_iit_net:+.0f} & {them_cell.revenues_payroll_tax:+.0f} & "
        f"{them_cell.macro_cit_delta:+.0f} & {them_cell.total_with_macro_cit:+.0f} \\\\"
    )
    T.append(r"\bottomrule")
    T.append(r"\end{tabular}}")

    # Payroll agreement table (all nine as-forecast cells, matched basis).
    T.append(r"\newcommand{\tabPayrollCells}{%")
    T.append(r"\begin{tabular}{lrrrr}")
    T.append(r"\toprule")
    T.append(r"Cell & \multicolumn{2}{c}{IIT net of credits} & \multicolumn{2}{c}{Payroll} \\")
    T.append(r" & Ours & Theirs & Ours & Theirs \\")
    T.append(r"\midrule")
    for name in ("Slow", "Moderate", "Rapid"):
        for var in ("compressive", "proportional", "expansive"):
            u = our_side(rows[(name, var)])
            cell = theirs.loc[f"ai_{VARIANT[name]}_R_{LABOR[var]}_V1"]
            t_iit = cell.revenues_income_tax - cell.outlays_tax_credits
            T.append(
                f"{name} / {var} & {u['iit_net']:+.0f} & {t_iit:+.0f} & "
                f"{u['payroll']:+.0f} & {cell.revenues_payroll_tax:+.0f} \\\\"
            )
        if name != "Rapid":
            T.append(r"\addlinespace")
    T.append(r"\bottomrule")
    T.append(r"\end{tabular}}")

    # Top-state table.
    T.append(r"\newcommand{\tabStates}{%")
    T.append(r"\begin{tabular}{lr}")
    T.append(r"\toprule")
    T.append(r"State & Net revenue change \\")
    T.append(r"\midrule")
    for code, val in sorted(sn.items(), key=lambda kv: kv[1], reverse=True)[:10]:
        T.append(f"{code} & {val:+.2f} \\\\")
    T.append(r"\addlinespace")
    T.append(
        rf"\multicolumn{{2}}{{l}}{{\footnotesize {n_zero} states collect exactly \$0: "
        + V["ZeroStatesCodes"]
        + r".} \\"
    )
    T.append(r"\bottomrule")
    T.append(r"\end{tabular}}")

    # Sweep table (every 10 points).
    T.append(r"\newcommand{\tabSweep}{%")
    T.append(r"\begin{tabular}{rrrrr}")
    T.append(r"\toprule")
    T.append(r"Shift & Revenue & Income tax & Poverty & Net Gini \\")
    T.append(r"\midrule")
    for pct in range(0, 101, 10):
        r = sw[pct]
        T.append(
            f"{pct}\\% & {r['total_rev_change_b']:+.0f} & "
            f"{r['income_tax_change_b']:+.0f} & "
            f"{100 * r['spm_poverty_rate']:.1f}\\% & {r['net_gini']:.3f} \\\\"
        )
    T.append(r"\bottomrule")
    T.append(r"\end{tabular}}")

    with open(os.path.join(PAPER, "tables_generated.tex"), "w") as fh:
        fh.write("\n".join(T) + "\n")

    print(f"wrote {len(V)} macros and 8 tables to paper/")
    for k in sorted(V):
        print(f"  \\gen{k} = {V[k]}")


if __name__ == "__main__":
    main()
