"""Decompose the transfer response, program by program, including health.

The headline run (`compute_ai_scenarios.py`) stores four named benefit
components plus a total, which leaves two gaps this script closes:

  1. Part of the non-credit benefit swing across the Rapid wage-inequality
     variants sits in programs the headline run never separated (school
     meals, housing, the commodity food program and others): $4.3B of the
     $27.8B swing once Head Start and Early Head Start are out of net income
     (`NET_INCOME_EXCLUDED_BENEFITS`), against $18.6B of $42.1B when the
     published run still counted them.

  2. Health programs are absent from `household_benefits` entirely: the
     registry routes them through `household_health_benefits`, which returns
     zero unless `gov.simulation.include_health_benefits_in_net_income` is
     enabled, and it is off by default. The unconditional value of the same
     coverage lives in `healthcare_benefit_value` (Medicaid, MSP, CHIP, the
     assigned ACA premium tax credit, the Basic Health Program and two state
     programs), which is what `household_net_income_including_health_benefits`
     adds. Nothing here double-counts the tax side: the federal refundable
     credit registry explicitly excludes the premium tax credit.

Health coverage cannot move the SPM poverty results: `spm_unit_net_income`
counts cash benefits and subtracts out-of-pocket medical expenses, and never
adds coverage value. So this is reported as a variant of the income and
inequality measures, not a replacement basis for the headline numbers.

Runs the 2030 baseline plus the three Rapid wage-inequality variants — four
simulations rather than the headline run's twelve-plus.

Usage:
    python -m analysis.compute_transfer_detail
"""

from __future__ import annotations

import argparse
import gc
import json
import os

from .ai_scenarios import (
    CAPITAL_INCOME_VARS,
    TARGET_YEAR,
    apply_ai_scenario,
    build_scenario,
)
from .compute_ai_scenarios import (
    _package_version,
    append_checkpoint,
    load_checkpoint,
)
from .policyengine_runtime import (
    managed_us_microsimulation,
    policyengine_bundle,
    runtime_fingerprint,
)

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "outputs", "transfer_detail.json"
)

#: Checkpoints live under $HOME, not the session scratchpad, which is wiped on
#: restart and has cost this analysis a completed run before.
CHECKPOINT_PATH = os.path.join(
    os.path.expanduser("~"),
    ".policyengine-runs",
    "ai-inequality-transfer-detail.jsonl",
)

#: The programs `household_benefits` adds at policyengine-us 1.764.6, kept as
#: the record of what the published run decomposed. Runs read the live list
#: from the engine instead (`benefit_programs`), because it changes across
#: versions: 2.x folds `head_start` and `early_head_start` into
#: `household_head_start_benefits`, counts `housing_assistance` instead of
#: `spm_unit_capped_housing_subsidy`, and adds `trump_dividend`. Inputs the
#: shock cannot move (Social Security, unemployment compensation, workers'
#: compensation, child support) stay in the decomposition so their invariance
#: is visible rather than assumed.
BENEFIT_PROGRAMS_1_764_6 = [
    "social_security",
    "ssi",
    "snap",
    "wic",
    "free_school_meals",
    "reduced_price_school_meals",
    "acp",
    "ebb",
    "tanf",
    "high_efficiency_electric_home_rebate",
    "residential_efficiency_electrification_rebate",
    "unemployment_compensation",
    "child_support_received",
    "workers_compensation",
    "educational_assistance",
    "financial_assistance",
    "survivor_benefits",
    "head_start",
    "early_head_start",
    "basic_income",
    "spm_unit_capped_housing_subsidy",
    "household_state_benefits",
    "commodity_supplemental_food_program",
]


def benefit_programs(sim, year):
    """Every program the running engine's `household_benefits` adds.

    Read from `gov.household.household_benefits`, so the decomposition sums
    back to the total on whichever engine version runs.
    """
    return list(
        sim.tax_benefit_system.parameters(f"{year}-01-01").gov.household.household_benefits
    )


#: Components of `healthcare_benefit_value`, which is unconditional.
HEALTH_PROGRAMS = [
    "medicaid_cost",
    "msp_cost",
    "chip",
    "assigned_aca_ptc",
    "basic_health_program",
    "co_omnisalud",
    "or_healthier_oregon_cost",
]

AGGREGATES = [
    "household_benefits",
    "healthcare_benefit_value",
    "household_net_income",
    "household_net_income_including_health_benefits",
    "household_refundable_tax_credits",
]

VARIANTS = ["compressive", "proportional", "expansive"]


def _sum(sim, variable, year):
    """Weighted national total for a variable, at whatever entity it lives on."""
    return float(sim.calculate(variable, year).sum())


def program_totals(sim, year, programs):
    """Every benefit program, the health components, and the aggregates."""
    totals = {}
    for variable in list(programs) + HEALTH_PROGRAMS + AGGREGATES:
        try:
            totals[variable] = _sum(sim, variable, year)
        except Exception as error:  # noqa: BLE001 - report, do not abort the run
            totals[variable] = None
            print(f"    ! {variable}: {type(error).__name__}: {error}", flush=True)
    return totals


def _deltas(scenario_totals, baseline_totals):
    return {
        name: (
            None
            if scenario_totals.get(name) is None or baseline_totals.get(name) is None
            else (scenario_totals[name] - baseline_totals[name]) / 1e9
        )
        for name in scenario_totals
    }


