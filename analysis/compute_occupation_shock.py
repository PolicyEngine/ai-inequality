"""Occupation-based AI wage shock simulation.

Uses Yale AI-Employment-Model exposure scores mapped to PolicyEngine's
POCCU2 occupation codes (via CPS ASEC codebook) to apply differential
wage shocks: high-AI-exposure occupations take larger wage cuts.

Two scenarios:
  - gdp_neutral: total employment income conserved, redistribution only
  - displacement: total employment income falls by exposure-weighted amount

Outputs: analysis/outputs/occupation_shock.json
"""

import json
import os
import numpy as np
import pandas as pd
from policyengine_us import Microsimulation

from .constants import YEAR
from .metrics import extract_results as _extract_results
from .compute_shift_sweep import _revenue_components, net_fiscal_impact

YALE_RESOURCES = os.environ.get(
    "YALE_RESOURCES",
    os.path.join(os.path.dirname(__file__), "..", "external", "AI-Employment-Model", "resources"),
)
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "outputs", "occupation_shock.json")

# ── Step 1: Compute automation exposure by SOC major group ───────────────────

def build_soc_major_exposure():
    tasks = pd.read_csv(os.path.join(YALE_RESOURCES, "onet_tasks_v2.csv"))
    exposure = pd.read_csv(os.path.join(YALE_RESOURCES, "automation_vs_augmentation_by_task_v2.csv"))
    oes = pd.read_csv(os.path.join(YALE_RESOURCES, "national_M2024_dl.csv"))

    tasks["task_key"] = tasks["Task"].str.lower().str.strip()
    exposure["task_key"] = exposure["task_name"].str.lower().str.strip()
    merged = tasks.merge(exposure, on="task_key", how="inner")
    merged["automation"] = merged["directive"] + merged["feedback_loop"]
    merged["major"] = merged["O*NET-SOC Code"].str[:2].astype(int)

    oes_major = (
        oes[oes["O_GROUP"] == "major"][["OCC_CODE", "TOT_EMP"]]
        .copy()
        .assign(major=lambda d: d["OCC_CODE"].str[:2].astype(int))
    )

    soc_exp = (
        merged.groupby(["major", "O*NET-SOC Code"])
        .apply(lambda g: pd.Series({
            "automation": np.average(g["automation"], weights=g["pct"]) if g["pct"].sum() > 0 else g["automation"].mean()
        }))
        .reset_index()
    )

    result = (
        soc_exp.merge(oes_major[["major", "TOT_EMP"]], on="major", how="left")
        .groupby("major")
        .apply(lambda g: np.average(g["automation"], weights=g["TOT_EMP"].fillna(1)))
        .reset_index()
    )
    result.columns = ["major", "automation"]
    return dict(zip(result["major"], result["automation"]))


# ── Step 2: POCCU2 → SOC major group mapping ─────────────────────────────────
# Source: CPS ASEC 2023 technical documentation, Appendix G (POCCU2 codes)

