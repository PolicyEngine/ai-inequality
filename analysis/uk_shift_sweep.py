"""UK sensitivity sweep of labour-to-capital income shifts."""

from __future__ import annotations

import json
import os
from importlib.metadata import PackageNotFoundError, version

import numpy as np

from .metrics import compute_top_shares
from .policyengine_runtime import managed_uk_microsimulation, policyengine_bundle

YEAR = 2026
SHIFT_LEVELS = [pct / 100 for pct in range(0, 101, 10)]
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "data",
    "ukShiftSweepData.json",
)
MODEL_URL = "https://www.policyengine.org/uk/model"
UK_DEFAULT_DATASET_URL = "hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5"
LABOR_INCOME_VARS = ("employment_income", "self_employment_income")
CAPITAL_INCOME_VARS = (
    "savings_interest_income",
    "individual_savings_account_interest_income",
    "dividend_income",
    "property_income",
    "capital_gains",
)

SHIFT_SWEEP_DESCRIPTION = (
    "Positive employment and self-employment income are reduced by the selected "
    "share, and the same weighted total is redistributed to positive capital "
    "income in proportion to existing UK capital-income holdings. This is a "
    "static current-law microsimulation; it is not a behavioural forecast."
)


def _package_version(package_name):
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None


def _currency_billions(amount):
    return amount / 1e9


def _weighted_top_share_by_rank(values, weights, rank_values, top_fraction):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    rank_values = np.asarray(rank_values, dtype=float)

    idx = np.argsort(rank_values)
    values, weights = values[idx], weights[idx]
    total_weight = float(weights.sum())
    total_value = float((values * weights).sum())
    if total_weight <= 0 or total_value == 0:
        return 0.0

    cutoff = (1 - top_fraction) * total_weight
    lower = np.concatenate([[0.0], np.cumsum(weights[:-1])])
    upper = lower + weights
    overlap = np.maximum(0, upper - np.maximum(lower, cutoff))
    top_value = float((values * overlap).sum())
    return top_value / total_value


def _positive_household_sum(sim, variables):
    household_values = None
    for variable in variables:
        values = np.asarray(
            sim.calculate(variable, period=YEAR, map_to="household"),
            dtype=float,
        )
        positive_values = np.where(values > 0, values, 0)
        household_values = (
            positive_values
            if household_values is None
            else household_values + positive_values
        )
    return household_values


def _baseline_facts(sim, baseline_metrics):
    household_weight = np.asarray(
        sim.calculate("household_weight", period=YEAR),
        dtype=float,
    )
    market_income = np.asarray(
        sim.calculate("household_market_income", period=YEAR),
        dtype=float,
    )
    positive_labor_income = 0.0
    for variable in LABOR_INCOME_VARS:
        values = sim.calculate(variable, period=YEAR)
        raw = np.asarray(values, dtype=float)
        weights = np.asarray(values.weights, dtype=float)
        positive_labor_income += float((np.where(raw > 0, raw, 0) * weights).sum())

    positive_capital_income = 0.0
    for variable in CAPITAL_INCOME_VARS:
        values = sim.calculate(variable, period=YEAR)
        raw = np.asarray(values, dtype=float)
        weights = np.asarray(values.weights, dtype=float)
        positive_capital_income += float(
            (np.where(raw > 0, raw, 0) * weights).sum()
        )

    household_positive_capital = _positive_household_sum(sim, CAPITAL_INCOME_VARS)
    households_with_positive_capital = (
        float(household_weight[household_positive_capital > 0].sum())
        / float(household_weight.sum())
    )

    return {
        "labor_income_t": positive_labor_income / 1e12,
        "positive_labor_income_t": positive_labor_income / 1e12,
        "positive_capital_income_t": positive_capital_income / 1e12,
        "households_with_positive_capital_income_share": (
            households_with_positive_capital
        ),
        "positive_capital_top_10_share": _weighted_top_share_by_rank(
            household_positive_capital,
            household_weight,
            market_income,
            0.10,
        ),
        "positive_capital_top_1_share": _weighted_top_share_by_rank(
            household_positive_capital,
            household_weight,
            market_income,
            0.01,
        ),
        "positive_capital_top_0_1_share": _weighted_top_share_by_rank(
            household_positive_capital,
            household_weight,
            market_income,
            0.001,
        ),
        "market_top_10_share": baseline_metrics["market_top_10_share"],
        "market_top_1_share": baseline_metrics["market_top_1_share"],
        "market_top_0_1_share": baseline_metrics["market_top_0_1_share"],
        "net_top_10_share": baseline_metrics["top_10_share"],
        "net_top_1_share": baseline_metrics["top_1_share"],
        "net_top_0_1_share": baseline_metrics["top_0_1_share"],
    }


