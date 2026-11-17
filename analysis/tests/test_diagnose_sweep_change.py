"""analysis.diagnose_sweep_change: the steps from the published sweep to the
rerun add up to the change, the published configuration prices Medicaid over
each branch's own enrollees as the published code did, the reproduction check
catches any published value the published configuration misses, and the
configuration check catches a run whose patches didn't take.

A real ``run`` needs policyengine-us and the pinned microdata. Here ``run``
gets a stand-in sweep, and the configurations get a stand-in for
``labor_capital_shift``, which imports policyengine-us, so CI checks them too.
"""

import copy
import json
import math
import sys
import types

import numpy as np
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
            {
                "shift_pct": 0,
                "revenue_change_b": 0.0,
                "benefits_change_b": 0.0,
                "net_gini": 0.47,
                "net_gini_including_health_benefits": 0.43,
                "spm_poverty_rate": 0.13,
            },
            {
                "shift_pct": 10,
                "revenue_change_b": -135.3,
                "benefits_change_b": 19.1,
                "net_gini": 0.49,
                "net_gini_including_health_benefits": 0.452,
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


#: How each configuration prices a shifted branch's Medicaid enrollees.
PRICING = {"published": "own_enrollees", "medicaid_at_baseline": "baseline", "head_start_excluded": "baseline"}


def _pricing_calls(kind, count=1):
    return {"baseline": 0, "own_enrollees": 0, "other": 0, kind: count}


def _new_run(name, total, benefits, gini, health_gini, poverty, deciles, tanf=0.2, health=66.2):
    excluded = [] if name in ("published", "medicaid_at_baseline") else ["early_head_start", "head_start"]
    configuration = {"name": name}
    if name in PRICING:
        configuration["medicaid_pricing_calls"] = _pricing_calls(PRICING[name])
    return {
        "metadata": {
            "diagnose_configuration": configuration,
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
                "net_gini_including_health_benefits": 0.43,
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
                "net_gini_including_health_benefits": health_gini,
                "spm_poverty_rate": poverty,
                "tanf_in_state_benefits_change_b": tanf,
                "health_change_b": health,
                "total_rev_change_b": total + tanf - health,
                "state_deltas": {"CA": _new_state()},
            },
        ],
    }


def _runs():
    """The published sweep, the runs in ``diagnose.RUNS`` order and the rerun.

    Pricing Medicaid at the baseline moves only the Gini with health benefits.
    """
    runs = (
        _new_run("published", -135.3, 19.1, 0.49, 0.452, 0.15, [0.12, -1.92]),
        _new_run("medicaid_at_baseline", -135.3, 19.1, 0.49, 0.4502, 0.15, [0.12, -1.92]),
        _new_run("head_start_excluded", -130.0, 13.8, 0.495, 0.4538, 0.15, [0.15, -1.99]),
    )
    rerun = _new_run("rerun", -129.2, 13.0, 0.496, 0.4537, 0.1496, [0.15, -1.95])
    # The published sweep's Gini at 0% is the published run's.
    published = _published()
    published["scenarios"][0]["net_gini"] = runs[0]["scenarios"][0]["net_gini"]
    return published, runs, rerun


def test_the_runs_follow_the_configurations():
    assert diagnose.RUNS == tuple(diagnose.CONFIGURATIONS)
    assert len(diagnose.CODE_STEPS) == len(diagnose.RUNS)


def test_the_total_s_steps_add_up_to_the_rerun():
    steps = diagnose.total_steps(*_runs())
    assert steps["published"] == -135.3
    assert steps["reproduction"] == 0.0
    assert steps["medicaid_at_baseline"] == 0.0
    assert steps["head_start"] == pytest.approx(5.3)
    assert steps["labor_inputs"] == pytest.approx(0.8)
    assert steps["tanf_counted_once"] == 0.2
    assert steps["health"] == -66.2
    assert steps["rerun"] == pytest.approx(-195.2)
    assert steps["unexplained"] == pytest.approx(0.0, abs=1e-9)