POCCU2_TO_SOC = {
    # Code 0: not employed → skip
    1:  11,   # Chief executives & top managers → Management
    2:  11,   # Other managers (purchasing, construction, agricultural) → Management
    3:  11,   # Education/food service/healthcare/social service managers → Management
    4:  11,   # Agents & business managers of artists/athletes → Management
    5:  13,   # Business operations specialists → Business/Financial
    6:  13,   # Accountants and auditors → Business/Financial
    7:  13,   # Financial specialists → Business/Financial
    8:  15,   # Computer occupations (software, IT, cybersecurity) → Computer/Math
    9:  15,   # Actuaries, operations research analysts → Computer/Math
    10: 17,   # Architects → Architecture/Engineering
    11: 17,   # Surveyors, cartographers → Architecture/Engineering
    12: 17,   # Engineers & engineering technicians → Architecture/Engineering
    13: 19,   # Scientists (life, physical, environmental) → Life/Social Science
    14: 19,   # Economists → Life/Social Science
    15: 19,   # Psychologists, social scientists → Life/Social Science
    16: 19,   # Science technicians → Life/Social Science
    17: 21,   # Community and social service → Community/Social Service
    18: 23,   # Lawyers, judges → Legal
    19: 23,   # Paralegals, legal support → Legal
    20: 25,   # Postsecondary teachers → Education/Library
    21: 25,   # K-12 teachers → Education/Library
    22: 25,   # Librarians, teaching assistants → Education/Library
    23: 27,   # Arts, design, entertainment, sports, media → Arts/Entertainment
    24: 29,   # Physicians, dentists, pharmacists, etc. → Healthcare Practitioners
    25: 29,   # Nurses, therapists → Healthcare Practitioners
    26: 29,   # Veterinarians → Healthcare Practitioners
    27: 29,   # Other health technologists & practitioners → Healthcare Practitioners
    28: 31,   # Healthcare support → Healthcare Support
    29: 33,   # First-line supervisors of protective service → Protective Service
    30: 33,   # Firefighters, police, correctional officers → Protective Service
    31: 33,   # Security guards, other protective service → Protective Service
    32: 35,   # Chefs, head cooks, food prep supervisors → Food Prep/Serving
    33: 35,   # Food prep workers, waiters, bartenders → Food Prep/Serving
    34: 37,   # Supervisors of housekeeping/landscaping → Building/Grounds
    35: 37,   # Janitors, maids, landscaping workers → Building/Grounds
    36: 39,   # Supervisors of personal care → Personal Care
    37: 39,   # Personal care occupations → Personal Care
    38: 41,   # First-line supervisors of sales → Sales
    39: 41,   # Sales occupations → Sales
    40: 43,   # Office & administrative support → Office/Admin Support
    41: 45,   # Farming, fishing, forestry → Farming/Fishing/Forestry
    42: 47,   # First-line supervisors of construction → Construction/Extraction
    43: 47,   # Carpenters → Construction/Extraction
    44: 47,   # Construction workers (equipment operators, laborers) → Construction/Extraction
    45: 47,   # Electricians → Construction/Extraction
    46: 47,   # Other construction trades → Construction/Extraction
    47: 47,   # Extraction workers → Construction/Extraction
    48: 49,   # Installation, maintenance, repair → Installation/Repair
    49: 51,   # Production occupations → Production
    50: 53,   # Transport supervisors, pilots, air traffic control → Transportation
    51: 53,   # Bus/taxi/truck drivers, other transport → Transportation
    52: None, # Military → no SOC equivalent
    # Code 53: never worked → skip
}

SOC_LABELS = {
    11: "Management", 13: "Business/Financial", 15: "Computer/Math",
    17: "Architecture/Engineering", 19: "Life/Social Science",
    21: "Community/Social Service", 23: "Legal", 25: "Education/Library",
    27: "Arts/Entertainment", 29: "Healthcare Practitioners",
    31: "Healthcare Support", 33: "Protective Service",
    35: "Food Prep/Serving", 37: "Building/Grounds",
    39: "Personal Care", 41: "Sales", 43: "Office/Admin Support",
    45: "Farming/Fishing", 47: "Construction/Extraction",
    49: "Installation/Repair", 51: "Production", 53: "Transportation",
}


