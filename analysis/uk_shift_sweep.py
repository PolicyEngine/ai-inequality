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
    "Positive employment and self-employment income fall by the selected "
    "share, and the same weighted total goes to positive capital income: "
    "savings and ISA interest, dividends, property income and capital gains. "
    "We scale every positive amount by one common factor, so each person "
    "gains in proportion to the capital income they already receive, and "
    "losses stay as they are. We simulate current law with no behavioural "
    "responses."
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
    """Non-overlapping revenue/transfer aggregates for UK.

    Split NI into employee+SE vs employer so the decomposition has a
    clean analog of US `household_tax_before_refundable_credits`
    (personal-side taxes that reduce household net income) plus
    employer-side payroll (government revenue that doesn't come out of
    household net income). `capital_gains_tax` is reported separately
    but folded into the personal tax aggregate for the identity check.
    """
    return {
        "income_tax": float(sim.calculate("income_tax", period=YEAR).sum()),
        "capital_gains_tax": float(
            sim.calculate("capital_gains_tax", period=YEAR).sum()
        ),
        "national_insurance": float(
            sim.calculate("national_insurance", period=YEAR).sum()
        ),
        "ni_class_1_employer": float(
            sim.calculate("ni_class_1_employer", period=YEAR).sum()
        ),
        "household_benefits": float(
            sim.calculate("household_benefits", period=YEAR).sum()
        ),
        "household_market_income": float(
            sim.calculate("household_market_income", period=YEAR).sum()
        ),
        "household_net_income": float(
            sim.calculate("household_net_income", period=YEAR).sum()
        ),
    }


def net_fiscal_impact(components, baseline_components):
    delta = {
        f"{k}_change": components[k] - baseline_components[k] for k in components
    }
    # Government net revenue change = personal taxes + employer NI - benefits.
    personal_tax_change = (
        delta["income_tax_change"]
        + delta["capital_gains_tax_change"]
        + delta["national_insurance_change"]
    )
    total = (
        personal_tax_change
        + delta["ni_class_1_employer_change"]
        - delta["household_benefits_change"]
    )
    delta["total_change"] = total
    delta["personal_tax_change"] = personal_tax_change
    delta["total_national_insurance_change"] = (
        delta["national_insurance_change"] + delta["ni_class_1_employer_change"]
    )
    # Household-side identity: market - net = Δ(personal_tax) - Δ(benefits),
    # approximately. Residual captures other taxes (council tax, duties, etc.)
    # that UK household_tax sums but our three-bucket view doesn't show.
    market_minus_net_change = (
        delta["household_market_income_change"]
        - delta["household_net_income_change"]
    )
    delta["_identity_residual"] = (
        market_minus_net_change
        - (personal_tax_change - delta["household_benefits_change"])
    )
    return delta


UK_MTR_SOURCES = [
    ("employment_income", "Employment"),
    ("self_employment_income", "Self-employment"),
    ("dividend_income", "Dividends"),
    ("savings_interest_income", "Savings interest"),
    ("property_income", "Property"),
    ("capital_gains", "Capital gains"),
]

UK_MTR_TAX_TARGETS = [
    # UK's income_tax does not include capital_gains_tax, so include CGT in
    # both targets — otherwise the MTR on capital gains is 0 and labor-side
    # comparison is misleading. Shared keys match the US sweep so the UI
    # reads one metric name across both countries.
    ("fed_income_tax", ["income_tax", "capital_gains_tax"]),
    (
        "fed_income_plus_payroll_tax",
        ["income_tax", "capital_gains_tax", "total_national_insurance"],
    ),
]

MTR_DELTA_PCT = 0.01