@given(MONEY, MONEY, MONEY, MONEY, MONEY, MONEY)
def test_the_steps_explain_everything_when_the_rerun_s_identity_holds(
    reproduced, medicaid, head_start, rerun_definition, tanf, health
):
    published, runs, rerun = _runs()
    for run, total in zip(runs, (reproduced, medicaid, head_start)):
        run["scenarios"][1]["total_rev_change_published_definition_b"] = total
    row = rerun["scenarios"][1]
    row.update(
        total_rev_change_published_definition_b=rerun_definition,
        tanf_in_state_benefits_change_b=tanf,
        health_change_b=health,
        total_rev_change_b=rerun_definition + tanf - health,
    )
    steps = diagnose.total_steps(published, runs, rerun)
    assert steps["unexplained"] == pytest.approx(0.0, abs=1e-9)
    # Every step together carries the published total to the rerun's.
    named = ["reproduction", *(key for key, _ in diagnose.CODE_STEPS), "tanf_counted_once", "health"]
    assert steps["published"] + sum(steps[key] for key in named) + steps["unexplained"] == pytest.approx(
        steps["rerun"], abs=1e-6
    )


def test_a_published_total_the_published_run_misses_goes_to_the_reproduction_step():
    published, runs, rerun = _runs()
    runs[0]["scenarios"][1]["total_rev_change_published_definition_b"] += 1.0
    steps = diagnose.total_steps(published, runs, rerun)
    assert steps["reproduction"] == pytest.approx(1.0)
    assert steps["medicaid_at_baseline"] == pytest.approx(-1.0)
    assert steps["unexplained"] == pytest.approx(0.0, abs=1e-9)


def test_a_rerun_that_breaks_its_identity_leaves_the_gap_unexplained():
    published, runs, rerun = _runs()
    rerun["scenarios"][1]["total_rev_change_b"] += 1.5
    steps = diagnose.total_steps(published, runs, rerun)
    assert steps["unexplained"] == pytest.approx(1.5)


def test_the_published_configuration_reproduces_the_published_values():
    published, runs, _ = _runs()
    assert diagnose.reproduction_gaps(published, runs[0]) == []


def test_a_run_that_prices_medicaid_at_baseline_misses_the_gini_with_health():
    published, runs, _ = _runs()
    gaps = diagnose.reproduction_gaps(published, runs[1])
    assert [(gap["shift_pct"], gap["field"]) for gap in gaps] == [
        (10, "net_gini_including_health_benefits")
    ]


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
    published, (published_run, *_), _ = _runs()
    published_run["scenarios"][1][field] += change
    gaps = diagnose.reproduction_gaps(published, published_run)
    assert [(gap["shift_pct"], gap["field"]) for gap in gaps] == [(10, field)]
    assert abs(change) > diagnose.REPRODUCED[kind]


def test_a_state_s_gap_is_reported_and_its_redefined_total_compared_the_old_way():
    published, (published_run, *_), _ = _runs()
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
    published, (published_run, *_), _ = _runs()
    row = published_run["scenarios"][1]
    assert row["total_rev_change_b"] != published["scenarios"][1]["revenue_change_b"]
    assert diagnose.reproduction_gaps(published, published_run) == []


def test_float_noise_is_no_gap():
    published, (published_run, *_), _ = _runs()
    published_run["scenarios"][1]["benefits_change_b"] += 5e-7
    published_run["scenarios"][1]["net_gini"] += 5e-10
    assert diagnose.reproduction_gaps(published, published_run) == []


