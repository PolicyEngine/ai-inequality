"""Tests for local household-level microdata export helpers."""

import numpy as np

from analysis.constants import CAPITAL_INCOME_VARS
from analysis.microdata_export import (
    scenario_household_microdata,
    write_microdata_manifest,
)


class _FakeSim:
    def __init__(self, values):
        self.values = values

    def calculate(self, variable, period=None, map_to=None):
        if map_to == "household":
            return np.asarray(self.values[variable], dtype=float)
        return np.asarray(self.values[variable], dtype=float)


def test_scenario_household_microdata_includes_distribution_columns():
    values = {
        "household_weight": [1.0, 2.0],
        "household_count_people": [1.0, 3.0],
        "household_market_income": [10.0, 20.0],
        "household_net_income": [8.0, 15.0],
        "household_net_income_including_health_benefits": [9.0, 18.0],
        "employment_income": [5.0, 10.0],
        "self_employment_income": [0.0, 2.0],
        "long_term_capital_gains": [1.0, -2.0],
        "short_term_capital_gains": [0.0, 3.0],
        "taxable_interest_income": [0.5, 0.0],
        "qualified_dividend_income": [0.0, 0.0],
        "non_qualified_dividend_income": [0.0, 1.0],
        "rental_income": [0.0, 4.0],
    }
    sim = _FakeSim(values)

    frame = scenario_household_microdata(sim, "10% shift", 10)

    assert list(frame["scenario_label"]) == ["10% shift", "10% shift"]
    assert list(frame["shift_pct"]) == [10, 10]
    assert list(frame["positive_capital_income"]) == [1.5, 8.0]
    assert list(frame["has_positive_capital_income"]) == [True, True]
    for variable in CAPITAL_INCOME_VARS:
        assert variable in frame.columns


def test_write_microdata_manifest_preserves_release_bundle_metadata(tmp_path):
    manifest = write_microdata_manifest(
        tmp_path,
        {
            "dataset_name": "enhanced_cps_2024",
            "dataset_uri": "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.73.0",
            "policyengine_package": "policyengine",
            "policyengine_version": "3.4.4",
            "country_model_package": "policyengine-us",
            "country_model_version": "1.636.2",
            "policyengine_us_version": "1.636.2",
            "data_package": "policyengine-us-data",
            "data_version": "1.73.0",
            "policyengine_bundle": {
                "policyengine_version": "3.4.4",
                "model_version": "1.636.2",
                "data_version": "1.73.0",
                "runtime_dataset": "enhanced_cps_2024",
                "runtime_dataset_uri": "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.73.0",
            },
        },
        [{"label": "Baseline", "shift_pct": 0, "filename": "baseline.csv.gz"}],
    )

    assert manifest["dataset_uri"].endswith("@1.73.0")
    assert manifest["country_model_version"] == "1.636.2"
    assert manifest["data_version"] == "1.73.0"
    assert manifest["policyengine_bundle"]["runtime_dataset"] == "enhanced_cps_2024"
