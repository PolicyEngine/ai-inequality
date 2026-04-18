"""Tests for website-facing analysis exports."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

from analysis.website_exports import (
    LABOR_SHIFT_DESCRIPTION,
    labor_shift_website_payload,
)


def _result_row(
    label,
    decile_shares,
    *,
    decile_shares_including_health_benefits=None,
    market_gini=0.7,
    net_gini=0.6,
    net_gini_including_health_benefits=0.58,
    poverty_rate=0.2,
    fed_revenue=2_000_000_000.0,
    state_revenue=500_000_000.0,
    mean_net_income=100_000.0,
    mean_net_income_including_health_benefits=105_000.0,
    healthcare_benefit_value_total=600_000_000.0,
    medicaid_cost_total=400_000_000.0,
    chip_benefit_total=100_000_000.0,
    aca_ptc_total=100_000_000.0,
    ubi_per_person=None,
):
    if decile_shares_including_health_benefits is None:
        decile_shares_including_health_benefits = decile_shares
    row = {
        "label": label,
        "market_gini": market_gini,
        "net_gini": net_gini,
        "net_gini_including_health_benefits": net_gini_including_health_benefits,
        "spm_poverty_rate": poverty_rate,
        "fed_revenue": fed_revenue,
        "state_revenue": state_revenue,
        "total_revenue": fed_revenue + state_revenue,
        "top_10_share": decile_shares[9],
        "bottom_10_share": decile_shares[0],
        "top_10_share_including_health_benefits": (
            decile_shares_including_health_benefits[9]
        ),
        "bottom_10_share_including_health_benefits": (
            decile_shares_including_health_benefits[0]
        ),
        "mean_net_income": mean_net_income,
        "mean_net_income_including_health_benefits": (
            mean_net_income_including_health_benefits
        ),
        "decile_shares": decile_shares,
        "decile_shares_including_health_benefits": (
            decile_shares_including_health_benefits
        ),
        "healthcare_benefit_value_total": healthcare_benefit_value_total,
        "medicaid_cost_total": medicaid_cost_total,
        "chip_benefit_total": chip_benefit_total,
        "aca_ptc_total": aca_ptc_total,
    }
    if ubi_per_person is not None:
        row["ubi_per_person"] = ubi_per_person
    return row


def _sample_results(include_ubi):
    baseline_deciles = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.12, 0.16, 0.43]
    shift10_deciles = [0.01, 0.02, 0.03, 0.03, 0.04, 0.05, 0.07, 0.11, 0.16, 0.48]
    shift50_deciles = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.07, 0.1, 0.16, 0.52]
    ubi_deciles = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.11, 0.16, 0.44]
    baseline_resources = [0.02, 0.03, 0.04, 0.04, 0.05, 0.06, 0.07, 0.11, 0.16, 0.42]
    shift10_resources = [0.02, 0.03, 0.04, 0.04, 0.05, 0.05, 0.07, 0.1, 0.16, 0.44]
    shift50_resources = [0.02, 0.03, 0.03, 0.04, 0.04, 0.05, 0.06, 0.09, 0.16, 0.48]
    ubi_resources = [0.02, 0.03, 0.04, 0.04, 0.05, 0.06, 0.07, 0.1, 0.16, 0.43]

    results = {
        "baseline": _result_row(
            "Baseline",
            baseline_deciles,
            decile_shares_including_health_benefits=baseline_resources,
            net_gini_including_health_benefits=0.57,
            mean_net_income_including_health_benefits=106_000.0,
            healthcare_benefit_value_total=700_000_000.0,
            medicaid_cost_total=500_000_000.0,
            chip_benefit_total=100_000_000.0,
            aca_ptc_total=100_000_000.0,
        ),
        "shifts": [
            {
                **_result_row(
                    "10% shift",
                    shift10_deciles,
                    decile_shares_including_health_benefits=shift10_resources,
                    poverty_rate=0.22,
                    net_gini_including_health_benefits=0.59,
                    mean_net_income_including_health_benefits=107_000.0,
                    healthcare_benefit_value_total=900_000_000.0,
                    medicaid_cost_total=650_000_000.0,
                    chip_benefit_total=120_000_000.0,
                    aca_ptc_total=130_000_000.0,
                ),
                "shift_pct": 0.10,
            },
            {
                **_result_row(
                    "50% shift",
                    shift50_deciles,
                    decile_shares_including_health_benefits=shift50_resources,
                    poverty_rate=0.35,
                    net_gini_including_health_benefits=0.63,
                    mean_net_income_including_health_benefits=109_000.0,
                    healthcare_benefit_value_total=1_500_000_000.0,
                    medicaid_cost_total=1_100_000_000.0,
                    chip_benefit_total=150_000_000.0,
                    aca_ptc_total=250_000_000.0,
                ),
                "shift_pct": 0.50,
            },
        ],
        "ubi": None,
        "meta": {"year": 2026},
    }
    if include_ubi:
        results["ubi"] = _result_row(
            "50% shift + UBI",
            ubi_deciles,
            decile_shares_including_health_benefits=ubi_resources,
            poverty_rate=0.18,
            net_gini_including_health_benefits=0.58,
            mean_net_income_including_health_benefits=110_000.0,
            healthcare_benefit_value_total=1_600_000_000.0,
            medicaid_cost_total=1_150_000_000.0,
            chip_benefit_total=150_000_000.0,
            aca_ptc_total=300_000_000.0,
            ubi_per_person=432.1,
        )
    return results


def _load_run_simulations_module():
    """Load scripts/run_simulations.py without requiring PolicyEngine."""
    policyengine_us = types.ModuleType("policyengine_us")
    policyengine_us.Microsimulation = object
    sys.modules["policyengine_us"] = policyengine_us

    policyengine_core = types.ModuleType("policyengine_core")
    reforms = types.ModuleType("policyengine_core.reforms")

    class DummyReform:
        @staticmethod
        def from_dict(*args, **kwargs):
            return {"args": args, "kwargs": kwargs}

    reforms.Reform = DummyReform
    sys.modules["policyengine_core"] = policyengine_core
    sys.modules["policyengine_core.reforms"] = reforms

    module_path = Path(__file__).resolve().parents[2] / "scripts" / "run_simulations.py"
    spec = importlib.util.spec_from_file_location("run_simulations_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_labor_shift_payload_omits_ubi_when_absent():
    payload = labor_shift_website_payload(_sample_results(include_ubi=False))

    assert [scenario["label"] for scenario in payload["scenarios"]] == [
        "Baseline",
        "10% shift",
        "50% shift",
    ]
    assert payload["scenarios"][0]["fedRevenue"] == pytest.approx(2.0)
    assert payload["scenarios"][0]["healthcareBenefitValue"] == pytest.approx(0.7)
    assert payload["scenarios"][2]["medicaidBenefits"] == pytest.approx(1.1)
    assert payload["deciles"]["10pctShift"][9] == pytest.approx(0.44)
    assert "50pctUBI" not in payload["deciles"]
    assert payload["metadata"]["description"] == LABOR_SHIFT_DESCRIPTION
    assert payload["metadata"]["ubiScenarioAvailable"] is False


def test_labor_shift_payload_includes_ubi_when_present():
    payload = labor_shift_website_payload(_sample_results(include_ubi=True))

    assert payload["scenarios"][-1]["label"] == "50% shift + UBI"
    assert payload["scenarios"][-1]["ubiPerPerson"] == pytest.approx(432.1)
    assert payload["scenarios"][-1]["acaBenefits"] == pytest.approx(0.3)
    assert payload["deciles"]["50pctUBI"][9] == pytest.approx(0.43)
    assert payload["metadata"]["ubiScenarioAvailable"] is True


def test_gen_labor_shift_writes_payload_from_analysis_results(tmp_path, monkeypatch):
    module = _load_run_simulations_module()
    results = _sample_results(include_ubi=False)

    monkeypatch.setattr(module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(module, "run_labor_shift_scenarios", lambda: results)

    module.gen_labor_shift()

    output = json.loads((tmp_path / "laborShiftData.json").read_text())
    assert output == labor_shift_website_payload(results)


def test_gen_shift_sweep_uses_every_ten_percent_increment(tmp_path, monkeypatch):
    module = _load_run_simulations_module()
    expected = {
        "year": 2026,
        "scenarios": [
            {"shift_pct": pct, "label": "Baseline" if pct == 0 else f"{pct}% shift"}
            for pct in range(0, 101, 10)
        ],
    }

    monkeypatch.setattr(module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(module, "run_shift_sweep_analysis", lambda verbose=True: expected)

    module.gen_shift_sweep()

    output = json.loads((tmp_path / "shiftSweepData.json").read_text())
    assert output == expected
