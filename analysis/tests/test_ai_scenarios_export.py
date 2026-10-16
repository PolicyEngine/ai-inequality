"""Tests for the AI scenario website export shape."""

import pytest

from analysis.website_exports import (
    AI_SCENARIO_DESCRIPTION,
    ai_scenarios_website_payload,
)


def _scenario_row(label="Rapid / proportional", **overrides):
    row = {
        "scenario": {
            "name": "Rapid",
            "label": label,
            "inequality": "proportional",
            "hold_shares_fixed": False,
            "realization_rate": 1.0,
            "gdp_growth": 0.0717,
            "capital_growth": 0.1728,
            "labor_growth": -0.0094,
            "inequality_lambda": 1.0,
        },
        "diagnostics": {"labor_crossover_income": None},
        "total_rev_change_b": 205.7,
        "fed_income_tax_change_b": 180.2,
        "payroll_change_b": -16.1,
        "fed_capital_gains_tax_change_b": 40.0,
        "benefits_change_b": 3.2,
        "refundable_credits_change_b": -1.1,
        "state_tax_change_b": 22.4,
        "snap_change_b": 1.0,
        "eitc_change_b": -0.4,
        "market_income_change_b": 764.0,
        "net_income_change_b": 558.3,
        "spm_poverty_rate": 0.1258,
        "net_gini": 0.4644,
        "market_gini": 0.5200,
        "net_top_1_share": 0.1400,
        "net_top_10_share": 0.3100,
        "net_bottom_20_share": 0.0400,
        "decile_shares": [0.01 * i for i in range(1, 11)],
    }
    row.update(overrides)
    return row


def _result(**overrides):
    result = {
        "year": 2030,
        "metadata": {
            "corporate_tax_scope_note": "no corporate tax",
            "policyengine_version": "4.22.3",
            "country_model_package": "policyengine-us",
            "country_model_version": "1.764.6",
            "data_package": "populace-data",
            "data_version": "0.1.0",
            "dataset_name": "populace_us_2024",
            "certified_data_build_id": "build-id",
            "capital_income_vars": ["long_term_capital_gains"],
        },
        "baseline": {
            "spm_poverty_rate": 0.1250,
            "net_gini": 0.4570,
            "market_gini": 0.5150,
            "net_top_1_share": 0.1350,
            "decile_shares": [0.01 * i for i in range(1, 11)],
            "context": {"modelled_labor_share": 0.7507},
        },
        "scenarios": [_scenario_row()],
        "sensitivities": {"realization": [_scenario_row("Rapid / realization 50%")]},
    }
    result.update(overrides)
    return result


class TestAIScenarioPayload:
    def test_carries_year_and_description(self):
        payload = ai_scenarios_website_payload(_result())
        assert payload["year"] == 2030
        assert payload["metadata"]["year"] == 2030
        assert payload["metadata"]["description"] == AI_SCENARIO_DESCRIPTION

    def test_carries_provenance_so_charts_can_cite_the_build(self):
        metadata = ai_scenarios_website_payload(_result())["metadata"]
        assert metadata["countryModelVersion"] == "1.764.6"
        assert metadata["dataPackage"] == "populace-data"
        assert metadata["datasetName"] == "populace_us_2024"
        assert metadata["certifiedDataBuildId"] == "build-id"

    def test_scope_note_survives_into_the_payload(self):
        metadata = ai_scenarios_website_payload(_result())["metadata"]
        assert metadata["corporateTaxScopeNote"] == "no corporate tax"

    def test_scenario_fields_are_camel_cased(self):
        scenario = ai_scenarios_website_payload(_result())["scenarios"][0]
        assert scenario["revenueChange"] == pytest.approx(205.7)
        assert scenario["payrollChange"] == pytest.approx(-16.1)
        assert scenario["capitalGrowth"] == pytest.approx(0.1728)
        assert scenario["label"] == "Rapid / proportional"

    def test_poverty_and_gini_changes_are_computed_against_baseline(self):
        scenario = ai_scenarios_website_payload(_result())["scenarios"][0]
        assert scenario["povertyRateChange"] == pytest.approx(0.1258 - 0.1250)
        assert scenario["netGiniChange"] == pytest.approx(0.4644 - 0.4570)

    def test_baseline_block_carries_levels_and_context(self):
        baseline = ai_scenarios_website_payload(_result())["baseline"]
        assert baseline["povertyRate"] == pytest.approx(0.1250)
        assert baseline["context"]["modelled_labor_share"] == pytest.approx(0.7507)

    def test_sensitivities_are_serialized_with_the_same_shape(self):
        payload = ai_scenarios_website_payload(_result())
        realization = payload["sensitivities"]["realization"]
        assert len(realization) == 1
        assert realization[0]["label"] == "Rapid / realization 50%"
        assert "povertyRateChange" in realization[0]

    def test_missing_sensitivities_key_is_tolerated(self):
        payload = ai_scenarios_website_payload(_result(sensitivities=None))
        assert payload["sensitivities"] == {}

    def test_none_valued_fields_are_dropped(self):
        """A null crossover is the proportional case, not missing data."""
        scenario = ai_scenarios_website_payload(_result())["scenarios"][0]
        assert "laborCrossoverIncome" not in scenario

    def test_crossover_is_carried_when_present(self):
        row = _scenario_row()
        row["diagnostics"]["labor_crossover_income"] = 61_500.0
        payload = ai_scenarios_website_payload(_result(scenarios=[row]))
        assert payload["scenarios"][0]["laborCrossoverIncome"] == pytest.approx(
            61_500.0
        )

    def test_empty_scenario_list_produces_an_empty_payload_not_an_error(self):
        payload = ai_scenarios_website_payload(_result(scenarios=[]))
        assert payload["scenarios"] == []
        assert payload["baseline"]["povertyRate"] == pytest.approx(0.1250)