def main():
    print("=" * 65)
    print("OCCUPATION-BASED AI WAGE SHOCK")
    print("=" * 65)

    print("\nBuilding SOC major group exposure scores...")
    soc_exposure = build_soc_major_exposure()

    # Map POCCU2 → automation score
    poccu2_exposure = {}
    mean_exposure = np.mean(list(soc_exposure.values()))
    for code, soc in POCCU2_TO_SOC.items():
        if soc is None:
            poccu2_exposure[code] = mean_exposure  # military: use mean
        else:
            poccu2_exposure[code] = soc_exposure.get(soc, mean_exposure)

    print("\nExposure by occupation group:")
    print(f"{'POCCU2':>7} {'SOC Label':<30} {'Automation':>10}")
    print("-" * 50)
    seen_soc = set()
    for code in sorted(poccu2_exposure):
        soc = POCCU2_TO_SOC.get(code)
        if soc not in seen_soc:
            label = SOC_LABELS.get(soc, "Other")
            print(f"{code:>7}   {label:<30} {poccu2_exposure[code]:.3f}")
            seen_soc.add(soc)

    print("\nRunning baseline microsimulation...")
    baseline = Microsimulation()

    occ_codes = np.array(baseline.calculate("detailed_occupation_recode", period=YEAR))
    emp_income = np.array(baseline.calculate("employment_income", period=YEAR))
    pw = np.array(baseline.calculate("person_weight", period=YEAR))

    # Assign exposure score to each person
    exposure_scores = np.array([poccu2_exposure.get(int(c), mean_exposure) for c in occ_codes])
    # Unexposed (code 0, 53) get 0 exposure and no shock
    exposure_scores[occ_codes == 0] = 0
    exposure_scores[occ_codes == 53] = 0

    # ── Scenario: GDP-neutral differential shock ─────────────────────────────
    # High-exposure workers lose more wages; scale so total wages conserved.
    # Shock = exposure_score * max_shock_rate, then rescale.
    # Workers at mean exposure get zero change; above-mean lose wages,
    # below-mean gain wages.
    MAX_SHOCK = 0.30  # max 30% wage reduction at exposure=1.0

    # Only shock employed workers (positive wages)
    employed = (emp_income > 0) & (occ_codes > 0) & (occ_codes < 53)
    exp_emp = exposure_scores[employed]
    mean_exp_weighted = float(np.average(exp_emp, weights=(emp_income * pw)[employed]))
    print(f"\nMean employment-income-weighted exposure: {mean_exp_weighted:.3f}")

    # Shock relative to mean: positive exposure → wage cut, below mean → wage gain
    relative_shock = (exposure_scores - mean_exp_weighted) * MAX_SHOCK / (1 - mean_exp_weighted)
    new_wages = emp_income * (1 - relative_shock)
    new_wages = np.maximum(new_wages, 0)  # no negative wages

    # Verify conservation
    base_total = float((emp_income * pw).sum())
    shock_total = float((new_wages * pw).sum())
    print(f"Total wages: ${base_total/1e12:.3f}T → ${shock_total/1e12:.3f}T "
          f"(Δ = ${(shock_total - base_total)/1e9:+.1f}B)")

    # Apply to branch
    branch = baseline.get_branch("occ_shock")
    branch.set_input("employment_income", YEAR, new_wages)

    print("\nComputing baseline metrics...")
    base_metrics = _extract_results(baseline, "Baseline")
    base_rev = _revenue_components(baseline)

    print("Computing occupation shock metrics...")
    shock_metrics = _extract_results(branch, "Occ shock")
    shock_rev = _revenue_components(branch)
    delta = net_fiscal_impact(shock_rev, base_rev)

    # ── Per-occupation-group summary ─────────────────────────────────────────
    occ_summary = []
    for soc_code, label in SOC_LABELS.items():
        # Find POCCU2 codes mapping to this SOC
        codes = [c for c, s in POCCU2_TO_SOC.items() if s == soc_code]
        mask = np.isin(occ_codes, codes) & employed
        if mask.sum() == 0:
            continue
        pop = float((pw[mask]).sum() / 1e6)
        mean_wage_before = float(np.average(emp_income[mask], weights=pw[mask]))
        mean_wage_after = float(np.average(new_wages[mask], weights=pw[mask]))
        exp = soc_exposure.get(soc_code, mean_exposure)
        occ_summary.append({
            "soc_major": soc_code,
            "label": label,
            "automation_score": round(exp, 4),
            "employed_m": round(pop, 2),
            "mean_wage_before": round(mean_wage_before),
            "mean_wage_after": round(mean_wage_after),
            "wage_change_pct": round((mean_wage_after / mean_wage_before - 1) * 100, 1),
        })

    occ_summary.sort(key=lambda x: x["automation_score"], reverse=True)
    print(f"\n{'Occupation':<30} {'Exposure':>9} {'Pop(M)':>7} {'Wage Δ':>8}")
    print("-" * 57)
    for r in occ_summary:
        print(f"{r['label']:<30} {r['automation_score']:>9.3f} {r['employed_m']:>7.1f} {r['wage_change_pct']:>+7.1f}%")

    result = {
        "year": YEAR,
        "method": "GDP-neutral differential shock (max 30% at exposure=1.0)",
        "mean_exposure": round(mean_exp_weighted, 4),
        "baseline": {
            "net_gini": base_metrics["net_gini"],
            "market_gini": base_metrics["market_gini"],
            "spm_poverty_rate": base_metrics["spm_poverty_rate"],
            "fed_revenue_b": base_metrics["fed_revenue"] / 1e9,
        },
        "shocked": {
            "net_gini": shock_metrics["net_gini"],
            "market_gini": shock_metrics["market_gini"],
            "spm_poverty_rate": shock_metrics["spm_poverty_rate"],
            "fed_revenue_b": shock_metrics["fed_revenue"] / 1e9,
            "revenue_change_b": delta["total_change"] / 1e9,
        },
        "occupation_groups": occ_summary,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {OUTPUT_PATH}")
    print(f"\nBaseline net Gini: {base_metrics['net_gini']:.4f}")
    print(f"Shocked net Gini:  {shock_metrics['net_gini']:.4f}")
    print(f"Poverty: {base_metrics['spm_poverty_rate']:.2%} → {shock_metrics['spm_poverty_rate']:.2%}")
    print(f"Revenue change: ${delta['total_change']/1e9:+.1f}B")


if __name__ == "__main__":
    main()