def test_a_configuration_that_did_not_take_is_reported():
    _, (published_run, medicaid_run, head_start_run), _ = _runs()
    assert diagnose.configuration_problems((published_run, medicaid_run, head_start_run)) == []
    wrong = copy.deepcopy(published_run)
    wrong["metadata"]["policyengine_bundle"]["net_income_excluded_benefits"] = ["head_start"]
    assert diagnose.configuration_problems((wrong, medicaid_run, head_start_run)) == [
        "the published run left ['head_start'] out of net income, not []"
    ]
    assert diagnose.configuration_problems((published_run, published_run, head_start_run)) == [
        "the medicaid_at_baseline run records configuration 'published'",
        "the medicaid_at_baseline run records Medicaid pricing calls "
        "{'baseline': 0, 'own_enrollees': 1, 'other': 0}, not {'baseline': 1, 'own_enrollees': 0, 'other': 0}",
    ]
    assert diagnose.configuration_problems((published_run, medicaid_run, published_run)) == [
        "the head_start_excluded run records configuration 'published'",
        "the head_start_excluded run records Medicaid pricing calls "
        "{'baseline': 0, 'own_enrollees': 1, 'other': 0}, not {'baseline': 1, 'own_enrollees': 0, 'other': 0}",
        "the head_start_excluded run left [] out of net income, not "
        "['early_head_start', 'head_start']",
    ]


def test_a_run_whose_medicaid_pricing_did_not_take_is_reported():
    # Named and excluded right, but it priced its branch over its own enrollees.
    _, runs, _ = _runs()
    runs[1]["metadata"]["diagnose_configuration"]["medicaid_pricing_calls"] = _pricing_calls("own_enrollees")
    assert diagnose.configuration_problems(runs) == [
        "the medicaid_at_baseline run records Medicaid pricing calls "
        "{'baseline': 0, 'own_enrollees': 1, 'other': 0}, not {'baseline': 1, 'own_enrollees': 0, 'other': 0}"
    ]
    # A run that records no count, such as one from before the count existed.
    del runs[1]["metadata"]["diagnose_configuration"]["medicaid_pricing_calls"]
    assert diagnose.configuration_problems(runs) == [
        "the medicaid_at_baseline run records Medicaid pricing calls None, "
        "not {'baseline': 1, 'own_enrollees': 0, 'other': 0}"
    ]
    # The sweep never reached the pricing step.
    runs[1]["metadata"]["diagnose_configuration"]["medicaid_pricing_calls"] = _pricing_calls("baseline", 0)
    assert len(diagnose.configuration_problems(runs)) == 1


def test_a_missing_run_is_reported():
    _, runs, _ = _runs()
    assert diagnose.configuration_problems(runs[:2]) == [
        "2 runs given, not 3: published, medicaid_at_baseline, head_start_excluded"
    ]


def test_field_steps_skip_a_field_a_run_lacks():
    _, runs, rerun = _runs()
    del rerun["scenarios"][1]["benefits_change_b"]
    fields = [row["field"] for row in diagnose.field_steps(runs, rerun)]
    assert "benefits_change_b" not in fields
    assert "net_gini" in fields


def test_field_steps_list_only_fields_a_step_moves():
    rows = diagnose.field_steps(*_runs()[1:])
    assert [row["field"] for row in rows] == [
        "benefits_change_b",
        "net_gini",
        "net_gini_including_health_benefits",
        "revenue_change_b",
        "spm_poverty_rate",
        "total_rev_change_b",
        "total_rev_change_published_definition_b",
    ]
    benefits, health_gini = rows[0], rows[2]
    assert benefits["medicaid_at_baseline"] == 0.0
    assert benefits["head_start"] == pytest.approx(-5.3)
    assert benefits["labor_inputs"] == pytest.approx(-0.8)
    assert health_gini["medicaid_at_baseline"] == pytest.approx(-0.0018)


def _code_step_total(row):
    return sum(row[key] for key, _ in diagnose.CODE_STEPS)


def test_distribution_and_decile_steps_add_up():
    published, runs, rerun = _runs()
    # The published run misses the published Gini with health benefits at 10%.
    runs[0]["scenarios"][1]["net_gini_including_health_benefits"] += 0.001
    for shift_pct in (0, 10):
        rows = diagnose.distribution_steps(published, runs, rerun, shift_pct)
        assert "net_gini_including_health_benefits" in [row["field"] for row in rows]
        for row in rows:
            assert row["published"] + row["reproduction"] + _code_step_total(row) == pytest.approx(row["rerun"])
    health = {row["field"]: row for row in diagnose.distribution_steps(published, runs, rerun, 10)}
    assert health["net_gini_including_health_benefits"]["reproduction"] == pytest.approx(0.001)
    deciles = diagnose.decile_steps(published, runs, rerun)
    assert [row["decile"] for row in deciles] == [1, 2]
    for row in deciles:
        assert row["published"] + row["reproduction"] + _code_step_total(row) == pytest.approx(row["rerun"])


