"""Tests for runtime provenance: legacy input renames and resume-store fingerprints.

A refresh on a new engine must neither reuse numbers another runtime wrote nor
silently drop a stored input the engine has renamed. Everything here runs on
fakes, without policyengine installed.
"""

import json
import sys
import types
import warnings
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from analysis import policyengine_runtime as runtime


class _FakeSim:
    """The slice of a Microsimulation the rename and bundle code touches."""

    def __init__(self, variables, person_by_year, simulated_ids=None):
        self.tax_benefit_system = SimpleNamespace(variables=variables)
        self.dataset = SimpleNamespace(
            datasets={
                year: SimpleNamespace(person=person)
                for year, person in person_by_year.items()
            }
        )
        self._simulated_ids = simulated_ids
        self.inputs = {}

    def calculate(self, variable, period=None):
        assert variable == "person_id"
        year = int(str(period)[:4])
        ids = (
            self._simulated_ids
            if self._simulated_ids is not None
            else self.dataset.datasets[year].person["person_id"].to_numpy()
        )
        return SimpleNamespace(values=np.asarray(ids))

    def set_input(self, variable, period, values):
        self.inputs[(variable, period)] = np.asarray(values)


def _variables(*names, period="month"):
    return {name: SimpleNamespace(definition_period=period) for name in names}


def _person(claims, ids=None):
    ids = list(range(1, len(claims) + 1)) if ids is None else ids
    return pd.DataFrame({"person_id": ids, "would_claim_wic": claims})


class TestLegacyInputRenames:
    def test_stored_claim_draw_becomes_the_live_take_up_input_every_month(self):
        sim = _FakeSim(
            _variables("takes_up_wic_if_eligible", "person_id"),
            {2024: _person([True, False, True]), 2030: _person([False, False, True])},
        )

        applied = runtime.apply_legacy_input_renames(sim)

        assert applied == {"would_claim_wic": "takes_up_wic_if_eligible"}
        assert len(sim.inputs) == 24
        np.testing.assert_array_equal(
            sim.inputs[("takes_up_wic_if_eligible", "2024-07")], [True, False, True]
        )
        np.testing.assert_array_equal(
            sim.inputs[("takes_up_wic_if_eligible", "2030-12")], [False, False, True]
        )

    def test_engine_that_still_knows_the_legacy_name_is_left_alone(self):
        sim = _FakeSim(
            _variables("would_claim_wic", "takes_up_wic_if_eligible"),
            {2024: _person([True])},
        )
        assert runtime.apply_legacy_input_renames(sim) == {}
        assert sim.inputs == {}

    def test_engine_without_the_live_input_is_left_alone(self):
        sim = _FakeSim(_variables("person_id"), {2024: _person([True])})
        assert runtime.apply_legacy_input_renames(sim) == {}

    def test_data_that_already_carries_the_live_input_is_left_alone(self):
        person = _person([True, False])
        person["takes_up_wic_if_eligible"] = [False, False]
        sim = _FakeSim(_variables("takes_up_wic_if_eligible"), {2024: person})
        assert runtime.apply_legacy_input_renames(sim) == {}
        assert sim.inputs == {}

    def test_misaligned_person_order_refuses(self):
        sim = _FakeSim(
            _variables("takes_up_wic_if_eligible"),
            {2024: _person([True, False])},
            simulated_ids=[2, 1],
        )
        with pytest.raises(ValueError, match="person order"):
            runtime.apply_legacy_input_renames(sim)

    def test_yearly_live_input_is_set_once_per_year(self):
        sim = _FakeSim(
            _variables("takes_up_wic_if_eligible", period="year"),
            {2024: _person([True])},
        )
        runtime.apply_legacy_input_renames(sim)
        assert list(sim.inputs) == [("takes_up_wic_if_eligible", "2024")]

    def test_managed_simulation_records_the_renames_in_its_bundle(self, monkeypatch):
        sim = _FakeSim(_variables("takes_up_wic_if_eligible"), {2024: _person([True])})
        sim.policyengine_bundle = {"model_version": "2.2.1"}
        fake = types.ModuleType("policyengine.tax_benefit_models.us")
        fake.managed_microsimulation = lambda **kwargs: sim
        monkeypatch.setitem(sys.modules, "policyengine.tax_benefit_models.us", fake)

        result = runtime.managed_us_microsimulation()

        assert result is sim
        assert sim.policyengine_bundle["legacy_input_renames"] == {
            "would_claim_wic": "takes_up_wic_if_eligible"
        }