def _uk_mtrs(sim, branch_prefix="mtr"):
    """Dollar-weighted UK income tax and income+NI MTRs by income source."""
    try:
        branches = {}
        positive_totals = {}
        labels = {}
        for source_var, source_label in UK_MTR_SOURCES:
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
            for key, variables in UK_MTR_TAX_TARGETS
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
            for key, variables in UK_MTR_TAX_TARGETS:
                bumped_total = _sum_vars(branch, variables)
                delta_tax = bumped_total - base_totals[key]
                row[f"{key}_mtr"] = (
                    delta_tax / delta_gross if delta_gross else None
                )
            rows.append(row)
        return rows
    except Exception as exc:  # noqa: BLE001
        import traceback

        print(f"  _uk_mtrs failed: {exc}", flush=True)
        traceback.print_exc()
        return []


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
            "Net government revenue change = taxes (Income Tax, Capital Gains "
            "Tax, and workers' and employers' National Insurance) minus "
            "household benefits."
        ),
        "revenue_summary_note": (
            "We estimate Income Tax and Capital Gains Tax receipts, taken "
            "together, climb at the top of the sweep, while National Insurance "
            "receipts keep falling and household benefits keep rising."
        ),
        "baseline_facts": _baseline_facts(baseline, baseline_metrics),
    }


def _scenario_row(
    shift_pct,
    label,
    metrics,
    fiscal_delta=None,
    fiscal=None,
    mtrs=None,
):
    """Emit a scenario row using the shared US-parity schema.

    The UI chart components read shared keys like
    fed_income_tax_before_refundable_credits_change_b, so UK maps its
    concepts to those names: UK's income_tax goes on the income-tax
    line (no refundable-credit concept), NI fills the payroll bucket,
    and benefits go on the benefits line. Keeps legacy UK-specific
    fields populated for any older consumers.
    """
    if fiscal_delta is None:
        fiscal_delta = {
            "total_change": 0.0,
            "income_tax_change": 0.0,
            "capital_gains_tax_change": 0.0,
            "national_insurance_change": 0.0,
            "ni_class_1_employer_change": 0.0,
            "total_national_insurance_change": 0.0,
            "personal_tax_change": 0.0,
            "household_benefits_change": 0.0,
            "_identity_residual": 0.0,
            "household_market_income_change": 0.0,
            "household_net_income_change": 0.0,
        }
    if fiscal is None:
        fiscal = {
            "income_tax": 0.0,
            "capital_gains_tax": 0.0,
            "national_insurance": 0.0,
            "ni_class_1_employer": 0.0,
        }

    income_tax_change_b = _currency_billions(
        fiscal_delta["income_tax_change"]
        + fiscal_delta.get("capital_gains_tax_change", 0.0)
    )
    ni_ee_se_change_b = _currency_billions(
        fiscal_delta["national_insurance_change"]
    )
    ni_er_change_b = _currency_billions(
        fiscal_delta.get("ni_class_1_employer_change", 0.0)
    )
    ni_change_b = ni_ee_se_change_b + ni_er_change_b
    benefits_change_b = _currency_billions(
        fiscal_delta["household_benefits_change"]
    )
    total_change_b = _currency_billions(fiscal_delta["total_change"])

    return {
        "shift_pct": shift_pct,
        "label": label,
        "net_gini": metrics["net_gini"],
        "net_gini_including_health_benefits": metrics["net_gini"],
        "market_gini": metrics["market_gini"],
        "net_top_10_share": metrics["top_10_share"],
        "net_top_1_share": metrics["top_1_share"],
        "net_top_0_1_share": metrics["top_0_1_share"],
        "market_top_10_share": metrics["market_top_10_share"],
        "market_top_1_share": metrics["market_top_1_share"],
        "market_top_0_1_share": metrics["market_top_0_1_share"],
        "spm_poverty_rate": metrics.get("poverty_rate", 0.0),
        "fed_revenue_b": _currency_billions(
            fiscal.get("income_tax", 0.0)
            + fiscal.get("capital_gains_tax", 0.0)
            + fiscal.get("national_insurance", 0.0)
            + fiscal.get("ni_class_1_employer", 0.0)
        ),
        # Shared-schema fiscal fields consumed by the UI. UK maps:
        # income_tax_before_refundable_credits ← income_tax + CGT;
        # employer_payroll ← ni_class_1_employer;
        # employee_ss_tax ← national_insurance (employee + SE portion).
        "total_rev_change_b": total_change_b,
        "revenue_change_b": total_change_b,
        "household_tax_change_b": income_tax_change_b + ni_ee_se_change_b,
        "refundable_credits_change_b": 0.0,
        "state_refundable_credits_change_b": 0.0,
        "state_tax_before_refundable_credits_change_b": 0.0,
        "state_benefits_change_b": 0.0,
        "benefits_change_b": benefits_change_b,
        "fed_income_tax_before_refundable_credits_change_b": income_tax_change_b,
        "fed_main_rates_change_b": income_tax_change_b,
        "fed_capital_gains_tax_change_b": 0.0,
        "fed_amt_change_b": 0.0,
        "fed_niit_change_b": 0.0,
        "fed_nonrefundable_credits_change_b": 0.0,
        "fed_other_income_tax_items_change_b": 0.0,
        "employer_payroll_change_b": ni_er_change_b,
        "employee_ss_tax_change_b": ni_ee_se_change_b,
        "employee_medicare_tax_change_b": 0.0,
        "self_employment_tax_change_b": 0.0,
        "identity_residual_b": _currency_billions(
            fiscal_delta.get("_identity_residual", 0.0)
        ),
        "state_deltas": {},
        "federal_mtrs": mtrs or [],
        # Legacy UK-specific fields kept for back-compat.
        "gov_revenue_b": _currency_billions(
            fiscal.get("income_tax", 0.0)
            + fiscal.get("capital_gains_tax", 0.0)
            + fiscal.get("national_insurance", 0.0)
            + fiscal.get("ni_class_1_employer", 0.0)
        ),
        "income_tax_change_b": income_tax_change_b,
        "national_insurance_change_b": ni_change_b,
    }