def revenue_components(sim):
    income_tax = float(sim.calculate("income_tax", period=YEAR).sum())
    national_insurance = float(
        sim.calculate("total_national_insurance", period=YEAR).sum()
    )
    household_benefits = float(sim.calculate("household_benefits", period=YEAR).sum())
    return {
        "income_tax": income_tax,
        "national_insurance": national_insurance,
        "household_benefits": household_benefits,
    }


def net_fiscal_impact(components, baseline_components):
    delta_income_tax = components["income_tax"] - baseline_components["income_tax"]
    delta_national_insurance = (
        components["national_insurance"] - baseline_components["national_insurance"]
    )
    delta_benefits = -(
        components["household_benefits"]
        - baseline_components["household_benefits"]
    )
    total = delta_income_tax + delta_national_insurance + delta_benefits
    return {
        "income_tax_change": delta_income_tax,
        "national_insurance_change": delta_national_insurance,
        "benefits_change": delta_benefits,
        "total_change": total,
    }


def _extract_results(sim, label):
    net_income = sim.calculate("household_net_income", period=YEAR)
    market_income = sim.calculate("household_market_income", period=YEAR)
    market_top_shares = compute_top_shares(
        np.asarray(market_income, dtype=float),
        np.asarray(market_income.weights, dtype=float),
    )
    net_top_shares = compute_top_shares(
        np.asarray(net_income, dtype=float),
        np.asarray(net_income.weights, dtype=float),
    )

    return {
        "label": label,
        "mean_net_income": float(net_income.mean()),
        "mean_market_income": float(market_income.mean()),
        "market_gini": float(market_income.gini()),
        "net_gini": float(net_income.gini()),
        "market_top_10_share": market_top_shares[0.10],
        "market_top_1_share": market_top_shares[0.01],
        "market_top_0_1_share": market_top_shares[0.001],
        "top_10_share": net_top_shares[0.10],
        "top_1_share": net_top_shares[0.01],
        "top_0_1_share": net_top_shares[0.001],
    }


def _apply_shift(baseline, branch_name, shift_pct):
    branch = baseline.get_branch(branch_name)

    total_freed = 0.0
    for variable in LABOR_INCOME_VARS:
        values = baseline.calculate(variable, period=YEAR)
        raw = np.asarray(values, dtype=float)
        weights = np.asarray(values.weights, dtype=float)
        reduction = np.where(raw > 0, raw * shift_pct, 0)
        branch.set_input(variable, YEAR, raw - reduction)
        total_freed += float((reduction * weights).sum())

    capital_positive_totals = {}
    for variable in CAPITAL_INCOME_VARS:
        values = baseline.calculate(variable, period=YEAR)
        raw = np.asarray(values, dtype=float)
        weights = np.asarray(values.weights, dtype=float)
        capital_positive_totals[variable] = float(
            (np.where(raw > 0, raw, 0) * weights).sum()
        )

    total_positive_capital = sum(capital_positive_totals.values())
    if total_positive_capital <= 0:
        return branch, total_freed

    for variable in CAPITAL_INCOME_VARS:
        original = baseline.calculate(variable, period=YEAR)
        positive_total = capital_positive_totals[variable]
        if positive_total <= 0:
            continue
        share = positive_total / total_positive_capital
        scale = 1 + (share * total_freed) / positive_total
        raw = np.asarray(original, dtype=float)
        branch.set_input(variable, YEAR, np.where(raw > 0, raw * scale, raw))

    return branch, total_freed