def test_the_report_names_each_step():
    text = diagnose.report(*_runs())
    assert "reproduces every published value" in text
    assert (
        "| Published | Reproduction gap | Medicaid priced at baseline | Head Start left out "
        "| Stored labor inputs | TANF counted once | Health coverage | Rerun |\n"
        "|---:|---:|---:|---:|---:|---:|---:|---:|"
    ) in text
    assert "| -135.30 | +0.00 | +0.00 | +5.30 | +0.80 | +0.20 | -66.20 | -195.20 |" in text
    assert "The steps leave $+0.0000B unexplained." in text
    assert "| Net Gini with health benefits | 0.4520 | +0.0000 | -0.0018 | +0.0036 | -0.0001 | 0.4537 |" in text
    assert (
        "| Field | Published configuration | Medicaid priced at baseline | Head Start left out "
        "| Stored labor inputs | Rerun |\n|---|---:|---:|---:|---:|---:|"
    ) in text
    assert text.count(
        "| Measure | Published | Reproduction gap | Medicaid priced at baseline | Head Start left out "
        "| Stored labor inputs | Rerun |\n|---|---:|---:|---:|---:|---:|---:|"
    ) == 2
    assert (
        "| Decile | Published | Reproduction gap | Medicaid priced at baseline | Head Start left out "
        "| Stored labor inputs | Rerun |\n|---:|---:|---:|---:|---:|---:|---:|"
    ) in text
    assert "It doesn't compare the deciles" in text
    published, runs, rerun = _runs()
    runs[0]["scenarios"][1]["benefits_change_b"] = 20.0
    assert "misses 1 of the published values" in diagnose.report(published, runs, rerun)


def test_every_report_row_has_a_cell_for_each_column():
    tables, rows = 0, 0
    width = None
    for line in diagnose.report(*_runs()).splitlines():
        if not line.startswith("|"):
            width = None
            continue
        cells = line.count("|") - 1
        if width is None:
            width, tables = cells, tables + 1
        else:
            assert cells == width, line
            rows += 1
    # Revenue, field, two distribution and decile tables, each with an alignment row.
    assert tables == 5
    assert rows > 2 * tables


def _report_tables(text):
    """Each table in a report: its column names and its rows' cells."""
    lines = text.splitlines()
    tables = []
    for i, line in enumerate(lines):
        if line.startswith("|") and (i == 0 or not lines[i - 1].startswith("|")):
            rows = []
            for row in lines[i + 2 :]:
                if not row.startswith("|"):
                    break
                rows.append([cell.strip() for cell in row.strip("|").split("|")])
            tables.append(([cell.strip() for cell in line.strip("|").split("|")], rows))
    return tables


def test_every_report_row_adds_up_across_its_cells():
    published, runs, rerun = _runs()
    # Reproduction gaps give the revenue and distribution tables' second column
    # something to add.
    runs[0]["scenarios"][1]["net_gini_including_health_benefits"] += 0.001
    runs[0]["scenarios"][1]["total_rev_change_published_definition_b"] += 1.0
    tables = _report_tables(diagnose.report(published, runs, rerun))
    assert [names[0] for names, _ in tables] == ["Published", "Field", "Measure", "Measure", "Decile"]
    # The revenue table starts from the published total, not the published run's.
    [revenue_row] = tables[0][1]
    assert revenue_row[0] == f"{published['scenarios'][1]['revenue_change_b']:,.2f}"
    assert revenue_row[1] == "+1.00"
    for names, rows in tables:
        assert rows, names
        for row in rows:
            # Every column after a label column is a number; the last is the rerun.
            cells = row[1:] if names[0] in ("Field", "Measure", "Decile") else row
            values = [float(cell.replace(",", "")) for cell in cells]
            digits = max(len(cell.rsplit(".", 1)[1]) for cell in cells)
            # Each cell is rounded to ``digits`` places.
            slack = len(cells) * 0.5 * 10**-digits + 1e-12
            assert math.fsum(values[:-1]) == pytest.approx(values[-1], abs=slack), (names, row)


