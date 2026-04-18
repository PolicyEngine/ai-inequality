"""Sensitivity sweep of labor→capital shift at multiple magnitudes.

Runs the shift at 0%, 10%, 20%, ..., 100% and records:
  - Net income Gini and market Gini
  - SPM poverty rate
  - Revenue decomposition: income tax, payroll, EITC, CTC, SNAP
"""

import gc
import json
import os
from importlib.metadata import PackageNotFoundError, version

import numpy as np

from .constants import CAPITAL_INCOME_VARS, YEAR
from .fiscal import (
    net_fiscal_impact,
    revenue_components,
    state_revenue_components,
)
from .labor_capital_shift import _apply_shift
from .metrics import extract_results as _extract_results
from .microdata_export import (
    write_microdata_manifest,
    write_scenario_household_microdata,
)
from .policyengine_runtime import managed_us_microsimulation, policyengine_bundle

SHIFT_LEVELS = [pct / 100 for pct in range(0, 101, 10)]

# Fiscal fields attached to each scenario row. The bucket names are the
# storytelling primitives for the website chart and the EA Forum post.
_FISCAL_FIELDS = [
    ("total_rev_change_b", "total_change"),
    # Non-overlapping top-line aggregates.
    ("household_tax_change_b", "household_tax_before_refundable_credits_change"),
    ("refundable_credits_change_b", "household_refundable_tax_credits_change"),
    ("benefits_change_b", "household_benefits_change"),
    ("employer_payroll_change_b", "employer_payroll_tax_change"),
    # Federal income-tax attribution (already inside household_tax_before...).
    ("fed_income_tax_before_refundable_credits_change_b",
     "fed_income_tax_before_refundable_credits_change"),
    ("fed_main_rates_change_b", "fed_income_tax_main_rates_change"),
    ("fed_capital_gains_tax_change_b", "fed_capital_gains_tax_change"),
    ("fed_amt_change_b", "fed_alternative_minimum_tax_change"),
    ("fed_niit_change_b", "fed_net_investment_income_tax_change"),
    ("fed_nonrefundable_credits_change_b", "fed_nonrefundable_credits_change"),
    ("fed_other_income_tax_items_change_b", "fed_other_income_tax_items_change"),
    # Payroll / self-employment (already inside household_tax_before...).
    ("employee_ss_tax_change_b", "employee_social_security_tax_change"),
    ("employee_medicare_tax_change_b", "employee_medicare_tax_change"),
    ("employer_ss_tax_change_b", "employer_social_security_tax_change"),
    ("employer_medicare_tax_change_b", "employer_medicare_tax_change"),
    ("self_employment_tax_change_b", "self_employment_tax_change"),
    # State (already inside household_tax_before... / refundable / benefits).
    ("state_tax_before_refundable_credits_change_b",
     "state_tax_before_refundable_credits_change"),
    ("state_refundable_credits_change_b", "state_refundable_credits_change"),
    ("state_benefits_change_b", "state_benefits_change"),
    # Federal refundable credit attribution.
    ("eitc_change_b", "eitc_change"),
    ("refundable_ctc_change_b", "refundable_ctc_change"),
    # Benefit attribution.
    ("snap_change_b", "snap_change"),
    ("ssi_change_b", "ssi_change"),
    ("tanf_change_b", "tanf_change"),
    ("wic_change_b", "wic_change"),
    ("health_benefits_change_b", "health_benefits_change"),
    # Identity diagnostics.
    ("market_income_change_b", "household_market_income_change"),
    ("net_income_change_b", "household_net_income_change"),
    ("identity_residual_b", "_identity_residual"),
]

# Legacy aliases preserved so downstream code/tests reading older keys still
# works. These all equal one of the new fields above.
_LEGACY_ALIASES = {
    # The website previously read "revenue_change_b"; keep it.
    "revenue_change_b": "total_rev_change_b",
    "income_tax_change_b": "fed_income_tax_before_refundable_credits_change_b",
}


def _fiscal_row(delta):
    row = {name: delta.get(key, 0.0) / 1e9 for name, key in _FISCAL_FIELDS}
    for alias, source in _LEGACY_ALIASES.items():
        row[alias] = row[source]
    return row