def _uk_national_baseline_totals(sim):
    income_tax_plus_cgt = float(
        sim.calculate("income_tax", period=YEAR).sum()
    ) + float(sim.calculate("capital_gains_tax", period=YEAR).sum())
    ni_ee_se = float(sim.calculate("national_insurance", period=YEAR).sum())
    ni_er = float(sim.calculate("ni_class_1_employer", period=YEAR).sum())
    return {
        "fed_income_tax": income_tax_plus_cgt,
        "fed_income_tax_before_refundable_credits": income_tax_plus_cgt,
        "household_tax_before_refundable_credits": income_tax_plus_cgt + ni_ee_se,
        "household_refundable_tax_credits": 0.0,
        "household_benefits": float(
            sim.calculate("household_benefits", period=YEAR).sum()
        ),
        "employer_payroll_tax": ni_er,
        "employee_social_security_tax": ni_ee_se,
        "employee_medicare_tax": 0.0,
        "self_employment_tax": 0.0,
        "state_tax_before_refundable_credits": 0.0,
        "state_refundable_credits": 0.0,
        "state_benefits": 0.0,
    }


def _uk_decile_impacts(baseline_sim, scenario_sims):
    """Per-decile mean net income change by baseline market-income decile.

    baseline_sim: the baseline Microsimulation (already loaded).
    scenario_sims: dict of {shift_pct: branched_sim} for the computed shifts.
    """
    weights = np.asarray(
        baseline_sim.calculate("household_weight", period=YEAR), dtype=float
    )
    market = np.asarray(
        baseline_sim.calculate("household_market_income", period=YEAR),
        dtype=float,
    )
    net_base = np.asarray(
        baseline_sim.calculate("household_net_income", period=YEAR), dtype=float
    )

    sorted_idx = np.argsort(market)
    sorted_weights = weights[sorted_idx]
    cum = np.cumsum(sorted_weights)
    total = cum[-1]
    edges = [np.searchsorted(cum, total * i / 10) for i in range(1, 10)]
    decile_of_sorted = np.digitize(
        np.arange(len(sorted_idx)), edges, right=False
    ) + 1
    decile_labels = np.zeros_like(market, dtype=int)
    decile_labels[sorted_idx] = decile_of_sorted

    def _decile_stats(net_values):
        rows = []
        for d in range(1, 11):
            mask = decile_labels == d
            w = weights[mask].sum()
            total_net = (net_values[mask] * weights[mask]).sum()
            mean_net = total_net / w if w > 0 else float("nan")
            rows.append({"decile": d, "weight": float(w), "mean_net": float(mean_net)})
        return rows

    baseline_stats = _decile_stats(net_base)
    baseline_mean = {r["decile"]: r["mean_net"] for r in baseline_stats}

    scenarios = [{"shift_pct": 0, "deciles": [
        {**s, "baseline_mean_net": s["mean_net"], "delta_mean_net": 0.0,
         "pct_change": 0.0}
        for s in baseline_stats
    ]}]
    for pct, sim in sorted(scenario_sims.items()):
        net = np.asarray(
            sim.calculate("household_net_income", period=YEAR), dtype=float
        )
        stats = _decile_stats(net)
        for s in stats:
            s["baseline_mean_net"] = baseline_mean[s["decile"]]
            s["delta_mean_net"] = s["mean_net"] - baseline_mean[s["decile"]]
            s["pct_change"] = (
                (s["mean_net"] / baseline_mean[s["decile"]] - 1) * 100
                if baseline_mean[s["decile"]] > 0
                else None
            )
        scenarios.append({"shift_pct": int(pct * 100), "deciles": stats})

    return {
        "baseline_mean_net_by_decile": baseline_stats,
        "scenarios": scenarios,
        "methodology": (
            "Households bucketed into deciles by baseline weighted market "
            "income; decile membership held fixed across scenarios."
        ),
    }