def test_the_zero_shift_table_starts_from_the_published_zero_shift_values():
    published, runs, rerun = _runs()
    text = diagnose.report(published, runs, rerun)
    zero_table = text.split("Distribution at a 0% shift:")[1].split("Distribution at a 10% shift:")[0]
    ten_table = text.split("Distribution at a 10% shift:")[1]
    zero, ten = published["scenarios"][0], published["scenarios"][1]
    for field, label in diagnose.DISTRIBUTION:
        if zero.get(field) is None:
            continue
        # The fixture gives each shift its own value, so a table that read the
        # other shift's would show it.
        assert zero[field] != ten[field]
        assert f"| {label} | {zero[field]:.4f} |" in zero_table
        assert f"| {label} | {ten[field]:.4f} |" in ten_table


def test_the_published_shift_sets_the_built_labor_variable_alone():
    calls = []

    class Branch:
        def set_input(self, variable, year, values):
            calls.append((variable, year, values))

    # The published code touched no baseline, so a stand-in with no attributes will do.
    result = diagnose._set_built_labor_income_only(object(), Branch(), "employment_income", 2026, [1, 2.5])
    assert result is None
    [(variable, year, values)] = calls
    assert (variable, year) == ("employment_income", 2026)
    assert values.dtype == np.float64
    assert values.tolist() == [1.0, 2.5]


def test_the_report_reads_main_before_this_sweep_by_default(monkeypatch, tmp_path):
    published, runs, rerun = _runs()
    refs = []
    monkeypatch.setattr(diagnose, "_load_old", lambda path, ref: refs.append(ref) or published)
    paths = []
    for name, payload in zip(("rerun", *diagnose.RUNS), (rerun, *runs)):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload))
        paths.append(str(path))
    diagnose.main(["report", *paths])
    assert refs == ["a78aa979a05d5be3028324ff2cc8fe0fd72ed346"]


def _stand_in(monkeypatch, module, **attributes):
    """Put a stand-in module at ``analysis.<module>`` for the test."""
    import analysis

    fake = types.ModuleType(f"analysis.{module}")
    for name, value in attributes.items():
        setattr(fake, name, value)
    monkeypatch.setitem(sys.modules, f"analysis.{module}", fake)
    monkeypatch.setattr(analysis, module, fake, raising=False)
    return fake


class Untouchable:
    def __getattr__(self, name):
        raise AssertionError(f"the published pricing read branch.{name}")


class FakeBranch:
    """A branch whose Medicaid denominator holder answers as core's does.

    ``held`` gives it a denominator before any pricing, as a branch would
    inherit one from a parent that had calculated it. Core stores float
    inputs in float32.
    """

    branch_name = "sweep_10"

    def __init__(self, held=None):
        self.stored = {} if held is None else {2026: np.asarray(held, dtype=np.float32)}

    @property
    def known(self):
        return list(self.stored)

    def set_denominator(self, year, values):
        self.stored[year] = np.asarray(values, dtype=float).astype(np.float32)

    def get_holder(self, variable):
        from analysis import health_tanf

        assert variable == health_tanf.MEDICAID_DENOMINATOR

        def get_array(period, branch_name):
            assert branch_name == self.branch_name
            return self.stored.get(period)

        return types.SimpleNamespace(get_known_periods=lambda: list(self.stored), get_array=get_array)


def _baseline_pricing(priced, scale=1.0):
    """A stand-in for health_tanf.price_medicaid_at_baseline: it stores the denominator.

    ``scale`` other than 1 stores a different denominator from the one passed.
    """

    def pricing(branch, denominator, year):
        branch.set_denominator(year, np.asarray(denominator, dtype=float) * scale)
        priced.append(year)

    return pricing