class TestRuntimeFingerprint:
    def test_digest_is_stable(self):
        assert runtime.runtime_fingerprint() == runtime.runtime_fingerprint()

    def test_revision_bump_changes_the_digest(self, monkeypatch):
        before = runtime.runtime_fingerprint()["digest"]
        monkeypatch.setattr(runtime, "RUNTIME_REVISION", runtime.RUNTIME_REVISION + 1)
        assert runtime.runtime_fingerprint()["digest"] != before

    def test_rename_register_change_changes_the_digest(self, monkeypatch):
        before = runtime.runtime_fingerprint()["digest"]
        monkeypatch.setattr(runtime, "LEGACY_INPUT_RENAMES", {})
        assert runtime.runtime_fingerprint()["digest"] != before

    def test_package_version_change_changes_the_digest(self, monkeypatch):
        before = runtime.runtime_fingerprint()["digest"]
        real_version = runtime.importlib.metadata.version

        def fake_version(package):
            if package == "policyengine-us":
                return "0.0.0-test"
            return real_version(package)

        monkeypatch.setattr(runtime.importlib.metadata, "version", fake_version)
        assert runtime.runtime_fingerprint()["digest"] != before


class TestFingerprintedCheckpoints:
    def test_only_units_from_the_same_runtime_resume(self, tmp_path):
        from analysis.compute_ai_scenarios import append_checkpoint, load_checkpoint

        path = str(tmp_path / "checkpoint.jsonl")
        append_checkpoint(path, "grid:Rapid / proportional", {"revenue": 1.0}, "old")
        append_checkpoint(path, "grid:Slow / proportional", {"revenue": 2.0}, "new")

        with pytest.warns(UserWarning, match="skipped 1 checkpoint unit"):
            loaded = load_checkpoint(path, "new")
        assert loaded == {"grid:Slow / proportional": {"revenue": 2.0}}

    def test_units_written_before_fingerprints_are_not_resumed(self, tmp_path):
        from analysis.compute_ai_scenarios import load_checkpoint

        path = tmp_path / "checkpoint.jsonl"
        path.write_text(json.dumps({"key": "baseline", "payload": {"a": 1}}) + "\n")

        with pytest.warns(UserWarning, match="another runtime"):
            assert load_checkpoint(str(path), "current") == {}

    def test_no_fingerprint_keeps_the_old_behaviour(self, tmp_path):
        from analysis.compute_ai_scenarios import append_checkpoint, load_checkpoint

        path = str(tmp_path / "checkpoint.jsonl")
        append_checkpoint(path, "k", {"a": 1}, "any")
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert load_checkpoint(path) == {"k": {"a": 1}}


class TestTransferDetailPrograms:
    def test_programs_come_from_the_running_engine(self):
        from analysis.compute_transfer_detail import benefit_programs

        programs = ["snap", "housing_assistance", "trump_dividend"]
        parameters = lambda instant: SimpleNamespace(  # noqa: E731
            gov=SimpleNamespace(household=SimpleNamespace(household_benefits=programs))
        )
        sim = SimpleNamespace(tax_benefit_system=SimpleNamespace(parameters=parameters))
        assert benefit_programs(sim, 2030) == programs

    def test_sum_residual_is_the_total_less_its_programs(self):
        from analysis.compute_transfer_detail import _sum_residual_b

        totals = {"household_benefits": 10e9, "snap": 4e9, "wic": 5e9}
        assert _sum_residual_b(totals, ["snap", "wic"]) == pytest.approx(1.0)
        assert _sum_residual_b({**totals, "wic": None}, ["snap", "wic"]) is None


