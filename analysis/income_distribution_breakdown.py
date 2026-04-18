"""Baseline income composition by distribution group."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .constants import CAPITAL_INCOME_VARS, YEAR
from .policyengine_runtime import managed_us_microsimulation, policyengine_bundle

BASELINE_MICRODATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "outputs",
    "shift_sweep_microdata",
    "baseline.csv.gz",
)
MICRODATA_MANIFEST_PATH = os.path.join(
    os.path.dirname(__file__),
    "outputs",
    "shift_sweep_microdata",
    "manifest.json",
)
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "data",
    "incomeDistributionData.json",
)

REQUIRED_BASELINE_COLUMNS = [
    "household_weight",
    "household_market_income",
    "household_net_income",
    "employment_income",
    "self_employment_income",
    *CAPITAL_INCOME_VARS,
]

GROUP_EDGES = (
    (0.0, 0.1, "Bottom 10%"),
    (0.1, 0.2, "P10-20"),
    (0.2, 0.3, "P20-30"),
    (0.3, 0.4, "P30-40"),
    (0.4, 0.5, "P40-50"),
    (0.5, 0.6, "P50-60"),
    (0.6, 0.7, "P60-70"),
    (0.7, 0.8, "P70-80"),
    (0.8, 0.9, "P80-90"),
    (0.9, 0.99, "P90-99"),
    (0.99, 0.999, "P99-99.9"),
    (0.999, 1.0, "Top 0.1%"),
)

TOP_SHARE_CUTOFFS = (
    ("top10", "Top 10%", 0.1),
    ("top1", "Top 1%", 0.01),
    ("top01", "Top 0.1%", 0.001),
)

MARKET_COMPONENTS = (
    {
        "key": "labor",
        "label": "Labor income",
        "description": "Employment and self-employment income.",
        "color": "#2C7A7B",
    },
    {
        "key": "capital",
        "label": "Capital income",
        "description": (
            "Capital gains, taxable interest, dividends, and rental income."
        ),
        "color": "#DD6B20",
    },
    {
        "key": "otherMarket",
        "label": "Other market income",
        "description": (
            "Residual market income not in labor or the capital-income measure, "
            "mostly partnership/S-corp income, pensions, retirement distributions, "
            "farm income, and miscellaneous income."
        ),
        "color": "#718096",
    },
)

NET_COMPONENTS = (
    {
        "key": "market",
        "label": "Market income",
        "description": "PolicyEngine household market income.",
        "color": "#2C7A7B",
    },
    {
        "key": "benefits",
        "label": "Benefits",
        "description": "Cash and near-cash benefits included in household net income.",
        "color": "#68D391",
    },
    {
        "key": "refundableCredits",
        "label": "Refundable credits",
        "description": "Refundable federal and state tax credits.",
        "color": "#63B3ED",
    },
    {
        "key": "taxes",
        "label": "Taxes before credits",
        "description": "Payroll, income, flat, and state taxes before refundable credits.",
        "color": "#C53030",
    },
)


def _read_microdata_manifest(manifest_path):
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing microdata manifest at {path}. Run the shift sweep first."
        )

    with open(path) as f:
        manifest = json.load(f)

    baseline_entry = next(
        (
            scenario
            for scenario in manifest.get("scenarios", [])
            if scenario.get("shift_pct") == 0
        ),
        None,
    )
    if baseline_entry is None:
        raise ValueError("Microdata manifest does not include a baseline scenario.")

    return manifest, baseline_entry


def _validate_baseline_microdata(baseline, baseline_microdata_path, manifest, baseline_entry):
    expected_name = baseline_entry.get("filename")
    actual_name = Path(baseline_microdata_path).name
    if expected_name and expected_name != actual_name:
        raise ValueError(
            "Baseline microdata path does not match manifest baseline: "
            f"{actual_name} != {expected_name}."
        )

    missing_columns = sorted(set(REQUIRED_BASELINE_COLUMNS) - set(baseline.columns))
    if missing_columns:
        raise ValueError(
            "Baseline microdata is missing required columns: "
            + ", ".join(missing_columns)
        )

    missing_manifest_fields = sorted(
        set(REQUIRED_BASELINE_COLUMNS) - set(manifest.get("analysis_fields", []))
    )
    if missing_manifest_fields:
        raise ValueError(
            "Microdata manifest does not list required columns: "
            + ", ".join(missing_manifest_fields)
        )


def _source_metadata(manifest, baseline_entry, baseline_microdata_path):
    return {
        "year": manifest.get("year"),
        "dataset_name": manifest.get("dataset_name"),
        "dataset_uri": manifest.get("dataset_uri"),
        "policyengine_package": manifest.get("policyengine_package"),
        "policyengine_version": manifest.get("policyengine_version"),
        "country_model_package": manifest.get("country_model_package"),
        "country_model_version": manifest.get("country_model_version"),
        "policyengine_us_version": manifest.get("policyengine_us_version"),
        "data_package": manifest.get("data_package"),
        "data_version": manifest.get("data_version"),
        "policyengine_core_version": manifest.get("policyengine_core_version"),
        "policyengine_bundle": manifest.get("policyengine_bundle"),
        "microdata_created_at": manifest.get("created_at"),
        "baseline_microdata_file": baseline_entry.get("filename"),
        "baseline_microdata_path": str(Path(baseline_microdata_path)),
    }


def _instantiate_runtime_microsim(microsim_factory, manifest):
    dataset_name = manifest.get("dataset_name")
    if dataset_name is None:
        return microsim_factory()

    try:
        return microsim_factory(dataset=dataset_name)
    except TypeError:
        return microsim_factory()


def _validate_runtime_bundle(manifest, sim):
    expected_bundle = manifest.get("policyengine_bundle") or {}
    actual_bundle = policyengine_bundle(sim)

    if not expected_bundle or not actual_bundle:
        return

    comparisons = [
        ("policyengine_version", "PolicyEngine version"),
        ("model_version", "country model version"),
        ("data_version", "data package version"),
        ("runtime_dataset", "dataset name"),
        ("runtime_dataset_uri", "dataset URI"),
    ]
    mismatches = []
    for key, label in comparisons:
        expected = expected_bundle.get(key)
        actual = actual_bundle.get(key)
        if expected and actual and expected != actual:
            mismatches.append(f"{label}: expected {expected}, got {actual}")

    if mismatches:
        raise ValueError(
            "Installed PolicyEngine runtime does not match the microdata manifest. "
            + "; ".join(mismatches)
        )


def _weighted_top_share(frame, value_column, rank_column, top_share):
    """Return top-share metrics with records split at the cutoff."""
    ordered = frame.sort_values(rank_column).reset_index(drop=True)
    weights = ordered["household_weight"].to_numpy(dtype=float)
    values = ordered[value_column].to_numpy(dtype=float)
    total_weight = float(weights.sum())
    total_value = float((values * weights).sum())
    cutoff = (1 - top_share) * total_weight
    lower = np.concatenate([[0.0], np.cumsum(weights[:-1])])
    upper = lower + weights
    overlap = np.maximum(
        0,
        np.minimum(upper, total_weight) - np.maximum(lower, cutoff),
    )
    top_value = float((values * overlap).sum())
    return {
        "share": top_value / total_value if total_value else 0,
        "amount_b": top_value / 1e9,
        "total_b": total_value / 1e9,
    }


def _weighted_group_totals(frame, rank_column, component_columns):
    """Return weighted component totals split across percentile boundaries."""
    ordered = frame.sort_values(rank_column).reset_index(drop=True)
    weights = ordered["household_weight"].to_numpy(dtype=float)
    total_weight = float(weights.sum())
    lower = np.concatenate([[0.0], np.cumsum(weights[:-1])])
    upper = lower + weights

    groups = []
    for lower_share, upper_share, label in GROUP_EDGES:
        group_lower = lower_share * total_weight
        group_upper = upper_share * total_weight
        group_weight = 0.0
        component_totals = {key: 0.0 for key in component_columns}

        for i, record_lower in enumerate(lower):
            overlap = min(upper[i], group_upper) - max(record_lower, group_lower)
            if overlap <= 0:
                continue

            group_weight += overlap
            for key, column in component_columns.items():
                component_totals[key] += float(ordered.loc[i, column]) * overlap

        groups.append({
            "label": label,
            "lower_percentile": lower_share,
            "upper_percentile": upper_share,
            "household_weight": group_weight,
            "components_b": {
                key: value / 1e9 for key, value in component_totals.items()
            },
        })

    return groups


def _add_group_totals(groups):
    for group in groups:
        total_b = sum(group["components_b"].values())
        group["total_b"] = total_b
        group["mean_per_household"] = (
            total_b * 1e9 / group["household_weight"]
            if group["household_weight"]
            else 0.0
        )
    return groups


def _net_component_frame(sim, baseline_frame):
    frame = baseline_frame.copy()
    frame["market"] = frame["household_market_income"]
    frame["benefits"] = np.asarray(
        sim.calculate("household_benefits", period=YEAR), dtype=float
    )
    frame["refundableCredits"] = np.asarray(
        sim.calculate("household_refundable_tax_credits", period=YEAR), dtype=float
    )
    frame["taxes"] = -np.asarray(
        sim.calculate("household_tax_before_refundable_credits", period=YEAR),
        dtype=float,
    )
    return frame


def _capital_benchmark_payload(baseline):
    local_series = []
    for item in [
        {
            "label": "Net capital income, ranked by market income",
            "description": (
                "The same net capital-income measure shown in the chart: capital gains, "
                "taxable interest, dividends, and rental income, including losses."
            ),
            "value_column": "capital",
            "rank_column": "household_market_income",
        },
        {
            "label": "Positive capital income, ranked by market income",
            "description": (
                "Same sources, but losses are set to zero before summing. This is usually "
                "the easier comparison to tax-data benchmarks."
            ),
            "value_column": "positiveCapital",
            "rank_column": "household_market_income",
        },
        {
            "label": "Positive capital income, ranked by capital income",
            "description": (
                "Shows how concentrated the positive capital-income dollars are among "
                "capital-income recipients themselves."
            ),
            "value_column": "positiveCapital",
            "rank_column": "positiveCapital",
        },
    ]:
        shares = {
            key: {
                "label": label,
                **_weighted_top_share(
                    baseline,
                    item["value_column"],
                    item["rank_column"],
                    top_share,
                ),
            }
            for key, label, top_share in TOP_SHARE_CUTOFFS
        }
        local_series.append({
            "label": item["label"],
            "description": item["description"],
            "shares": shares,
        })

    return {
        "summary": (
            "Capital-income benchmarks are not perfectly apples-to-apples. Our local "
            "figures are household-weighted; IRS percentiles are tax returns ranked "
            "by AGI; CBO uses households adjusted for size; the Fed benchmark is an "
            "asset-holding benchmark rather than an income-flow benchmark."
        ),
        "local": local_series,
        "external": [
            {
                "source": "IRS Statistics of Income, Table 4.3, tax year 2022",
                "url": (
                    "https://www.irs.gov/statistics/"
                    "soi-tax-stats-individual-statistical-tables-by-tax-rate-and-income-percentile"
                ),
                "benchmark": (
                    "Top 10% of AGI-ranked individual returns received 92.1% of net "
                    "capital asset gains, 75.7% of ordinary dividends, and 72.9% of "
                    "taxable interest. Top 1% received 75.0% of net capital gains."
                ),
                "comparison": (
                    "Closest tax-data check for realized capital income, but it ranks "
                    "tax returns by AGI rather than households by market income."
                ),
            },
            {
                "source": "CBO, The Distribution of Household Income in 2022",
                "url": "https://www.cbo.gov/system/files/2026-01/61911-Household-Income-2022.pdf",
                "benchmark": (
                    "CBO includes realized capital gains in market income and notes "
                    "that capital-gains swings are concentrated among high-income "
                    "households."
                ),
                "comparison": (
                    "Best conceptual benchmark for household distribution, though "
                    "CBO's public report does not mirror our exact capital-income "
                    "bucket."
                ),
            },
            {
                "source": "Federal Reserve, 2022 Survey of Consumer Finances",
                "url": "https://www.federalreserve.gov/publications/files/scf23.pdf",
                "benchmark": (
                    "58% of families held stock directly or indirectly, but 95% of "
                    "top-decile families held stock versus 34% in the bottom half."
                ),
                "comparison": (
                    "Useful holdings benchmark: broad participation does not imply "
                    "broad dollar ownership or broad capital-income flows."
                ),
            },
        ],
    }


def build_income_distribution_payload(
    baseline_microdata_path=BASELINE_MICRODATA_PATH,
    microdata_manifest_path=MICRODATA_MANIFEST_PATH,
    microsim_factory=managed_us_microsimulation,
):
    """Build the website payload for baseline income distribution context."""
    manifest, baseline_entry = _read_microdata_manifest(microdata_manifest_path)
    baseline = pd.read_csv(baseline_microdata_path)
    _validate_baseline_microdata(
        baseline,
        baseline_microdata_path,
        manifest,
        baseline_entry,
    )
    sim = _instantiate_runtime_microsim(microsim_factory, manifest)
    _validate_runtime_bundle(manifest, sim)

    baseline["labor"] = baseline["employment_income"] + baseline[
        "self_employment_income"
    ]
    baseline["capital"] = baseline[list(CAPITAL_INCOME_VARS)].sum(axis=1)
    baseline["positiveCapital"] = baseline[list(CAPITAL_INCOME_VARS)].clip(
        lower=0
    ).sum(axis=1)
    baseline["otherMarket"] = (
        baseline["household_market_income"]
        - baseline["labor"]
        - baseline["capital"]
    )

    market_groups = _add_group_totals(
        _weighted_group_totals(
            baseline,
            "household_market_income",
            {
                "labor": "labor",
                "capital": "capital",
                "otherMarket": "otherMarket",
            },
        )
    )

    net_frame = _net_component_frame(sim, baseline)
    net_groups = _add_group_totals(
        _weighted_group_totals(
            net_frame,
            "household_net_income",
            {
                "market": "market",
                "benefits": "benefits",
                "refundableCredits": "refundableCredits",
                "taxes": "taxes",
            },
        )
    )

    return {
        "year": YEAR,
        "source": _source_metadata(manifest, baseline_entry, baseline_microdata_path),
        "grouping": (
            "Households are ranked by the income concept shown. Records are "
            "split across percentile cutoffs when their survey weight spans a "
            "boundary."
        ),
        "views": {
            "composition": "Each component as a percent of the group's total income.",
            "absolute": "Aggregate dollars in each group, in billions.",
            "shareOfTotal": (
                "Each component's contribution as a percent of national total "
                "income for the concept."
            ),
        },
        "market": {
            "title": "Market income",
            "rank_variable": "household_market_income",
            "total_b": sum(group["total_b"] for group in market_groups),
            "components": list(MARKET_COMPONENTS),
            "groups": market_groups,
        },
        "net": {
            "title": "Net income",
            "rank_variable": "household_net_income",
            "total_b": sum(group["total_b"] for group in net_groups),
            "components": list(NET_COMPONENTS),
            "groups": net_groups,
        },
        "capitalBenchmarks": _capital_benchmark_payload(baseline),
    }


def main():
    payload = build_income_distribution_payload()
    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