def _zero_fiscal_row():
    row = {name: 0.0 for name, _ in _FISCAL_FIELDS}
    for alias in _LEGACY_ALIASES:
        row[alias] = 0.0
    return row


def _state_delta_rows(scenario_states, baseline_states):
    """Return per-state delta dicts keyed by two-letter state code, in $B."""
    codes = set(scenario_states) | set(baseline_states)
    rows = {}
    for code in codes:
        scen = scenario_states.get(code, {})
        base = baseline_states.get(code, {})
        state_tax = (
            scen.get("household_state_tax_before_refundable_credits", 0.0)
            - base.get("household_state_tax_before_refundable_credits", 0.0)
        )
        state_credits = (
            scen.get("household_refundable_state_tax_credits", 0.0)
            - base.get("household_refundable_state_tax_credits", 0.0)
        )
        state_benefits = (
            scen.get("household_state_benefits", 0.0)
            - base.get("household_state_benefits", 0.0)
        )
        fed_tax_before = (
            scen.get("household_tax_before_refundable_credits", 0.0)
            - base.get("household_tax_before_refundable_credits", 0.0)
        )
        fed_refundable = (
            scen.get("household_refundable_tax_credits", 0.0)
            - base.get("household_refundable_tax_credits", 0.0)
        )
        hh_benefits = (
            scen.get("household_benefits", 0.0) - base.get("household_benefits", 0.0)
        )
        rows[code] = {
            "state_tax_before_refundable_credits_change_b": state_tax / 1e9,
            "state_refundable_credits_change_b": state_credits / 1e9,
            "state_benefits_change_b": state_benefits / 1e9,
            "state_net_change_b": (state_tax - state_credits - state_benefits) / 1e9,
            "household_tax_before_refundable_credits_change_b": fed_tax_before / 1e9,
            "household_refundable_tax_credits_change_b": fed_refundable / 1e9,
            "household_benefits_change_b": hh_benefits / 1e9,
            "eitc_change_b": (scen.get("eitc", 0.0) - base.get("eitc", 0.0)) / 1e9,
            "snap_change_b": (scen.get("snap", 0.0) - base.get("snap", 0.0)) / 1e9,
            "capital_gains_tax_change_b": (
                scen.get("capital_gains_tax", 0.0)
                - base.get("capital_gains_tax", 0.0)
            ) / 1e9,
            "amt_change_b": (
                scen.get("alternative_minimum_tax", 0.0)
                - base.get("alternative_minimum_tax", 0.0)
            ) / 1e9,
            "niit_change_b": (
                scen.get("net_investment_income_tax", 0.0)
                - base.get("net_investment_income_tax", 0.0)
            ) / 1e9,
            "household_weight": scen.get(
                "household_weight", base.get("household_weight", 0.0)
            ),
        }
    return rows

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "outputs", "shift_sweep.json")
MICRODATA_OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "outputs", "shift_sweep_microdata"
)
MODEL_URL = "https://www.policyengine.org/us/model"
SHIFT_SWEEP_DESCRIPTION = (
    "Positive employment and self-employment income are reduced by the selected "
    "share, and the same weighted total is redistributed to positive capital "
    "income in proportion to existing holdings. This is a static current-law "
    "microsimulation; it is not a behavioral forecast."
)


def _package_version(package_name):
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None


POLICYENGINE_PACKAGE = "policyengine"
POLICYENGINE_VERSION = (
    _package_version(POLICYENGINE_PACKAGE)
    or _package_version("policyengine-core")
    or "unknown"
)
POLICYENGINE_US_VERSION = _package_version("policyengine-us") or "unknown"


MTR_SOURCES = [
    ("employment_income", "Employment"),
    ("self_employment_income", "Self-employment"),
    ("long_term_capital_gains", "Long-term capital gains"),
    ("short_term_capital_gains", "Short-term capital gains"),
    ("qualified_dividend_income", "Qualified dividends"),
    ("non_qualified_dividend_income", "Ordinary dividends"),
    ("taxable_interest_income", "Taxable interest"),
    ("rental_income", "Rental income"),
]