def run_shift_sweep(
    shift_levels=None,
    microsim_factory=managed_uk_microsimulation,
    verbose=False,
):
    if shift_levels is None:
        shift_levels = SHIFT_LEVELS

    baseline = microsim_factory()
    if verbose:
        print("Computing UK baseline...")
    # PE-UK does not propagate sub-branch inputs correctly when the parent
    # branch already overrides the same variables. This makes per-scenario
    # MTR computation on shifted UK branches produce nonsense (−22 000% on
    # self-employment at 50% shift, etc.), so UK MTR computation is
    # disabled across the board — the chart hides when no scenario has
    # populated federal_mtrs. US is unaffected.
    baseline_mtrs = []
    baseline_metrics = _extract_results(baseline, "Baseline")
    baseline_fiscal = revenue_components(baseline)
    baseline_totals = {"national": _uk_national_baseline_totals(baseline)}
    metadata = _metadata(baseline, baseline_metrics)
    metadata["baseline_facts"]["totals"] = baseline_totals

    scenarios = [
        _scenario_row(
            0,
            "Baseline",
            baseline_metrics,
            fiscal_delta=None,
            fiscal=baseline_fiscal,
            mtrs=baseline_mtrs,
        )
    ]

    scenario_sims = {}

    for pct in shift_levels:
        if pct == 0:
            continue

        label = f"{int(pct * 100)}% shift"
        if verbose:
            print(f"Computing UK {label}...")

        sim = microsim_factory()
        branch, _ = _apply_shift(sim, f"uk_sweep_{int(pct * 100)}", pct)
        # MTRs disabled for UK; see comment on baseline_mtrs above.
        scenario_mtrs = []
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
                mtrs=scenario_mtrs,
            )
        )
        scenario_sims[pct] = branch

    if verbose:
        print("Computing UK decile impacts...")
    metadata["baseline_facts"]["decile_impacts"] = _uk_decile_impacts(
        baseline, scenario_sims
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
