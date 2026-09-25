"""Run the forecaster-calibrated AI scenarios through PolicyEngine-US.

Produces `analysis/outputs/ai_scenarios.json`: for each scenario, the revenue
decomposition, inequality and poverty metrics, decile shares, state-level
deltas, and the diagnostics needed to check the shock landed where it was
aimed.

Three families of run:

  scenarios      Slow / Moderate / Rapid, each with a shares-fixed
                 counterfactual and three labor-inequality variants.
  realization    Rapid / proportional swept over the share of the incremental
                 capital flow that reaches the individual tax base. The
                 Budget Lab holds this at 1.0 and flags it as a limitation;
                 it turns out to be the assumption the revenue estimate is
                 most sensitive to.
  capital scope  The same scenario with and without taxable retirement
                 distributions in the capital set, because including them
                 routes part of the capital shock through ordinary rates.

Usage:
    python -m analysis.compute_ai_scenarios
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import warnings
from importlib.metadata import PackageNotFoundError, version

from .ai_scenarios import (
    CAPITAL_INCOME_VARS,
    CAPITAL_INCOME_VARS_EXCL_RETIREMENT,
    CORPORATE_TAX_SCOPE_NOTE,
    TARGET_YEAR,
    apply_ai_scenario,
    build_scenario,
    default_scenario_grid,
    modelled_factor_shares,
    social_security_cap_diagnostics,
)
from .fiscal import (
    net_fiscal_impact,
    revenue_components,
    state_revenue_components,
)
from .metrics import extract_results
from .policyengine_runtime import (
    managed_us_microsimulation,
    policyengine_bundle,
    runtime_fingerprint,
)
from .website_exports import ai_scenarios_website_payload

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "outputs", "ai_scenarios.json")

#: Trimmed, camel-cased payload the site imports. Checked in, unlike the full
#: run output.
WEBSITE_OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "data", "aiScenariosData.json"
)

#: Append-only record of completed units, so a killed run resumes instead of
#: starting over. Lives beside the run output, outside any temp directory that
#: a restart might clear.
CHECKPOINT_PATH = os.path.join(
    os.path.dirname(__file__), "outputs", "ai_scenarios_checkpoint.jsonl"
)

BASELINE_KEY = "baseline"

MODEL_URL = "https://www.policyengine.org/us/model"

DESCRIPTION = (
    "AI scenarios calibrated to the Karger et al. (2026) forecaster survey as "
    "implemented by The Budget Lab (Iselin and Nunn, 2026-07-20). Labor and "
    "capital income are grown at scenario-specific rates derived from a "
    "target 2030 labor share, with an optional log-scale spread change in the "
    "labor income distribution. Static current-law microsimulation: no "
    "behavioural response, no labor supply response, no corporate sector."
)

REALIZATION_SWEEP = (0.0, 0.25, 0.50, 0.75, 1.0)

#: Buckets carried into the JSON, mirroring the shift sweep so the website can
#: reuse its chart code. Names on the left, `net_fiscal_impact` keys on the
#: right; all values are reported in billions.
FISCAL_FIELDS = (
    ("total_rev_change_b", "total_change"),
    ("household_tax_change_b", "household_tax_before_refundable_credits_change"),
    ("refundable_credits_change_b", "household_refundable_tax_credits_change"),
    ("benefits_change_b", "household_benefits_change"),
    ("employer_payroll_change_b", "employer_payroll_tax_change"),
    (
        "fed_income_tax_change_b",
        "fed_income_tax_before_refundable_credits_change",
    ),
    ("fed_main_rates_change_b", "fed_income_tax_main_rates_change"),
    ("fed_capital_gains_tax_change_b", "fed_capital_gains_tax_change"),
    ("fed_amt_change_b", "fed_alternative_minimum_tax_change"),
    ("fed_niit_change_b", "fed_net_investment_income_tax_change"),
    ("employee_ss_tax_change_b", "employee_social_security_tax_change"),
    ("employee_medicare_tax_change_b", "employee_medicare_tax_change"),
    ("employer_ss_tax_change_b", "employer_social_security_tax_change"),
    ("employer_medicare_tax_change_b", "employer_medicare_tax_change"),
    ("self_employment_tax_change_b", "self_employment_tax_change"),
    (
        "state_tax_change_b",
        "state_tax_before_refundable_credits_change",
    ),
    ("state_refundable_credits_change_b", "state_refundable_credits_change"),
    ("state_benefits_change_b", "state_benefits_change"),
    ("eitc_change_b", "eitc_change"),
    ("refundable_ctc_change_b", "refundable_ctc_change"),
    ("snap_change_b", "snap_change"),
    ("ssi_change_b", "ssi_change"),
    ("tanf_change_b", "tanf_change"),
    ("wic_change_b", "wic_change"),
    ("health_benefits_change_b", "health_benefits_change"),
    ("market_income_change_b", "household_market_income_change"),
    ("net_income_change_b", "household_net_income_change"),
    ("identity_residual_b", "_identity_residual"),
)

#: Payroll receipts, the line the Social Security cap acts on. Kept separate so
#: the cap mechanism can be shown rather than asserted.
PAYROLL_FIELDS = (
    "employee_ss_tax_change_b",
    "employer_ss_tax_change_b",
    "employee_medicare_tax_change_b",
    "employer_medicare_tax_change_b",
    "self_employment_tax_change_b",
)


def _package_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _branch_name(scenario):
    """Deterministic, PolicyEngine-safe branch name derived from the label.

    Deterministic rather than hash-based so a rerun produces the same branch
    names and the run stays diffable.
    """
    slug = "".join(char if char.isalnum() else "_" for char in scenario.label.lower())
    return f"ai_{slug}"[:48]


def _fiscal_row(delta):
    row = {name: delta.get(key, 0.0) / 1e9 for name, key in FISCAL_FIELDS}
    row["payroll_change_b"] = sum(row[field] for field in PAYROLL_FIELDS)
    return row


def _diff(scenario, baseline, key):
    return scenario.get(key, 0.0) - baseline.get(key, 0.0)


def _state_delta_rows(scenario_states, baseline_states):
    """Per-state fiscal deltas in billions, keyed by two-letter code."""
    rows = {}
    for code in set(scenario_states) | set(baseline_states):
        scenario = scenario_states.get(code, {})
        baseline = baseline_states.get(code, {})

        state_tax = _diff(
            scenario, baseline, "household_state_tax_before_refundable_credits"
        )
        state_credits = _diff(
            scenario, baseline, "household_refundable_state_tax_credits"
        )
        state_benefits = _diff(scenario, baseline, "household_state_benefits")
        rows[code] = {
            "state_tax_change_b": state_tax / 1e9,
            "state_refundable_credits_change_b": state_credits / 1e9,
            "state_benefits_change_b": state_benefits / 1e9,
            "state_net_change_b": (state_tax - state_credits - state_benefits) / 1e9,
            "federal_tax_change_b": _diff(
                scenario, baseline, "household_tax_before_refundable_credits"
            )
            / 1e9,
            "eitc_change_b": _diff(scenario, baseline, "eitc") / 1e9,
            "snap_change_b": _diff(scenario, baseline, "snap") / 1e9,
            "household_weight": scenario.get(
                "household_weight", baseline.get("household_weight", 0.0)
            ),
        }
    return rows


def _metrics_row(metrics):
    """The distributional summary carried for every scenario."""
    return {
        "market_gini": metrics["market_gini"],
        "net_gini": metrics["net_gini"],
        "net_gini_including_health_benefits": metrics[
            "net_gini_including_health_benefits"
        ],
        "spm_poverty_rate": metrics["spm_poverty_rate"],
        "net_top_10_share": metrics["top_10_share"],
        "net_top_1_share": metrics["top_1_share"],
        "net_top_0_1_share": metrics["top_0_1_share"],
        "net_bottom_10_share": metrics["bottom_10_share"],
        "net_bottom_20_share": metrics["bottom_20_share"],
        "market_top_10_share": metrics["market_top_10_share"],
        "market_top_1_share": metrics["market_top_1_share"],
        "market_top_0_1_share": metrics["market_top_0_1_share"],
        "mean_net_income": metrics["mean_net_income"],
        "mean_market_income": metrics["mean_market_income"],
        "decile_shares": metrics["decile_shares"],
        "fed_revenue_b": metrics["fed_revenue"] / 1e9,
        "state_revenue_b": metrics["state_revenue"] / 1e9,
    }


def _baseline_context(sim, year, capital_income_vars):
    """Aggregates that make the calibration mapping auditable."""
    shares = modelled_factor_shares(sim, year, capital_income_vars)
    context = {
        "modelled_labor_share": shares["modelled_labor_share"],
        "modelled_capital_share": shares["modelled_capital_share"],
        "positive_labor_income_t": shares["positive_labor_income"] / 1e12,
        "positive_capital_income_t": shares["positive_capital_income"] / 1e12,
    }
    context.update(social_security_cap_diagnostics(sim, year))
    return context


def _metadata(baseline, year, capital_income_vars):
    bundle = policyengine_bundle(baseline)
    return {
        "year": year,
        "description": DESCRIPTION,
        "model_url": MODEL_URL,
        "corporate_tax_scope_note": CORPORATE_TAX_SCOPE_NOTE,
        "capital_income_vars": list(capital_income_vars),
        "policyengine_version": (
            bundle.get("policyengine_version") or _package_version("policyengine")
        ),
        "country_model_package": bundle.get("model_package") or "policyengine-us",
        "country_model_version": (
            bundle.get("model_version") or _package_version("policyengine-us")
        ),
        "data_package": bundle.get("data_package"),
        "data_version": bundle.get("data_version"),
        "dataset_name": bundle.get("runtime_dataset"),
        "dataset_uri": bundle.get("runtime_dataset_uri"),
        "certified_data_build_id": bundle.get("certified_data_build_id"),
        "certified_data_artifact_sha256": bundle.get("certified_data_artifact_sha256"),
        "legacy_input_renames": bundle.get("legacy_input_renames", {}),
        "net_income_excluded_benefits": bundle.get(
            "net_income_excluded_benefits", []
        ),
        "runtime_fingerprint": runtime_fingerprint(),
        "policyengine_bundle": bundle or None,
    }


def load_checkpoint(path, fingerprint=None):
    """Read completed units from a checkpoint file, keyed by unit name.

    A run of this length should not be all-or-nothing, so each finished unit is
    appended as one JSON line. A process killed mid-write leaves a torn final
    line; that line is discarded rather than failing the resume.

    With ``fingerprint`` (``runtime_fingerprint()["digest"]``), only units that
    the same runtime wrote are returned. A unit from another engine, dataset
    or runtime revision, or one written before units carried a fingerprint, is
    skipped with a warning: resuming it would pass old numbers off as new.
    """
    if not path or not os.path.exists(path):
        return {}
    records = {}
    skipped = 0
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if fingerprint is not None and record.get("fingerprint") != fingerprint:
                skipped += 1
                continue
            records[record["key"]] = record["payload"]
    if skipped:
        warnings.warn(
            f"{path}: skipped {skipped} checkpoint unit(s) written by another "
            f"runtime (current fingerprint {fingerprint}); they will be recomputed.",
            stacklevel=2,
        )
    return records


def append_checkpoint(path, key, payload, fingerprint=None):
    """Append one completed unit, flushed to disk before returning."""
    if not path:
        return
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    record = {"key": key, "payload": payload}
    if fingerprint is not None:
        record["fingerprint"] = fingerprint
    with open(path, "a") as handle:
        handle.write(json.dumps(record, default=float))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _run_one(
    scenario,
    baseline_revenue,
    baseline_states,
    microsim_factory,
    year,
    capital_income_vars,
    verbose,
    checkpoint_path=None,
    checkpoint=None,
    checkpoint_key=None,
    checkpoint_fingerprint=None,
):
    """Run a single scenario from a fresh microsimulation."""
    key = checkpoint_key or scenario.label
    if checkpoint and key in checkpoint:
        if verbose:
            print(f"  {scenario.label} ... (from checkpoint)", flush=True)
        return checkpoint[key]

    if verbose:
        print(f"  {scenario.label} ...", flush=True)

    sim = microsim_factory()
    branch, diagnostics = apply_ai_scenario(
        sim,
        _branch_name(scenario),
        scenario,
        year=year,
        capital_income_vars=capital_income_vars,
    )

    metrics = extract_results(branch, scenario.label, year=year)
    revenue = revenue_components(branch, year=year)
    delta = net_fiscal_impact(revenue, baseline_revenue)
    states = state_revenue_components(branch, year=year)

    row = {
        "scenario": scenario.to_dict(),
        "diagnostics": diagnostics,
        "factor_shares": modelled_factor_shares(branch, year, capital_income_vars),
        "social_security_cap": social_security_cap_diagnostics(branch, year),
        "state_deltas": _state_delta_rows(states, baseline_states),
    }
    row.update(_metrics_row(metrics))
    row.update(_fiscal_row(delta))

    if verbose:
        print(
            f"    revenue {row['total_rev_change_b']:+,.1f}B"
            f"  payroll {row['payroll_change_b']:+,.1f}B"
            f"  poverty {row['spm_poverty_rate']:.2%}"
            f"  net Gini {row['net_gini']:.4f}",
            flush=True,
        )

    del branch, sim
    gc.collect()
    append_checkpoint(checkpoint_path, key, row, checkpoint_fingerprint)
    return row


def run_ai_scenarios(
    scenarios=None,
    year=TARGET_YEAR,
    microsim_factory=managed_us_microsimulation,
    capital_income_vars=CAPITAL_INCOME_VARS,
    realization_sweep=REALIZATION_SWEEP,
    include_capital_scope_sensitivity=True,
    verbose=False,
    checkpoint_path=CHECKPOINT_PATH,
):
    """Run the scenario grid plus sensitivities and return an export payload.

    Completed units are appended to `checkpoint_path` as they finish, and a
    rerun with the same path skips them. Each unit carries the runtime
    fingerprint (package versions and runtime revision), and only units the
    same runtime wrote are resumed, so an engine or dataset change recomputes
    everything instead of mixing vintages. Pass `checkpoint_path=None` to
    disable. Delete the file to force a clean run.
    """
    if scenarios is None:
        scenarios = default_scenario_grid()

    fingerprint = runtime_fingerprint()
    checkpoint_fingerprint = fingerprint["digest"] if checkpoint_path else None
    checkpoint = load_checkpoint(checkpoint_path, checkpoint_fingerprint)
    if checkpoint and verbose:
        print(f"Resuming: {len(checkpoint)} unit(s) already in the checkpoint.")

    if verbose:
        print(f"Baseline microsimulation for {year}...", flush=True)

    cached_baseline = checkpoint.get(BASELINE_KEY)
    if cached_baseline:
        if verbose:
            print("  (from checkpoint)", flush=True)
        baseline_row = cached_baseline["row"]
        baseline_revenue = cached_baseline["revenue"]
        baseline_states = cached_baseline["states"]
        metadata = cached_baseline["metadata"]
    else:
        baseline = microsim_factory()
        baseline_metrics = extract_results(baseline, "Baseline", year=year)
        baseline_revenue = revenue_components(baseline, year=year)
        baseline_states = state_revenue_components(baseline, year=year)
        metadata = _metadata(baseline, year, capital_income_vars)
        baseline_row = {
            "scenario": {"name": "Baseline", "label": "Baseline"},
            "context": _baseline_context(baseline, year, capital_income_vars),
        }
        baseline_row.update(_metrics_row(baseline_metrics))
        del baseline
        gc.collect()
        append_checkpoint(
            checkpoint_path,
            BASELINE_KEY,
            {
                "row": baseline_row,
                "revenue": baseline_revenue,
                "states": baseline_states,
                "metadata": metadata,
            },
            checkpoint_fingerprint,
        )

    if verbose:
        context = baseline_row["context"]
        print(
            f"  modelled labor share {context['modelled_labor_share']:.1%}"
            f"  (labor ${context['positive_labor_income_t']:.2f}T,"
            f" capital ${context['positive_capital_income_t']:.2f}T)",
            flush=True,
        )
        print(
            f"  wages above the SS cap: "
            f"{context['share_of_wages_above_cap']:.1%} of wage income,"
            f" {context['share_of_workers_above_cap']:.1%} of workers",
            flush=True,
        )
        print("\nScenario grid:", flush=True)

    rows = [
        _run_one(
            scenario,
            baseline_revenue,
            baseline_states,
            microsim_factory,
            year,
            capital_income_vars,
            verbose,
            checkpoint_path=checkpoint_path,
            checkpoint=checkpoint,
            checkpoint_fingerprint=checkpoint_fingerprint,
            checkpoint_key=f"grid:{scenario.label}",
        )
        for scenario in scenarios
    ]

    sensitivities = {}

    if realization_sweep:
        if verbose:
            print("\nRealization sweep (Rapid / proportional):", flush=True)
        sensitivities["realization"] = [
            _run_one(
                build_scenario(
                    "Rapid", inequality="proportional", realization_rate=rate
                ),
                baseline_revenue,
                baseline_states,
                microsim_factory,
                year,
                capital_income_vars,
                verbose,
                checkpoint_path=checkpoint_path,
                checkpoint=checkpoint,
                checkpoint_fingerprint=checkpoint_fingerprint,
                checkpoint_key=f"realization:{rate}",
            )
            for rate in realization_sweep
        ]

    if include_capital_scope_sensitivity:
        if verbose:
            print("\nCapital scope sensitivity (retirement excluded):", flush=True)
        sensitivities["capital_scope_excluding_retirement"] = [
            _run_one(
                build_scenario(name, inequality="proportional"),
                baseline_revenue,
                baseline_states,
                microsim_factory,
                year,
                CAPITAL_INCOME_VARS_EXCL_RETIREMENT,
                verbose,
                checkpoint_path=checkpoint_path,
                checkpoint=checkpoint,
                checkpoint_fingerprint=checkpoint_fingerprint,
                checkpoint_key=f"capital_scope:{name}",
            )
            for name in ("Slow", "Moderate", "Rapid")
        ]

    return {
        "year": year,
        "metadata": metadata,
        "baseline": baseline_row,
        "scenarios": rows,
        "sensitivities": sensitivities,
    }


def summary_table(result):
    """Return printable rows: label, revenue, payroll, poverty, Gini."""
    header = (
        f"{'scenario':38s} {'revenue $B':>11s} {'payroll $B':>11s} "
        f"{'poverty':>8s} {'net Gini':>9s}"
    )
    lines = [header, "-" * len(header)]
    baseline = result["baseline"]
    lines.append(
        f"{'Baseline':38s} {'--':>11s} {'--':>11s} "
        f"{baseline['spm_poverty_rate']:>7.2%} {baseline['net_gini']:>9.4f}"
    )
    for row in result["scenarios"]:
        lines.append(
            f"{row['scenario']['label']:38s} "
            f"{row['total_rev_change_b']:>+11,.1f} "
            f"{row['payroll_change_b']:>+11,.1f} "
            f"{row['spm_poverty_rate']:>7.2%} "
            f"{row['net_gini']:>9.4f}"
        )
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output",
        default=OUTPUT_PATH,
        help="Full run output (default: the committed analysis/outputs file).",
    )
    parser.add_argument(
        "--website-output",
        default=WEBSITE_OUTPUT_PATH,
        help="Site payload path (default: the checked-in src/data file).",
    )
    parser.add_argument(
        "--no-website",
        action="store_true",
        help="Do not write the site payload, e.g. for a comparison run.",
    )
    parser.add_argument(
        "--checkpoint",
        default=CHECKPOINT_PATH,
        help="Resume store; 'none' disables resuming.",
    )
    args = parser.parse_args(argv)
    checkpoint_path = None if args.checkpoint == "none" else args.checkpoint

    print("=" * 78)
    print("AI SCENARIOS (Budget Lab calibration, PolicyEngine-US)")
    print("=" * 78)

    result = run_ai_scenarios(verbose=True, checkpoint_path=checkpoint_path)

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(args.output, "w") as handle:
        json.dump(result, handle, indent=2, default=float)
    print(f"\nSaved to {args.output}")

    if not args.no_website:
        website_dir = os.path.dirname(args.website_output)
        if website_dir:
            os.makedirs(website_dir, exist_ok=True)
        with open(args.website_output, "w") as handle:
            json.dump(
                ai_scenarios_website_payload(result), handle, indent=2, default=float
            )
        print(f"Saved website payload to {args.website_output}")

    print()
    for line in summary_table(result):
        print(line)

    print(f"\n{result['metadata']['corporate_tax_scope_note']}")


if __name__ == "__main__":
    main()