MTR_TAX_TARGETS = [
    # (output_key, [PE variable(s) to sum]).
    ("fed_income_tax", ["income_tax"]),
    (
        "fed_income_tax_before_refundable_credits",
        ["income_tax_before_refundable_credits"],
    ),
    (
        "fed_income_plus_payroll_tax",
        [
            "income_tax",
            "employer_payroll_tax",
            "employee_social_security_tax",
            "employee_medicare_tax",
            "self_employment_tax",
        ],
    ),
]

MTR_DELTA_PCT = 0.01


def _federal_mtrs(sim, branch_prefix="mtr"):
    """Dollar-weighted federal income tax MTRs by income source.

    Each source is bumped by +1% of its (positive) values on a fresh
    sub-branch, then the change in federal income tax is divided by the
    weighted dollar change in the source to get a dollar-weighted MTR.
    `branch_prefix` lets the caller keep per-scenario branches from
    clashing.

    Branches must be created (with modified inputs) BEFORE any downstream
    variable is computed on the parent sim, otherwise PE's memoization
    propagates the parent value to child branches and all MTRs come out
    zero. Phases:
      1. Create all branches + set modified inputs
      2. Compute base totals on parent sim
      3. Compute bumped totals on each branch
    """
    try:
        branches = {}
        positive_totals = {}
        labels = {}
        for source_var, source_label in MTR_SOURCES:
            try:
                original = sim.calculate(source_var, period=YEAR)
            except Exception:
                continue
            raw = np.asarray(original, dtype=float)
            weights = np.asarray(original.weights, dtype=float)
            positive = np.where(raw > 0, raw, 0)
            positive_total = float((positive * weights).sum())
            if positive_total <= 0:
                continue

            branch_name = f"{branch_prefix}_{source_var}"[:48]
            branch = sim.get_branch(branch_name)
            branch.set_input(source_var, YEAR, raw + positive * MTR_DELTA_PCT)
            branches[source_var] = branch
            positive_totals[source_var] = positive_total
            labels[source_var] = source_label

        if not branches:
            return []

        def _sum_vars(source_sim, variables):
            return sum(
                float(
                    source_sim.calculate(
                        v, map_to="household", period=YEAR
                    ).sum()
                )
                for v in variables
            )

        base_totals = {
            key: _sum_vars(sim, variables)
            for key, variables in MTR_TAX_TARGETS
        }

        rows = []
        for source_var, branch in branches.items():
            positive_total = positive_totals[source_var]
            delta_gross = positive_total * MTR_DELTA_PCT
            row = {
                "source": source_var,
                "label": labels[source_var],
                "positive_total_t": positive_total / 1e12,
            }
            for key, variables in MTR_TAX_TARGETS:
                bumped_total = _sum_vars(branch, variables)
                delta_tax = bumped_total - base_totals[key]
                row[f"{key}_mtr"] = (
                    delta_tax / delta_gross if delta_gross else None
                )
            rows.append(row)
        return rows
    except Exception:
        return []