class TestCheckpointRoundTrip:
    """A run this long must not be all-or-nothing."""

    def test_append_then_load_round_trips(self, tmp_path):
        from analysis.compute_ai_scenarios import append_checkpoint, load_checkpoint

        path = str(tmp_path / "checkpoint.jsonl")
        append_checkpoint(path, "grid:Rapid / proportional", {"revenue": 205.7})
        append_checkpoint(path, "realization:0.5", {"revenue": 110.0})

        loaded = load_checkpoint(path)
        assert loaded["grid:Rapid / proportional"] == {"revenue": 205.7}
        assert loaded["realization:0.5"] == {"revenue": 110.0}

    def test_missing_file_loads_as_empty(self, tmp_path):
        from analysis.compute_ai_scenarios import load_checkpoint

        assert load_checkpoint(str(tmp_path / "absent.jsonl")) == {}

    def test_none_path_is_a_no_op(self, tmp_path):
        from analysis.compute_ai_scenarios import append_checkpoint, load_checkpoint

        append_checkpoint(None, "key", {"a": 1})
        assert load_checkpoint(None) == {}

    def test_torn_final_line_is_discarded_not_fatal(self, tmp_path):
        """A process killed mid-write leaves a partial line; resume anyway."""
        from analysis.compute_ai_scenarios import append_checkpoint, load_checkpoint

        path = tmp_path / "checkpoint.jsonl"
        append_checkpoint(str(path), "grid:Slow / proportional", {"revenue": 5.9})
        with open(path, "a") as handle:
            handle.write('{"key": "grid:Moderate / propor')

        loaded = load_checkpoint(str(path))
        assert loaded == {"grid:Slow / proportional": {"revenue": 5.9}}

    def test_later_record_wins_for_a_repeated_key(self, tmp_path):
        from analysis.compute_ai_scenarios import append_checkpoint, load_checkpoint

        path = str(tmp_path / "checkpoint.jsonl")
        append_checkpoint(path, "grid:Rapid / proportional", {"revenue": 1.0})
        append_checkpoint(path, "grid:Rapid / proportional", {"revenue": 2.0})
        assert load_checkpoint(path)["grid:Rapid / proportional"] == {"revenue": 2.0}


class TestCheckpointKeysCarryScenarioInputs:
    """A resumed unit must have been computed from the inputs being asked for.

    The Budget Lab's 2026-10-09 revision changed the Moderate and Rapid labor
    shares but no scenario label. A store keyed by label alone would have
    handed the July cells back to a rerun on the revised inputs.
    """

    def test_same_label_different_inputs_get_different_keys(self):
        from analysis.ai_scenarios import CAPITAL_INCOME_VARS, build_scenario
        from analysis.compute_ai_scenarios import scenario_checkpoint_key

        revised = build_scenario("Rapid")
        july = build_scenario("Rapid", target_labor_share=0.513)
        assert revised.label == july.label
        assert scenario_checkpoint_key(
            "grid:Rapid / proportional", revised, CAPITAL_INCOME_VARS
        ) != scenario_checkpoint_key(
            "grid:Rapid / proportional", july, CAPITAL_INCOME_VARS
        )

    def test_key_is_deterministic(self):
        from analysis.ai_scenarios import CAPITAL_INCOME_VARS, build_scenario
        from analysis.compute_ai_scenarios import scenario_checkpoint_key

        first = scenario_checkpoint_key(
            "grid:x", build_scenario("Moderate"), CAPITAL_INCOME_VARS
        )
        second = scenario_checkpoint_key(
            "grid:x", build_scenario("Moderate"), tuple(CAPITAL_INCOME_VARS)
        )
        assert first == second
        assert first.startswith("grid:x@")

    def test_capital_scope_is_part_of_the_key(self):
        from analysis.ai_scenarios import (
            CAPITAL_INCOME_VARS,
            CAPITAL_INCOME_VARS_EXCL_RETIREMENT,
            build_scenario,
        )
        from analysis.compute_ai_scenarios import scenario_checkpoint_key

        scenario = build_scenario("Slow")
        assert scenario_checkpoint_key(
            "u", scenario, CAPITAL_INCOME_VARS
        ) != scenario_checkpoint_key("u", scenario, CAPITAL_INCOME_VARS_EXCL_RETIREMENT)

    def test_a_label_only_match_is_recomputed_and_an_exact_match_is_reused(self):
        from analysis.ai_scenarios import CAPITAL_INCOME_VARS, build_scenario
        from analysis.compute_ai_scenarios import _run_one, scenario_checkpoint_key

        class Recomputed(Exception):
            pass

        def factory():
            raise Recomputed

        revised = build_scenario("Rapid")
        july = build_scenario("Rapid", target_labor_share=0.513)
        stale = {
            "grid:Rapid / proportional": {"revenue": "July, keyed by label"},
            scenario_checkpoint_key(
                "grid:Rapid / proportional", july, CAPITAL_INCOME_VARS
            ): {"revenue": "July, keyed by July inputs"},
        }
        args = (revised, {}, {}, factory, 2030, CAPITAL_INCOME_VARS, False)
        with pytest.raises(Recomputed):
            _run_one(
                *args,
                checkpoint=stale,
                checkpoint_key="grid:Rapid / proportional",
            )

        fresh = {
            scenario_checkpoint_key(
                "grid:Rapid / proportional", revised, CAPITAL_INCOME_VARS
            ): {"revenue": "revised"}
        }
        assert _run_one(
            *args, checkpoint=fresh, checkpoint_key="grid:Rapid / proportional"
        ) == {"revenue": "revised"}