def test_each_configuration_prices_medicaid_as_its_code_did():
    assert {name: s["medicaid_at_baseline"] for name, s in diagnose.CONFIGURATIONS.items()} == {
        name: kind == "baseline" for name, kind in PRICING.items()
    }


def test_the_configurations_route_and_count_medicaid_pricing(monkeypatch):
    from analysis import health_tanf, policyengine_runtime

    shift = _stand_in(monkeypatch, "labor_capital_shift", set_labor_income=object())
    setter, excluded = shift.set_labor_income, policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS
    priced = []
    baseline_pricing = _baseline_pricing(priced)
    monkeypatch.setattr(health_tanf, "price_medicaid_at_baseline", baseline_pricing)
    with diagnose.configuration("published") as record:
        branch = FakeBranch()
        assert health_tanf.price_medicaid_at_baseline(branch, [1.0], 2026) is None
        assert branch.known == []
        assert record["medicaid_pricing_calls"] == _pricing_calls("own_enrollees")
        assert policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS == ()
        assert shift.set_labor_income is diagnose._set_built_labor_income_only
    assert priced == []
    for name in ("medicaid_at_baseline", "head_start_excluded"):
        with diagnose.configuration(name) as record:
            health_tanf.price_medicaid_at_baseline(FakeBranch(), [1.0], 2026)
            health_tanf.price_medicaid_at_baseline(FakeBranch(), [1.0], 2026)
            assert record["medicaid_pricing_calls"] == _pricing_calls("baseline", 2)
            assert shift.set_labor_income is diagnose._set_built_labor_income_only
            assert policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS == (
                () if name == "medicaid_at_baseline" else excluded
            )
    assert priced == [2026] * 4
    assert health_tanf.price_medicaid_at_baseline is baseline_pricing
    assert policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS == excluded
    assert shift.set_labor_income is setter


def test_a_baseline_pricing_that_sets_nothing_counts_as_own_enrollees(monkeypatch):
    # The count reads the branch, not the configuration, so a baseline pricing
    # that leaves the denominator unset shows up as the wrong kind of call.
    from analysis import health_tanf

    _stand_in(monkeypatch, "labor_capital_shift", set_labor_income=object())
    monkeypatch.setattr(health_tanf, "price_medicaid_at_baseline", lambda branch, denominator, year: None)
    with diagnose.configuration("medicaid_at_baseline") as record:
        health_tanf.price_medicaid_at_baseline(FakeBranch(), [1.0], 2026)
        assert record["medicaid_pricing_calls"] == _pricing_calls("own_enrollees")


def test_a_branch_that_held_a_denominator_before_pricing_counts_as_other(monkeypatch):
    # A branch made from a parent that had calculated the denominator inherits
    # it. The published code would then have priced at that denominator, not
    # over the branch's own enrollees, so the count flags it.
    from analysis import health_tanf

    _stand_in(monkeypatch, "labor_capital_shift", set_labor_income=object())
    monkeypatch.setattr(health_tanf, "price_medicaid_at_baseline", _baseline_pricing([]))
    for name in diagnose.RUNS:
        with diagnose.configuration(name) as record:
            health_tanf.price_medicaid_at_baseline(FakeBranch(held=[1.0]), [1.0], 2026)
            assert record["medicaid_pricing_calls"] == _pricing_calls("other")
    published, runs, _ = _runs()
    runs[0]["metadata"]["diagnose_configuration"]["medicaid_pricing_calls"] = _pricing_calls("other")
    assert diagnose.configuration_problems(runs) == [
        "the published run records Medicaid pricing calls "
        "{'baseline': 0, 'own_enrollees': 0, 'other': 1}, not {'baseline': 0, 'own_enrollees': 1, 'other': 0}"
    ]