def _baseline_facts(sim):
    """Return high-level baseline totals used in the website explainer."""
    try:
        employment_income = sim.calculate("employment_income", period=YEAR)
        self_employment_income = sim.calculate(
            "self_employment_income", period=YEAR
        )
        employment_raw = np.asarray(employment_income, dtype=float)
        employment_weights = np.asarray(employment_income.weights, dtype=float)
        self_employment_raw = np.asarray(self_employment_income, dtype=float)
        self_employment_weights = np.asarray(
            self_employment_income.weights,
            dtype=float,
        )
        positive_labor_income = float(
            (np.where(employment_raw > 0, employment_raw, 0) * employment_weights).sum()
            + (
                np.where(self_employment_raw > 0, self_employment_raw, 0)
                * self_employment_weights
            ).sum()
        )

        positive_capital_income = 0.0
        for var in CAPITAL_INCOME_VARS:
            values = sim.calculate(var, period=YEAR)
            raw = np.asarray(values, dtype=float)
            weights = np.asarray(values.weights, dtype=float)
            positive_capital_income += float(
                (np.where(raw > 0, raw, 0) * weights).sum()
            )

        household_weight = np.asarray(
            sim.calculate("household_weight", period=YEAR), dtype=float
        )
        household_positive_capital = np.zeros_like(household_weight, dtype=float)
        for var in CAPITAL_INCOME_VARS:
            household_values = np.asarray(
                sim.calculate(var, period=YEAR, map_to="household"),
                dtype=float,
            )
            household_positive_capital += np.where(
                household_values > 0, household_values, 0
            )

        households_with_positive_capital_income_share = float(
            household_weight[household_positive_capital > 0].sum()
            / household_weight.sum()
        )

        return {
            "labor_income_t": positive_labor_income / 1e12,
            "positive_labor_income_t": positive_labor_income / 1e12,
            "positive_capital_income_t": positive_capital_income / 1e12,
            "households_with_positive_capital_income_share": (
                households_with_positive_capital_income_share
            ),
        }
    except Exception:
        return {}


def _metadata(baseline):
    bundle = policyengine_bundle(baseline)
    return {
        "year": YEAR,
        "description": SHIFT_SWEEP_DESCRIPTION,
        "model_url": MODEL_URL,
        "policyengine_package": POLICYENGINE_PACKAGE,
        "policyengine_version": (
            bundle.get("policyengine_version") or POLICYENGINE_VERSION
        ),
        "country_model_package": (
            bundle.get("model_package") or "policyengine-us"
        ),
        "country_model_version": (
            bundle.get("model_version") or POLICYENGINE_US_VERSION
        ),
        "policyengine_us_version": (
            bundle.get("model_version") or POLICYENGINE_US_VERSION
        ),
        "data_package": bundle.get("data_package"),
        "data_version": bundle.get("data_version"),
        "dataset_name": (
            bundle.get("runtime_dataset")
            or getattr(getattr(baseline, "dataset", None), "name", None)
        ),
        "dataset_uri": bundle.get("runtime_dataset_uri"),
        "policyengine_bundle": bundle or None,
        "baseline_facts": _baseline_facts(baseline),
    }