def _metadata(baseline, baseline_metrics):
    bundle = policyengine_bundle(baseline)
    return {
        "country_id": "uk",
        "country_label": "United Kingdom",
        "year": YEAR,
        "description": SHIFT_SWEEP_DESCRIPTION,
        "model_url": MODEL_URL,
        "currency_symbol": "£",
        "labor_label": "labour",
        "labor_title": "Labour",
        "policyengine_package": "policyengine",
        "policyengine_version": (
            bundle.get("policyengine_version")
            or _package_version("policyengine")
            or _package_version("policyengine-core")
            or "unknown"
        ),
        "country_model_package": bundle.get("model_package") or "policyengine-uk",
        "country_model_version": (
            bundle.get("model_version")
            or _package_version("policyengine-uk")
            or "unknown"
        ),
        "policyengine_uk_version": (
            bundle.get("model_version")
            or _package_version("policyengine-uk")
            or "unknown"
        ),
        "data_package": bundle.get("data_package"),
        "data_version": bundle.get("data_version"),
        "dataset_name": (
            bundle.get("runtime_dataset")
            or getattr(getattr(baseline, "dataset", None), "name", None)
        ),
        "dataset_uri": bundle.get("runtime_dataset_uri"),
        "policyengine_bundle": bundle or None,
        "revenue_label": "Net government revenue change",
        "revenue_description": (
            "UK government effect including Income Tax, National Insurance, "
            "and modelled household benefit changes."
        ),
        "revenue_summary_note": (
            "Includes Income Tax and National Insurance receipts net of modelled "
            "household benefit costs."
        ),
        "baseline_facts": _baseline_facts(baseline, baseline_metrics),
    }


def _scenario_row(shift_pct, label, metrics, fiscal_delta=None, fiscal=None):
    if fiscal_delta is None:
        fiscal_delta = {
            "total_change": 0.0,
            "income_tax_change": 0.0,
            "national_insurance_change": 0.0,
            "benefits_change": 0.0,
        }
    if fiscal is None:
        fiscal = {"income_tax": 0.0, "national_insurance": 0.0}

    return {
        "shift_pct": shift_pct,
        "label": label,
        "net_gini": metrics["net_gini"],
        "market_gini": metrics["market_gini"],
        "net_top_10_share": metrics["top_10_share"],
        "net_top_1_share": metrics["top_1_share"],
        "net_top_0_1_share": metrics["top_0_1_share"],
        "market_top_10_share": metrics["market_top_10_share"],
        "market_top_1_share": metrics["market_top_1_share"],
        "market_top_0_1_share": metrics["market_top_0_1_share"],
        "gov_revenue_b": _currency_billions(
            fiscal.get("income_tax", 0.0) + fiscal.get("national_insurance", 0.0)
        ),
        "revenue_change_b": _currency_billions(fiscal_delta["total_change"]),
        "income_tax_change_b": _currency_billions(
            fiscal_delta["income_tax_change"]
        ),
        "national_insurance_change_b": _currency_billions(
            fiscal_delta["national_insurance_change"]
        ),
        "benefits_change_b": _currency_billions(fiscal_delta["benefits_change"]),
    }


def run_shift_sweep(
    shift_levels=None,
    microsim_factory=managed_uk_microsimulation,
    verbose=False,
):
    if shift_levels is None:
        shift_levels = SHIFT_LEVELS

    baseline = microsim_factory()
    baseline_metrics = _extract_results(baseline, "Baseline")
    baseline_fiscal = revenue_components(baseline)
    metadata = _metadata(baseline, baseline_metrics)

    scenarios = [
        _scenario_row(
            0,
            "Baseline",
            baseline_metrics,
            fiscal_delta=None,
            fiscal=baseline_fiscal,
        )
    ]

    for pct in shift_levels:
        if pct == 0:
            continue

        label = f"{int(pct * 100)}% shift"
        if verbose:
            print(f"Computing UK {label}...")

        sim = microsim_factory()
        branch, _ = _apply_shift(sim, f"uk_sweep_{int(pct * 100)}", pct)
        metrics = _extract_results(branch, label)
        fiscal = revenue_components(branch)
        fiscal_delta = net_fiscal_impact(fiscal, baseline_fiscal)
        scenarios.append(
            _scenario_row(
                int(pct * 100),
                label,
                metrics,
                fiscal_delta=fiscal_delta,
                fiscal=fiscal,
            )
        )

    return {"year": YEAR, "metadata": metadata, "scenarios": scenarios}


def main():
    result = run_shift_sweep(verbose=True)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
