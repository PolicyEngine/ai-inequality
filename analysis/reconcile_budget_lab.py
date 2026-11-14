"""Compare our scenario results to The Budget Lab's, cell by cell.

Their AI-Fiscal repository (github.com/Budget-Lab-Yale/AI-Fiscal, MIT, release
git rev 74de5986e5ff) commits the full published result grid:
`results/aggregates/ai_fiscal_publishable_2030_latest.xlsx`, with revenue by
instrument for all 18 cells. That replaces the two text-stated totals this
script previously compared against, and it corrects two errors in the earlier
version of this bridge:

  The wedge cancels its base.  Their corporate line is
  dR_CIT = X * (R_CIT_CBO / Y0_K) with X = Y0_K * g, so dR_CIT = g * R_CIT_CBO
  — the capital base drops out. All 18 committed macro_cit_delta values equal
  g x $486B to <$0.15B. The earlier bridge applied a flat 10.5% to OUR larger
  capital base, overstating the borrowed wedge (Rapid: $96B vs the correct
  $84B).

  The base is not recoverable from the wedge.  Because it cancels, "inverting
  the identity" says nothing about their Y0_K. Their methodology's remark that
  eta "falls out to roughly one in practice" implies Y0_K near $486B/0.105 ~
  $4.6T, but that rests on their prose, not on algebra this script can verify.

Alignment of cells: their share_mode R (reallocate) is our as-forecast run and
F (fixed share) is our shares-fixed counterfactual; S0/S2/S3 are our
proportional/compressive/expansive. Their microsim total = individual income
tax + payroll - refundable-credit outlays, which matches our federal IIT net of
refundable credits plus payroll.

Usage:
    python analysis/reconcile_budget_lab.py [ours.json] [theirs.xlsx]
"""

import json
import os
import sys

import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
OURS_PATH = os.path.join(OUT, "ai_scenarios.json")
THEIRS_PATH = os.path.join(OUT, "yale_publishable_2030.xlsx")
THEIRS_URL = (
    "https://raw.githubusercontent.com/Budget-Lab-Yale/AI-Fiscal/main/"
    "results/aggregates/ai_fiscal_publishable_2030_latest.xlsx"
)

#: CBO 2030 corporate income tax anchor, from their corporate_tax sheet.
CBO_CIT_B = 486.0
THEIR_CBO_2030_TOTAL_REVENUE_B = 6595.0

VARIANT = {"Slow": "S", "Moderate": "M", "Rapid": "R"}
LABOR = {"proportional": "S0", "compressive": "S2", "expansive": "S3"}


def load_theirs(path):
    if not os.path.exists(path):
        raise SystemExit(
            f"{path} not found. Download it first:\n  curl -sL {THEIRS_URL} -o {path}"
        )
    df = pd.read_excel(path, sheet_name="revenue_grid_wide", engine="openpyxl")
    return df.set_index("scenario_id")


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
    """Our federal-only decomposition on their accounting basis, $B."""
    fed_refundable = row.get("refundable_credits_change_b", 0.0) - row.get(
        "state_refundable_credits_change_b", 0.0
    )
    iit_net = row.get("fed_income_tax_change_b", 0.0) - fed_refundable
    payroll = row.get("payroll_change_b", 0.0)
    return {
        "iit_net": iit_net,
        "payroll": payroll,
        "microsim_total": iit_net + payroll,
    }


def their_side(cell):
    iit_net = cell.revenues_income_tax - cell.outlays_tax_credits
    return {
        "iit_net": iit_net,
        "payroll": cell.revenues_payroll_tax,
        "microsim_total": cell.total,
        "cit": cell.macro_cit_delta,
        "publishable": cell.total_with_macro_cit,
    }