def run_shift_sweep(
    shift_levels=None,
    microsim_factory=managed_us_microsimulation,
    verbose=False,
    microdata_output_dir=MICRODATA_OUTPUT_DIR,
):
    """Run the labor→capital shift sweep and return website/export-ready rows.

    Each shift level is simulated from a fresh baseline microsimulation. This
    avoids retaining many live PolicyEngine branches in memory at once, which
    becomes expensive when sweeping the full 0–100% grid.
    """
    if shift_levels is None:
        shift_levels = SHIFT_LEVELS

    baseline = microsim_factory()
    if verbose:
        print("\nComputing baseline metrics...")
    # Compute MTRs FIRST on fresh sim — PE memoizes downstream variables
    # on the parent, and once they're cached the MTR sub-branches return
    # the parent value instead of recomputing against the bumped input.
    baseline_mtrs = _federal_mtrs(baseline, branch_prefix="mtr_base")
    base_metrics = _extract_results(baseline, "Baseline")
    base_rev = revenue_components(baseline)
    base_states = state_revenue_components(baseline)
    metadata = _metadata(baseline)
    microdata_files = []
    if microdata_output_dir:
        if verbose:
            print(f"Writing baseline household microdata to {microdata_output_dir}...")
        microdata_files.append(
            write_scenario_household_microdata(
                baseline,
                microdata_output_dir,
                "Baseline",
                0,
            )
        )
    del baseline

    scenarios = []

    baseline_scenario = {
        "shift_pct": 0,
        "label": "Baseline",
        "net_gini": base_metrics["net_gini"],
        "net_gini_including_health_benefits": (
            base_metrics["net_gini_including_health_benefits"]
        ),
        "market_gini": base_metrics["market_gini"],
        "net_top_10_share": base_metrics["top_10_share"],
        "net_top_1_share": base_metrics["top_1_share"],
        "net_top_0_1_share": base_metrics["top_0_1_share"],
        "market_top_10_share": base_metrics["market_top_10_share"],
        "market_top_1_share": base_metrics["market_top_1_share"],
        "market_top_0_1_share": base_metrics["market_top_0_1_share"],
        "spm_poverty_rate": base_metrics["spm_poverty_rate"],
        "fed_revenue_b": base_metrics["fed_revenue"] / 1e9,
        "state_deltas": {},
        "federal_mtrs": baseline_mtrs,
    }
    baseline_scenario.update(_zero_fiscal_row())
    scenarios.append(baseline_scenario)

    for pct in shift_levels:
        if pct == 0.0:
            continue
        label = f"{int(pct * 100)}% shift"
        if verbose:
            print(f"\nComputing {label} metrics...")

        sim = microsim_factory()
        branch, _ = _apply_shift(sim, f"sweep_{int(pct * 100)}", pct)
        # Compute MTRs on a freshly-shifted branch before any downstream
        # metrics populate PE's memoization cache.
        scenario_mtrs = _federal_mtrs(
            branch, branch_prefix=f"mtr_{int(pct * 100)}"
        )
        metrics = _extract_results(branch, label)
        rev = revenue_components(branch)
        delta = net_fiscal_impact(rev, base_rev)
        scenario_states = state_revenue_components(branch)
        state_deltas = _state_delta_rows(scenario_states, base_states)
        if microdata_output_dir:
            if verbose:
                print(f"  Writing household microdata for {label}...")
            microdata_files.append(
                write_scenario_household_microdata(
                    branch,
                    microdata_output_dir,
                    label,
                    int(pct * 100),
                )
            )

        row = {
            "shift_pct": int(pct * 100),
            "label": label,
            "net_gini": metrics["net_gini"],
            "net_gini_including_health_benefits": (
                metrics["net_gini_including_health_benefits"]
            ),
            "market_gini": metrics["market_gini"],
            "net_top_10_share": metrics["top_10_share"],
            "net_top_1_share": metrics["top_1_share"],
            "net_top_0_1_share": metrics["top_0_1_share"],
            "market_top_10_share": metrics["market_top_10_share"],
            "market_top_1_share": metrics["market_top_1_share"],
            "market_top_0_1_share": metrics["market_top_0_1_share"],
            "spm_poverty_rate": metrics["spm_poverty_rate"],
            "fed_revenue_b": metrics["fed_revenue"] / 1e9,
            "state_deltas": state_deltas,
            "federal_mtrs": scenario_mtrs,
        }
        row.update(_fiscal_row(delta))
        scenarios.append(row)

        if verbose:
            print(f"  Net Gini: {metrics['net_gini']:.4f}  Market Gini: {metrics['market_gini']:.4f}")
            print(f"  Poverty: {metrics['spm_poverty_rate']:.2%}")
            print(f"  Revenue change: ${delta['total_change']/1e9:+.1f}B")
            print(f"  Identity residual: ${delta['_identity_residual']/1e9:+.2f}B")

        del branch
        del sim
        gc.collect()

    if microdata_output_dir:
        write_microdata_manifest(
            microdata_output_dir,
            metadata,
            microdata_files,
        )

    return {"year": YEAR, "metadata": metadata, "scenarios": scenarios}


def main():
    print("=" * 60)
    print("LABOR→CAPITAL SHIFT SWEEP")
    print("=" * 60)

    result = run_shift_sweep(verbose=True)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {OUTPUT_PATH}")

    # Print summary table
    print("\n" + "=" * 75)
    print(f"{'Shift':>7} {'Market Gini':>12} {'Net Gini':>10} {'Poverty':>9} {'Rev Chg':>10}")
    print("-" * 75)
    for s in result["scenarios"]:
        print(
            f"{s['shift_pct']:>6}%"
            f"  {s['market_gini']:.4f}"
            f"  {s['net_gini']:.4f}"
            f"  {s['spm_poverty_rate']:.2%}"
            f"  ${s['total_rev_change_b']:>+.1f}B"
        )


if __name__ == "__main__":
    main()
