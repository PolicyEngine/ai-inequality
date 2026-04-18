"""Compute baseline-level totals (not deltas) and merge into shift_sweep.json.

Captures nationwide baseline aggregates plus per-state baselines for:
  - federal income tax (after and before refundable credits)
  - employer + employee payroll + self-employment tax
  - state income tax before refundable credits
  - state refundable credits
  - state benefits
  - household_tax_before_refundable_credits (federal + state + employee + SE)
  - household_benefits (all benefits)

These let the website render charts in either $B or "% of baseline income
+ payroll tax revenue" mode without rerunning the full shift sweep.
"""

import json
import os

import numpy as np

from .compute_shift_sweep import OUTPUT_PATH
from .constants import YEAR
from .policyengine_runtime import managed_us_microsimulation


def _hh_sum(sim, var):
    return float(sim.calculate(var, map_to="household", period=YEAR).sum())


def _tu_sum(sim, var):
    return float(sim.calculate(var, period=YEAR).sum())


def _national_totals(sim):
    return {
        "fed_income_tax": _hh_sum(sim, "income_tax"),
        "fed_income_tax_before_refundable_credits": _tu_sum(
            sim, "income_tax_before_refundable_credits"
        ),
        "state_tax_before_refundable_credits": _hh_sum(
            sim, "household_state_tax_before_refundable_credits"
        ),
        "state_refundable_credits": _hh_sum(
            sim, "household_refundable_state_tax_credits"
        ),
        "state_benefits": _hh_sum(sim, "household_state_benefits"),
        "household_tax_before_refundable_credits": _hh_sum(
            sim, "household_tax_before_refundable_credits"
        ),
        "household_refundable_tax_credits": _hh_sum(
            sim, "household_refundable_tax_credits"
        ),
        "household_benefits": _hh_sum(sim, "household_benefits"),
        "employer_payroll_tax": _hh_sum(sim, "employer_payroll_tax"),
        "employee_social_security_tax": _hh_sum(sim, "employee_social_security_tax"),
        "employee_medicare_tax": _hh_sum(sim, "employee_medicare_tax"),
        "employer_social_security_tax": _hh_sum(sim, "employer_social_security_tax"),
        "employer_medicare_tax": _hh_sum(sim, "employer_medicare_tax"),
        "self_employment_tax": _hh_sum(sim, "self_employment_tax"),
    }


STATE_VARIABLES = (
    "household_state_tax_before_refundable_credits",
    "household_refundable_state_tax_credits",
    "household_state_benefits",
    "household_tax_before_refundable_credits",
    "household_refundable_tax_credits",
    "household_benefits",
    "income_tax",
    "employer_payroll_tax",
    "employee_social_security_tax",
    "employee_medicare_tax",
    "self_employment_tax",
)


def _per_state_totals(sim):
    state_code = np.asarray(
        sim.calculate("state_code_str", map_to="household", period=YEAR)
    )
    hh_weight = np.asarray(
        sim.calculate("household_weight", period=YEAR), dtype=float
    )
    unique_states = np.unique(state_code)
    per_state = {str(code): {} for code in unique_states}

    for var in STATE_VARIABLES:
        values = np.asarray(
            sim.calculate(var, map_to="household", period=YEAR), dtype=float
        )
        weighted = values * hh_weight
        for code in unique_states:
            mask = state_code == code
            per_state[str(code)][var] = float(weighted[mask].sum())

    return per_state


def main():
    print("Loading microsimulation...")
    sim = managed_us_microsimulation()

    print("Computing national baseline totals...")
    national = _national_totals(sim)
    print("Computing per-state baseline totals...")
    per_state = _per_state_totals(sim)

    baseline_totals = {"national": national, "per_state": per_state}

    if not os.path.exists(OUTPUT_PATH):
        print(f"\nshift_sweep.json not found at {OUTPUT_PATH}")
        standalone = os.path.join(
            os.path.dirname(__file__), "outputs", "baseline_totals.json"
        )
        with open(standalone, "w") as f:
            json.dump(baseline_totals, f, indent=2)
        print(f"Saved to {standalone}")
        return

    with open(OUTPUT_PATH) as f:
        data = json.load(f)
    data.setdefault("metadata", {}).setdefault("baseline_facts", {})[
        "totals"
    ] = baseline_totals
    with open(OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nMerged baseline totals into {OUTPUT_PATH}")

    income_plus_payroll = (
        national["fed_income_tax"]
        + national["employer_payroll_tax"]
        + national["employee_social_security_tax"]
        + national["employee_medicare_tax"]
        + national["self_employment_tax"]
    )
    print(
        f"\nFederal baseline: income tax + payroll tax base = "
        f"${income_plus_payroll / 1e12:.2f}T"
    )


if __name__ == "__main__":
    main()
