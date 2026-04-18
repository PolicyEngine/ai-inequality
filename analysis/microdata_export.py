"""Helpers for caching household-level scenario microdata locally."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .constants import CAPITAL_INCOME_VARS, YEAR


def _package_version(package_name):
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None


def scenario_household_microdata(sim, label, shift_pct):
    """Return a compact household-level extract for one scenario."""
    household_weight = np.asarray(
        sim.calculate("household_weight", period=YEAR), dtype=float
    )
    household_count_people = np.asarray(
        sim.calculate("household_count_people", period=YEAR), dtype=float
    )
    market_income = np.asarray(
        sim.calculate("household_market_income", period=YEAR), dtype=float
    )
    net_income = np.asarray(
        sim.calculate("household_net_income", period=YEAR), dtype=float
    )
    net_income_including_health_benefits = np.asarray(
        sim.calculate(
            "household_net_income_including_health_benefits", period=YEAR
        ),
        dtype=float,
    )

    data = {
        "scenario_label": np.repeat(label, len(household_weight)),
        "shift_pct": np.repeat(shift_pct, len(household_weight)),
        "household_weight": household_weight,
        "household_count_people": household_count_people,
        "household_market_income": market_income,
        "household_net_income": net_income,
        "household_net_income_including_health_benefits": (
            net_income_including_health_benefits
        ),
        "employment_income": np.asarray(
            sim.calculate("employment_income", period=YEAR, map_to="household"),
            dtype=float,
        ),
        "self_employment_income": np.asarray(
            sim.calculate(
                "self_employment_income", period=YEAR, map_to="household"
            ),
            dtype=float,
        ),
    }

    positive_capital_income = np.zeros(len(household_weight), dtype=float)
    for var in CAPITAL_INCOME_VARS:
        household_values = np.asarray(
            sim.calculate(var, period=YEAR, map_to="household"), dtype=float
        )
        data[var] = household_values
        positive_capital_income += np.where(household_values > 0, household_values, 0)

    data["positive_capital_income"] = positive_capital_income
    data["has_positive_capital_income"] = positive_capital_income > 0

    return pd.DataFrame(data)


def write_scenario_household_microdata(sim, output_dir, label, shift_pct):
    """Write one scenario extract and return a manifest row."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = "baseline.csv.gz" if shift_pct == 0 else f"shift_{shift_pct:03d}.csv.gz"
    path = output_dir / filename
    scenario_household_microdata(sim, label, shift_pct).to_csv(
        path, index=False, compression="gzip"
    )

    return {
        "label": label,
        "shift_pct": shift_pct,
        "filename": filename,
    }


def write_microdata_manifest(output_dir, metadata, scenario_files):
    """Write manifest metadata for a cached microdata export."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "year": YEAR,
        "dataset_name": metadata.get("dataset_name"),
        "dataset_uri": metadata.get("dataset_uri"),
        "policyengine_package": metadata.get("policyengine_package"),
        "policyengine_version": metadata.get("policyengine_version"),
        "country_model_package": metadata.get("country_model_package"),
        "country_model_version": metadata.get("country_model_version"),
        "policyengine_us_version": metadata.get("policyengine_us_version"),
        "data_package": metadata.get("data_package"),
        "data_version": metadata.get("data_version"),
        "policyengine_core_version": _package_version("policyengine-core"),
        "policyengine_bundle": metadata.get("policyengine_bundle"),
        "analysis_fields": [
            "household_weight",
            "household_count_people",
            "household_market_income",
            "household_net_income",
            "household_net_income_including_health_benefits",
            "employment_income",
            "self_employment_income",
            *CAPITAL_INCOME_VARS,
            "positive_capital_income",
            "has_positive_capital_income",
        ],
        "scenarios": scenario_files,
    }

    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest
