"""analysis.diagnose_sweep_change: the steps from the published sweep to the
rerun add up to the change, the reproduction check catches any published value
the published configuration misses, and the configuration check catches a run
whose patches didn't take.

The ``run`` command needs policyengine-us and the pinned microdata, so only
the report's arithmetic runs here.
"""

import copy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from analysis import diagnose_sweep_change as diagnose

MONEY = st.floats(-3000, 3000, allow_nan=False)


def _deciles(pct_changes):
    return {
        "decile_impacts": {
            "scenarios": [
                {
                    "shift_pct": 10,
                    "deciles": [
                        {"decile": decile, "pct_change": change, "baseline_mean_net": 1.0}
                        for decile, change in enumerate(pct_changes, start=1)
                    ],
                }
            ]
        }
    }


def _published():
    """The published sweep's shape: its total is ``revenue_change_b``."""
    return {
        "metadata": {"baseline_facts": _deciles([0.10, -1.90])},
        "scenarios": [
            {"shift_pct": 0, "revenue_change_b": 0.0, "benefits_change_b": 0.0, "net_gini": 0.47, "spm_poverty_rate": 0.13},
            {
                "shift_pct": 10,
                "revenue_change_b": -135.3,
                "benefits_change_b": 19.1,
                "net_gini": 0.49,
                "spm_poverty_rate": 0.15,
                "state_deltas": {"CA": _published_state()},
            },
        ],
    }


def _published_state():
    return {
        "state_tax_before_refundable_credits_change_b": 3.0,
        "state_refundable_credits_change_b": 0.5,
        "state_benefits_change_b": 0.25,
        "state_net_change_b": 2.25,
    }


def _new_state(health=0.4):
    return {
        **_published_state(),
        "state_net_excluding_health_tanf_change_b": 2.25,
        "state_net_change_b": 2.25 - health,
    }


def _new_run(name, total, benefits, gini, poverty, deciles, tanf=0.2, health=66.2):
    excluded = [] if name == "published" else ["early_head_start", "head_start"]
    return {
        "metadata": {
            "diagnose_configuration": {"name": name},
            "policyengine_bundle": {"net_income_excluded_benefits": excluded},
            "baseline_facts": _deciles(deciles),
        },
        "scenarios": [
            {
                "shift_pct": 0,
                "total_rev_change_published_definition_b": 0.0,
                "revenue_change_b": 0.0,
                "benefits_change_b": 0.0,
                "net_gini": gini - 0.02,
                "spm_poverty_rate": 0.13,
                "tanf_in_state_benefits_change_b": 0.0,
                "health_change_b": 0.0,
                "total_rev_change_b": 0.0,
            },
            {
                "shift_pct": 10,
                "total_rev_change_published_definition_b": total,
                "revenue_change_b": total + tanf - health,
                "benefits_change_b": benefits,
                "net_gini": gini,
                "spm_poverty_rate": poverty,
                "tanf_in_state_benefits_change_b": tanf,
                "health_change_b": health,
                "total_rev_change_b": total + tanf - health,
                "state_deltas": {"CA": _new_state()},
            },
        ],
    }


def _runs():
    published_run = _new_run("published", -135.3, 19.1, 0.49, 0.15, [0.12, -1.92])
    head_start_run = _new_run("head_start_excluded", -130.0, 13.8, 0.495, 0.15, [0.15, -1.99])
    rerun = _new_run("rerun", -129.2, 13.0, 0.496, 0.1496, [0.15, -1.95])
    # The published sweep's Gini at 0% is the published run's.
    published = _published()
    published["scenarios"][0]["net_gini"] = published_run["scenarios"][0]["net_gini"]
    return published, published_run, head_start_run, rerun


def test_the_total_s_steps_add_up_to_the_rerun():
    steps = diagnose.total_steps(*_runs())
    assert steps["published"] == -135.3
    assert steps["head_start"] == pytest.approx(5.3)
    assert steps["labor_inputs"] == pytest.approx(0.8)
    assert steps["tanf_counted_once"] == 0.2
    assert steps["health"] == -66.2
    assert steps["rerun"] == pytest.approx(-195.2)
    assert steps["unexplained"] == pytest.approx(0.0, abs=1e-9)


@given(MONEY, MONEY, MONEY, MONEY, MONEY)
def test_the_steps_explain_everything_when_the_rerun_s_identity_holds(
    reproduced, head_start, rerun_definition, tanf, health
):
    published, published_run, head_start_run, rerun = _runs()
    published_run["scenarios"][1]["total_rev_change_published_definition_b"] = reproduced
    head_start_run["scenarios"][1]["total_rev_change_published_definition_b"] = head_start
    row = rerun["scenarios"][1]
    row.update(
        total_rev_change_published_definition_b=rerun_definition,
        tanf_in_state_benefits_change_b=tanf,
        health_change_b=health,
        total_rev_change_b=rerun_definition + tanf - health,
    )
    steps = diagnose.total_steps(published, published_run, head_start_run, rerun)
    assert steps["unexplained"] == pytest.approx(0.0, abs=1e-9)


def test_a_rerun_that_breaks_its_identity_leaves_the_gap_unexplained():
    published, published_run, head_start_run, rerun = _runs()
    rerun["scenarios"][1]["total_rev_change_b"] += 1.5
    steps = diagnose.total_steps(published, published_run, head_start_run, rerun)
    assert steps["unexplained"] == pytest.approx(1.5)


def test_the_published_configuration_reproduces_the_published_values():
    published, published_run, _, _ = _runs()
    assert diagnose.reproduction_gaps(published, published_run) == []


@pytest.mark.parametrize(
    "field, change, kind",
    [
        ("benefits_change_b", 2e-6, "b"),
        ("total_rev_change_published_definition_b", -2e-6, "b"),
        ("net_gini", 2e-9, "rate"),
        ("spm_poverty_rate", -1e-3, "rate"),
    ],
)
def test_a_reproduction_gap_beyond_float_noise_is_reported(field, change, kind):
    published, published_run, _, _ = _runs()
    published_run["scenarios"][1][field] += change
    gaps = diagnose.reproduction_gaps(published, published_run)
    assert [(gap["shift_pct"], gap["field"]) for gap in gaps] == [(10, field)]
    assert abs(change) > diagnose.REPRODUCED[kind]


def test_a_state_s_gap_is_reported_and_its_redefined_total_compared_the_old_way():
    published, published_run, _, _ = _runs()
    assert diagnose.reproduction_gaps(published, published_run) == []
    published_run["scenarios"][1]["state_deltas"]["CA"]["state_benefits_change_b"] += 0.01
    published_run["scenarios"][1]["state_deltas"]["CA"]["state_net_excluding_health_tanf_change_b"] -= 0.01
    gaps = diagnose.reproduction_gaps(published, published_run)
    assert [gap["field"] for gap in gaps] == [
        "state_deltas.CA.state_benefits_change_b",
        "state_deltas.CA.state_net_excluding_health_tanf_change_b",
    ]


def test_the_redefined_totals_never_count_as_gaps():
    # The rerun's total_rev_change_b and revenue_change_b count health and TANF;
    # the published ones don't, so the check compares the published definition.
    published, published_run, _, _ = _runs()
    row = published_run["scenarios"][1]
    assert row["total_rev_change_b"] != published["scenarios"][1]["revenue_change_b"]
    assert diagnose.reproduction_gaps(published, published_run) == []


def test_float_noise_is_no_gap():
    published, published_run, _, _ = _runs()
    published_run["scenarios"][1]["benefits_change_b"] += 5e-7
    published_run["scenarios"][1]["net_gini"] += 5e-10
    assert diagnose.reproduction_gaps(published, published_run) == []


def test_a_configuration_that_did_not_take_is_reported():
    _, published_run, head_start_run, _ = _runs()
    assert diagnose.configuration_problems(published_run, head_start_run) == []
    wrong = copy.deepcopy(published_run)
    wrong["metadata"]["policyengine_bundle"]["net_income_excluded_benefits"] = ["head_start"]
    assert diagnose.configuration_problems(wrong, head_start_run) == [
        "the published run left ['head_start'] out of net income, not []"
    ]
    assert diagnose.configuration_problems(published_run, published_run) == [
        "the head_start_excluded run records configuration 'published'",
        "the head_start_excluded run left [] out of net income, not "
        "['early_head_start', 'head_start']",
    ]


def test_field_steps_list_only_fields_a_step_moves():
    rows = diagnose.field_steps(*_runs()[1:])
    assert [row["field"] for row in rows] == [
        "benefits_change_b",
        "net_gini",
        "revenue_change_b",
        "spm_poverty_rate",
        "total_rev_change_b",
        "total_rev_change_published_definition_b",
    ]
    benefits = rows[0]
    assert benefits["head_start"] == pytest.approx(-5.3)
    assert benefits["labor_inputs"] == pytest.approx(-0.8)


def test_distribution_and_decile_steps_add_up():
    runs = _runs()
    for shift_pct in (0, 10):
        for row in diagnose.distribution_steps(*runs, shift_pct):
            assert row["reproduced"] + row["head_start"] + row["labor_inputs"] == pytest.approx(row["rerun"])
    deciles = diagnose.decile_steps(*runs)
    assert [row["decile"] for row in deciles] == [1, 2]
    for row in deciles:
        assert row["published"] + row["ties"] + row["head_start"] + row["labor_inputs"] == pytest.approx(row["rerun"])


def test_the_report_names_each_step():
    text = diagnose.report(*_runs())
    assert "reproduces every published value" in text
    assert "| -135.30 | +5.30 | +0.80 | +0.20 | -66.20 | -195.20 |" in text
    assert "The steps leave $+0.0000B unexplained." in text
    published, published_run, head_start_run, rerun = _runs()
    published_run["scenarios"][1]["benefits_change_b"] = 20.0
    assert "misses 1 of the published values" in diagnose.report(
        published, published_run, head_start_run, rerun
    )


def test_the_configurations_put_back_what_the_published_code_did(monkeypatch):
    pytest.importorskip("policyengine_core")
    from analysis import labor_capital_shift, policyengine_runtime

    excluded, setter = policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS, labor_capital_shift.set_labor_income
    with diagnose.configuration("published"):
        assert policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS == ()
        assert labor_capital_shift.set_labor_income is diagnose._set_built_labor_income_only
    with diagnose.configuration("head_start_excluded"):
        assert policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS == excluded
        assert labor_capital_shift.set_labor_income is diagnose._set_built_labor_income_only
    assert policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS == excluded
    assert labor_capital_shift.set_labor_income is setter