class TestStateExposureProvenance:
    def _patch(self, monkeypatch, digest, runs):
        from analysis import compute_state_exposure as exposure

        monkeypatch.setattr(exposure, "runtime_fingerprint", lambda: {"digest": digest})

        def fake_sim():
            runs.append(1)
            return SimpleNamespace(
                tax_benefit_system=SimpleNamespace(
                    variables={
                        "wa_income_tax_before_refundable_credits": SimpleNamespace(
                            adds=["wa_capital_gains_tax", "wa_millionaires_tax"]
                        )
                    }
                )
            )

        monkeypatch.setattr(exposure, "managed_us_microsimulation", fake_sim)
        monkeypatch.setattr(
            exposure, "state_revenue_components", lambda sim, year: {"CA": {"x": 1.0}}
        )
        return exposure

    def test_cache_is_reused_only_by_the_same_runtime_and_year(
        self, monkeypatch, tmp_path
    ):
        runs = []
        cache = str(tmp_path / "baseline.json")
        exposure = self._patch(monkeypatch, "aaa", runs)
        exposure.baseline_state_levels(year=2030, verbose=False, cache_path=cache)
        exposure.baseline_state_levels(year=2030, verbose=False, cache_path=cache)
        assert runs == [1]

        exposure = self._patch(monkeypatch, "bbb", runs)
        with pytest.warns(UserWarning, match="another runtime"):
            exposure.baseline_state_levels(year=2030, verbose=False, cache_path=cache)
        assert runs == [1, 1]

    def test_legacy_unfingerprinted_cache_is_recomputed(self, monkeypatch, tmp_path):
        runs = []
        cache = tmp_path / "baseline.json"
        cache.write_text(json.dumps({"CA": {"x": 9.0}}))
        exposure = self._patch(monkeypatch, "aaa", runs)
        with pytest.warns(UserWarning, match="another runtime"):
            levels = exposure.baseline_state_levels(
                year=2030, verbose=False, cache_path=str(cache)
            )
        assert levels == {"CA": {"x": 1.0}} and runs == [1]

    def test_capital_only_premise_is_checked_on_the_engine(self):
        from analysis.compute_state_exposure import _verify_capital_only_states

        sim = SimpleNamespace(
            tax_benefit_system=SimpleNamespace(
                variables={
                    "wa_income_tax_before_refundable_credits": SimpleNamespace(
                        adds=["wa_capital_gains_tax", "wa_wage_tax"]
                    )
                }
            )
        )
        with pytest.raises(ValueError, match="capital-only"):
            _verify_capital_only_states(sim)

    def test_scenarios_from_another_runtime_are_refused(self, monkeypatch, tmp_path):
        exposure = self._patch(monkeypatch, "current", [])
        scenarios = tmp_path / "scenarios.json"
        scenarios.write_text(
            json.dumps(
                {
                    "metadata": {"runtime_fingerprint": {"digest": "other"}},
                    "scenarios": [],
                }
            )
        )
        with pytest.raises(ValueError, match="rerun one of them"):
            exposure.build(
                verbose=False,
                scenarios_path=str(scenarios),
                output_path=str(tmp_path / "out.json"),
                website_output_path="none",
                cache_path="",
            )


RESULT = {"scenarios": [], "metadata": {"corporate_tax_scope_note": "note"}}


class TestOutputPaths:
    """A bare filename needs no directory; a nested one is created."""

    def test_scenarios_cli_writes_bare_and_nested_filenames(
        self, monkeypatch, tmp_path
    ):
        from analysis import compute_ai_scenarios as scenarios

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            scenarios, "run_ai_scenarios", lambda **kwargs: dict(RESULT)
        )
        monkeypatch.setattr(
            scenarios, "ai_scenarios_website_payload", lambda result: {"site": True}
        )
        monkeypatch.setattr(scenarios, "summary_table", lambda result: [])

        scenarios.main(
            [
                "--output",
                "scen.json",
                "--website-output",
                "site.json",
                "--checkpoint",
                "none",
            ]
        )
        scenarios.main(
            [
                "--output",
                "out/scen.json",
                "--website-output",
                "web/data/site.json",
                "--checkpoint",
                "none",
            ]
        )

        for name in ("scen.json", "out/scen.json"):
            assert json.loads((tmp_path / name).read_text()) == RESULT
        for name in ("site.json", "web/data/site.json"):
            assert json.loads((tmp_path / name).read_text()) == {"site": True}

    def test_state_baseline_cache_accepts_a_bare_filename(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        exposure = TestStateExposureProvenance()._patch(monkeypatch, "aaa", [])

        exposure.baseline_state_levels(
            year=2030, verbose=False, cache_path="baseline.json"
        )

        cached = json.loads((tmp_path / "baseline.json").read_text())
        assert cached["fingerprint"] == "aaa" and cached["year"] == 2030

    def test_parent_dir_helper(self, tmp_path, monkeypatch):
        from analysis.compute_state_exposure import _ensure_parent_dir

        monkeypatch.chdir(tmp_path)
        _ensure_parent_dir("bare.json")  # no directory to make, no error
        _ensure_parent_dir("a/b/c.json")
        assert (tmp_path / "a" / "b").is_dir()
