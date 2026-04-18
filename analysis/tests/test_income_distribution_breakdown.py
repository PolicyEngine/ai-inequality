"""Tests for baseline income distribution breakdown payloads."""

import numpy as np
import pandas as pd

from analysis.income_distribution_breakdown import build_income_distribution_payload


class _FakeSim:
    def __init__(self, n):
        self.n = n

    def calculate(self, variable, period=None):
        values = {
            "household_benefits": np.full(self.n, 10.0),
            "household_refundable_tax_credits": np.full(self.n, 2.0),
            "household_tax_before_refundable_credits": np.full(self.n, 5.0),
        }
        return values[variable]


class _ManagedFakeSim(_FakeSim):
    def __init__(self, n, bundle):
        super().__init__(n)
        self.policyengine_bundle = bundle


def test_income_distribution_payload_splits_top_groups_and_net_components(tmp_path):
    n = 1000
    frame = pd.DataFrame({
        "household_weight": np.ones(n),
        "household_market_income": np.arange(1, n + 1, dtype=float),
        "household_net_income": np.arange(8, n + 8, dtype=float),
        "employment_income": np.full(n, 20.0),
        "self_employment_income": np.full(n, 5.0),
        "long_term_capital_gains": np.full(n, 3.0),
        "short_term_capital_gains": np.full(n, 2.0),
        "taxable_interest_income": np.full(n, 1.0),
        "qualified_dividend_income": np.full(n, 1.0),
        "non_qualified_dividend_income": np.full(n, 1.0),
        "rental_income": np.full(n, 1.0),
    })
    path = tmp_path / "baseline.csv.gz"
    frame.to_csv(path, index=False, compression="gzip")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        """{
          "created_at": "2026-04-15T00:00:00+00:00",
          "year": 2026,
          "dataset_name": "test_dataset",
          "policyengine_package": "policyengine",
          "policyengine_version": "test-policyengine",
          "policyengine_us_version": "test-policyengine-us",
          "policyengine_core_version": "test-policyengine-core",
          "analysis_fields": [
            "household_weight",
            "household_market_income",
            "household_net_income",
            "employment_income",
            "self_employment_income",
            "long_term_capital_gains",
            "short_term_capital_gains",
            "taxable_interest_income",
            "qualified_dividend_income",
            "non_qualified_dividend_income",
            "rental_income"
          ],
          "scenarios": [
            {
              "label": "Baseline",
              "shift_pct": 0,
              "filename": "baseline.csv.gz"
            }
          ]
        }"""
    )

    payload = build_income_distribution_payload(
        baseline_microdata_path=path,
        microdata_manifest_path=manifest_path,
        microsim_factory=lambda: _FakeSim(n),
    )

    assert payload["source"]["dataset_name"] == "test_dataset"
    assert payload["source"]["policyengine_version"] == "test-policyengine"
    assert payload["source"]["policyengine_us_version"] == "test-policyengine-us"
    labels = [group["label"] for group in payload["market"]["groups"]]
    assert labels[-3:] == ["P90-99", "P99-99.9", "Top 0.1%"]
    assert set(payload["market"]["groups"][0]["components_b"]) == {
        "labor",
        "capital",
        "otherMarket",
    }
    assert set(payload["net"]["groups"][0]["components_b"]) == {
        "market",
        "benefits",
        "refundableCredits",
        "taxes",
    }
    assert payload["net"]["groups"][0]["components_b"]["taxes"] < 0
    assert len(payload["capitalBenchmarks"]["local"]) == 3
    assert (
        payload["capitalBenchmarks"]["local"][0]["shares"]["top10"]["label"]
        == "Top 10%"
    )
    assert payload["capitalBenchmarks"]["external"][0]["source"].startswith(
        "IRS Statistics of Income"
    )


def test_income_distribution_payload_rejects_runtime_bundle_mismatch(tmp_path):
    n = 2
    frame = pd.DataFrame({
        "household_weight": np.ones(n),
        "household_market_income": np.arange(1, n + 1, dtype=float),
        "household_net_income": np.arange(8, n + 8, dtype=float),
        "employment_income": np.full(n, 20.0),
        "self_employment_income": np.full(n, 5.0),
        "long_term_capital_gains": np.full(n, 3.0),
        "short_term_capital_gains": np.full(n, 2.0),
        "taxable_interest_income": np.full(n, 1.0),
        "qualified_dividend_income": np.full(n, 1.0),
        "non_qualified_dividend_income": np.full(n, 1.0),
        "rental_income": np.full(n, 1.0),
    })
    path = tmp_path / "baseline.csv.gz"
    frame.to_csv(path, index=False, compression="gzip")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        """{
          "created_at": "2026-04-16T00:00:00+00:00",
          "year": 2026,
          "dataset_name": "enhanced_cps_2024",
          "analysis_fields": [
            "household_weight",
            "household_market_income",
            "household_net_income",
            "employment_income",
            "self_employment_income",
            "long_term_capital_gains",
            "short_term_capital_gains",
            "taxable_interest_income",
            "qualified_dividend_income",
            "non_qualified_dividend_income",
            "rental_income"
          ],
          "policyengine_bundle": {
            "policyengine_version": "3.4.4",
            "model_version": "1.636.2",
            "data_version": "1.73.0",
            "runtime_dataset": "enhanced_cps_2024",
            "runtime_dataset_uri": "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.73.0"
          },
          "scenarios": [
            {
              "label": "Baseline",
              "shift_pct": 0,
              "filename": "baseline.csv.gz"
            }
          ]
        }"""
    )

    def factory(dataset=None):
        return _ManagedFakeSim(
            n,
            {
                "policyengine_version": "3.4.5",
                "model_version": "1.636.2",
                "data_version": "1.73.0",
                "runtime_dataset": dataset or "enhanced_cps_2024",
                "runtime_dataset_uri": "hf://policyengine/policyengine-us-data/enhanced_cps_2024.h5@1.74.0",
            },
        )

    try:
        build_income_distribution_payload(
            baseline_microdata_path=path,
            microdata_manifest_path=manifest_path,
            microsim_factory=factory,
        )
    except ValueError as error:
        assert "does not match the microdata manifest" in str(error)
    else:
        raise AssertionError("Expected runtime bundle mismatch to fail")