def run(year=TARGET_YEAR, verbose=True, output_path=None, checkpoint_path=None):
    output_path = output_path or OUTPUT_PATH
    checkpoint_path = CHECKPOINT_PATH if checkpoint_path is None else checkpoint_path
    if checkpoint_path == "none":
        checkpoint_path = None
    fingerprint = runtime_fingerprint()
    stamp = fingerprint["digest"] if checkpoint_path else None
    checkpoint = load_checkpoint(checkpoint_path, stamp)

    if "baseline" in checkpoint and "programs" in checkpoint:
        baseline_totals = checkpoint["baseline"]
        programs = checkpoint["programs"]
        bundle = checkpoint.get("bundle") or {}
        if verbose:
            print("baseline ... (from checkpoint)", flush=True)
    else:
        if verbose:
            print("baseline ...", flush=True)
        sim = managed_us_microsimulation()
        programs = benefit_programs(sim, year)
        baseline_totals = program_totals(sim, year, programs)
        bundle = policyengine_bundle(sim)
        append_checkpoint(checkpoint_path, "baseline", baseline_totals, stamp)
        append_checkpoint(checkpoint_path, "programs", programs, stamp)
        append_checkpoint(checkpoint_path, "bundle", bundle or {}, stamp)
        del sim
        gc.collect()

    rows = {}
    for variant in VARIANTS:
        key = f"rapid:{variant}"
        if key in checkpoint:
            rows[variant] = checkpoint[key]
            if verbose:
                print(f"Rapid / {variant} ... (from checkpoint)", flush=True)
            continue

        if verbose:
            print(f"Rapid / {variant} ...", flush=True)
        scenario = build_scenario("Rapid", inequality=variant)
        sim = managed_us_microsimulation()
        branch, _diagnostics = apply_ai_scenario(
            sim,
            f"transfer_detail_{variant}",
            scenario,
            year=year,
            capital_income_vars=CAPITAL_INCOME_VARS,
        )
        totals = program_totals(branch, year, programs)
        rows[variant] = totals
        append_checkpoint(checkpoint_path, key, totals, stamp)

        if verbose:
            d = _deltas(totals, baseline_totals)
            print(
                f"    benefits {d['household_benefits']:+,.1f}B"
                f"  health {d['healthcare_benefit_value']:+,.1f}B"
                f"  snap {d['snap']:+,.1f}B",
                flush=True,
            )
        del branch, sim
        gc.collect()

    payload = {
        "year": year,
        "metadata": {
            "policyengine_version": (
                bundle.get("policyengine_version") or _package_version("policyengine")
            ),
            "country_model_version": (
                bundle.get("model_version") or _package_version("policyengine-us")
            ),
            "certified_data_build_id": bundle.get("certified_data_build_id"),
            "legacy_input_renames": bundle.get("legacy_input_renames", {}),
            "net_income_excluded_benefits": bundle.get(
                "net_income_excluded_benefits", []
            ),
            "runtime_fingerprint": fingerprint,
            "benefit_programs": programs,
            "benefit_programs_sum_residual_b": _sum_residual_b(
                baseline_totals, programs
            ),
            "note": (
                "healthcare_benefit_value is unconditional; household_health_benefits "
                "is gated on gov.simulation.include_health_benefits_in_net_income and "
                "is zero in these runs. SPM poverty excludes coverage value by "
                "construction, so health is a variant of income and inequality only."
            ),
        },
        "baseline_totals": baseline_totals,
        "scenarios": {
            variant: {
                "totals": totals,
                "deltas_b": _deltas(totals, baseline_totals),
            }
            for variant, totals in rows.items()
        },
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as handle:
        json.dump(payload, handle, indent=2, default=float)

    if verbose:
        _report(payload)
    return payload


def _sum_residual_b(totals, programs):
    """household_benefits minus the sum of its programs, $B; None if unscored."""
    values = [totals.get(name) for name in programs]
    total = totals.get("household_benefits")
    if total is None or any(value is None for value in values):
        return None
    return (total - sum(values)) / 1e9


def _report(payload):
    scenarios = payload["scenarios"]
    if not all(v in scenarios for v in VARIANTS):
        return
    print("\nPROGRAM-BY-PROGRAM RESPONSE ($B vs baseline)")
    header = f"{'program':44s} {'compress':>9s} {'prop':>8s} {'expand':>9s} {'swing':>8s}"
    print(header)
    print("-" * len(header))
    ordered = payload["metadata"]["benefit_programs"] + ["household_benefits"] + HEALTH_PROGRAMS + [
        "healthcare_benefit_value"
    ]
    for name in ordered:
        vals = [scenarios[v]["deltas_b"].get(name) for v in VARIANTS]
        if any(x is None for x in vals):
            continue
        if all(abs(x) < 0.05 for x in vals):
            continue
        swing = vals[2] - vals[0]
        marker = "  <-- total" if name in ("household_benefits", "healthcare_benefit_value") else ""
        print(
            f"{name:44s} {vals[0]:>+9.2f} {vals[1]:>+8.2f} {vals[2]:>+9.2f} "
            f"{swing:>+8.2f}{marker}"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default=OUTPUT_PATH)
    parser.add_argument(
        "--checkpoint",
        default=CHECKPOINT_PATH,
        help="Resume store; 'none' disables resuming.",
    )
    args = parser.parse_args(argv)
    run(output_path=args.output, checkpoint_path=args.checkpoint)


if __name__ == "__main__":
    main()