def main():
    ours_path = sys.argv[1] if len(sys.argv) > 1 else OURS_PATH
    theirs_path = sys.argv[2] if len(sys.argv) > 2 else THEIRS_PATH

    with open(ours_path) as handle:
        ours = json.load(handle)
    theirs = load_theirs(theirs_path)

    print("=" * 96)
    print("OURS vs THE BUDGET LAB, CELL BY CELL (their committed result grid)")
    print(f"  ours:   {ours['metadata']['certified_data_build_id']}")
    print(
        "  theirs: AI-Fiscal results/aggregates/ai_fiscal_publishable_2030_latest.xlsx"
    )
    print("  basis:  federal IIT net of refundable credits + payroll ('microsim');")
    print("          'bridged' adds their corporate wedge g x $486B to our microsim.")
    print("=" * 96)

    header = (
        f"\n{'cell':24s} {'IIT ours':>9s} {'IIT them':>9s} "
        f"{'pay ours':>9s} {'pay them':>9s} {'ms ours':>8s} {'ms them':>8s} "
        f"{'bridged':>8s} {'publ.':>7s}"
    )
    print(header)
    print("-" * (len(header) - 1))
    for name in ("Slow", "Moderate", "Rapid"):
        for variant, code in LABOR.items():
            mine = our_row(ours, name, variant)
            cell_id = f"ai_{VARIANT[name]}_R_{code}_V1"
            if mine is None or cell_id not in theirs.index:
                continue
            us = our_side(mine)
            them = their_side(theirs.loc[cell_id])
            bridged = us["microsim_total"] + them["cit"]
            print(
                f"{name + ' / ' + variant:24s} "
                f"{us['iit_net']:>+9.0f} {them['iit_net']:>+9.0f} "
                f"{us['payroll']:>+9.0f} {them['payroll']:>+9.0f} "
                f"{us['microsim_total']:>+8.0f} {them['microsim_total']:>+8.0f} "
                f"{bridged:>+8.0f} {them['publishable']:>+7.0f}"
            )

    print("\nTHE PATTERN")
    print("  Payroll responses agree remarkably well across every variant --")
    print("  both models put the same wage distribution against the same cap.")
    print("  The divergence is concentrated in the income tax response to the")
    print("  capital shock, consistent with our larger realized-capital base,")
    print("  allocation by realized income rather than SCF wealth (top-heavier,")
    print("  higher marginal rates), and ordinary-rate retirement routing.")

    print("\nTILT RATIOS (revenue with shares fixed / as forecast, proportional)")
    for name in ("Slow", "Moderate", "Rapid"):
        v = VARIANT[name]
        them_fixed = theirs.loc[f"ai_{v}_F_S0_V1", "total_with_macro_cit"]
        them_realloc = theirs.loc[f"ai_{v}_R_S0_V1", "total_with_macro_cit"]
        ours_fixed = our_row(ours, name, "none", shares_fixed=True)
        ours_realloc = our_row(ours, name, "proportional")
        line = (
            f"  {name:9s} theirs {them_fixed:>+6.0f}/{them_realloc:>+6.0f}"
            f" = {them_fixed / them_realloc:4.2f}x"
        )
        if ours_fixed and ours_realloc:
            a = ours_fixed["total_rev_change_b"]
            b = ours_realloc["total_rev_change_b"]
            line += f"    ours {a:>+6.0f}/{b:>+6.0f} = {a / b:4.2f}x"
        print(line)

    rapid_exp = our_row(ours, "Rapid", "expansive")
    if rapid_exp is not None:
        us = our_side(rapid_exp)
        cit = theirs.loc["ai_R_R_S3_V1", "macro_cit_delta"]
        publ = theirs.loc["ai_R_R_S3_V1", "total_with_macro_cit"]
        bridged = us["microsim_total"] + cit
        print("\nHEADLINE, LIKE FOR LIKE (Rapid + expansive)")
        print(
            f"  ours bridged {bridged:+,.0f}B vs theirs {publ:+,.0f}B"
            f"  ({bridged / publ:.2f}x; "
            f"{bridged / THEIR_CBO_2030_TOTAL_REVENUE_B:.1%} vs "
            f"{publ / THEIR_CBO_2030_TOTAL_REVENUE_B:.1%} of CBO 2030 revenue)"
        )

    print("\nSTILL NOT NETTED OUT")
    print("  - Capital allocation: SCF total wealth (theirs) vs realized capital")
    print("    income (ours); they note a narrower base is more top-concentrated.")
    print("  - Pass-through: their active/passive-aware split vs our single rule.")
    print("  - Microdata: 2015 IRS PUF aged to 2030 vs Microcosm survey build.")
    print("  - Their capital base is not observable here; eta ~ 1 in their prose")
    print("    implies about $4.6T vs our $5.3T, but the wedge cannot confirm it.")


if __name__ == "__main__":
    main()