def test_a_pricing_that_stores_another_denominator_counts_as_other(monkeypatch):
    from analysis import health_tanf

    _stand_in(monkeypatch, "labor_capital_shift", set_labor_income=object())
    monkeypatch.setattr(health_tanf, "price_medicaid_at_baseline", _baseline_pricing([], scale=2.0))
    with diagnose.configuration("medicaid_at_baseline") as record:
        health_tanf.price_medicaid_at_baseline(FakeBranch(), [1.0, 3.0], 2026)
        assert record["medicaid_pricing_calls"] == _pricing_calls("other")
    # Core keeps the denominator in float32, so the count compares in float32.
    monkeypatch.setattr(health_tanf, "price_medicaid_at_baseline", _baseline_pricing([]))
    with diagnose.configuration("medicaid_at_baseline") as record:
        health_tanf.price_medicaid_at_baseline(FakeBranch(), [0.1, 1e6 / 3], 2026)
        assert record["medicaid_pricing_calls"] == _pricing_calls("baseline")


def test_run_records_how_the_sweep_priced_medicaid(monkeypatch, tmp_path):
    from analysis import health_tanf

    _stand_in(monkeypatch, "labor_capital_shift", set_labor_income=object())
    monkeypatch.setattr(health_tanf, "price_medicaid_at_baseline", _baseline_pricing([]))

    def run_shift_sweep(shift_levels, microdata_output_dir):
        # The real sweep prices each shifted branch once, through the module attribute.
        for pct in shift_levels:
            if pct:
                health_tanf.price_medicaid_at_baseline(FakeBranch(), [1.0], 2026)
        return {"metadata": {}, "scenarios": [{"shift_pct": 0}, {"shift_pct": 10}]}

    _stand_in(monkeypatch, "compute_shift_sweep", run_shift_sweep=run_shift_sweep)
    _stand_in(monkeypatch, "compute_decile_impacts", decile_impacts=lambda folder: {"scenarios": []})
    for name in diagnose.RUNS:
        out = tmp_path / f"{name}.json"
        result = diagnose.run(name, out)
        recorded = result["metadata"]["diagnose_configuration"]
        assert recorded == {"name": name, **diagnose.CONFIGURATIONS[name], "medicaid_pricing_calls": _pricing_calls(PRICING[name])}
        assert json.loads(out.read_text()) == result
        assert not [p for p in diagnose.configuration_problems([result] * 3) if p.startswith(f"the {name} run records Medicaid")]


def test_main_exits_on_the_published_run_and_the_runs_order(monkeypatch, tmp_path, capsys):
    published, runs, rerun = _runs()
    monkeypatch.setattr(diagnose, "_load_old", lambda path, ref: published)
    paths = []
    for name, payload in zip(("rerun", *diagnose.RUNS), (rerun, *runs)):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload))
        paths.append(str(path))
    # The medicaid_at_baseline run misses the Gini with health, as it should;
    # only the published run has to reproduce the published values.
    assert diagnose.main(["report", *paths]) == 0
    assert "reproduces every published value" in capsys.readouterr().out
    assert diagnose.main(["report", paths[0], paths[2], paths[1], paths[3]]) == 1
    assert "Configuration problems:" in capsys.readouterr().out
    runs[0]["scenarios"][1]["net_gini"] += 0.01
    (tmp_path / "published.json").write_text(json.dumps(runs[0]))
    assert diagnose.main(["report", *paths]) == 1


def test_the_configurations_put_back_what_the_published_code_did():
    pytest.importorskip("policyengine_core")
    from analysis import health_tanf, labor_capital_shift, policyengine_runtime

    pricing = health_tanf.price_medicaid_at_baseline
    excluded, setter = policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS, labor_capital_shift.set_labor_income
    for name in diagnose.RUNS:
        with diagnose.configuration(name):
            assert health_tanf.price_medicaid_at_baseline is not pricing
            assert labor_capital_shift.set_labor_income is diagnose._set_built_labor_income_only
    assert health_tanf.price_medicaid_at_baseline is pricing
    assert policyengine_runtime.NET_INCOME_EXCLUDED_BENEFITS == excluded
    assert labor_capital_shift.set_labor_income is setter


def test_the_published_pricing_leaves_the_branch_alone():
    assert diagnose._price_medicaid_over_own_enrollees(Untouchable(), [1.0], 2026) is None
