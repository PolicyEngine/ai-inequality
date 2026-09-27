"""Invariants of the committed Head Start correction and the paper's stability pair.

``analysis/outputs/ai_scenarios_buildp_published.json`` is the build-p run as
first published, with Head Start and Early Head Start counted in household net
income. ``analysis/outputs/ai_scenarios.json`` is the same runtime and data
with both programs kept out (``NET_INCOME_EXCLUDED_BENEFITS``). The correction
only drops two names from the household benefits list, so for every baseline,
scenario and sensitivity row:

- SPM poverty, market income, every tax and credit cell, and every separately
  reported program are exactly unchanged (neither program is in SPM resources);
- the revenue change moves by exactly minus the change in benefits, and the
  net income change by exactly the change in benefits.

The paper's data-build stability comparison pairs build o with build p as
published, because both count net income the same way; the emitter refuses a
pair that does not.

``analysis/outputs/transfer_detail_buildp_published.json`` is
``compute_transfer_detail.py`` on the published runtime. It is the source of
the correction notes' Head Start amounts, so it must describe the same run as
the published scenario file, and the two programs it itemizes must account for
the whole correction.
"""

import json
import math
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from analysis.emit_paper_values import net_income_accounting

OUTPUTS = Path(__file__).resolve().parents[1] / "outputs"

#: Row fields the correction must not move: scenario definitions, poverty,
#: market income, every tax, payroll and credit line, every separately stored
#: program, and the state rows.
UNCHANGED = (
    "scenario",
    "context",
    "diagnostics",
    "factor_shares",
    "social_security_cap",
    "spm_poverty_rate",
    "market_gini",
    "market_top_10_share",
    "market_top_1_share",
    "market_top_0_1_share",
    "mean_market_income",
    "market_income_change_b",
    "fed_revenue_b",
    "state_revenue_b",
    "household_tax_change_b",
    "fed_income_tax_change_b",
    "fed_main_rates_change_b",
    "fed_capital_gains_tax_change_b",
    "fed_amt_change_b",
    "fed_niit_change_b",
    "payroll_change_b",
    "employee_ss_tax_change_b",
    "employee_medicare_tax_change_b",
    "employer_ss_tax_change_b",
    "employer_medicare_tax_change_b",
    "employer_payroll_change_b",
    "self_employment_tax_change_b",
    "refundable_credits_change_b",
    "eitc_change_b",
    "refundable_ctc_change_b",
    "state_tax_change_b",
    "state_refundable_credits_change_b",
    "state_benefits_change_b",
    "snap_change_b",
    "ssi_change_b",
    "tanf_change_b",
    "wic_change_b",
    "health_benefits_change_b",
    "state_deltas",
)

#: Row fields the correction may move: the benefit total and what follows
#: from it (revenue, net income and every net-income distribution measure).
MAY_CHANGE = (
    "benefits_change_b",
    "total_rev_change_b",
    "net_income_change_b",
    "identity_residual_b",
    "mean_net_income",
    "net_gini",
    "net_gini_including_health_benefits",
    "net_top_10_share",
    "net_top_1_share",
    "net_top_0_1_share",
    "net_bottom_10_share",
    "net_bottom_20_share",
    "decile_shares",
)

#: $B. Row sums are float32 totals over weighted households; the pipeline's
#: own identity residual is about 2e-5 $B.
TOL_B = 1e-4


def _load(name):
    return json.loads((OUTPUTS / name).read_text())


def _rows(doc):
    yield "baseline", doc["baseline"]
    for row in doc["scenarios"]:
        yield row["scenario"]["label"], row
    for group, items in doc.get("sensitivities", {}).items():
        for index, row in enumerate(items):
            yield f"{group}[{index}]", row


def test_correction_moves_only_household_benefits():
    published = _load("ai_scenarios_buildp_published.json")
    corrected = _load("ai_scenarios.json")
    pairs = list(zip(_rows(published), _rows(corrected)))
    assert len(pairs) == len(list(_rows(corrected)))
    for (label, before), (label_after, after) in pairs:
        assert label == label_after
        for key in UNCHANGED:
            if key in before or key in after:
                assert before.get(key) == after.get(key), (label, key)
        if "benefits_change_b" in before:
            d_benefits = after["benefits_change_b"] - before["benefits_change_b"]
            d_revenue = after["total_rev_change_b"] - before["total_rev_change_b"]
            d_net = after["net_income_change_b"] - before["net_income_change_b"]
            assert math.isclose(d_revenue, -d_benefits, abs_tol=TOL_B), label
            assert math.isclose(d_net, d_benefits, abs_tol=TOL_B), label


def test_every_row_field_is_classified():
    """A field added to the outputs has to be declared unchanged or movable."""
    assert not set(UNCHANGED) & set(MAY_CHANGE)
    for name in ("ai_scenarios_buildp_published.json", "ai_scenarios.json"):
        for label, row in _rows(_load(name)):
            unclassified = set(row) - set(UNCHANGED) - set(MAY_CHANGE)
            assert not unclassified, (name, label, sorted(unclassified))


def _rapid(doc, variant):
    for row in doc["scenarios"]:
        scenario = row["scenario"]
        if (
            scenario["name"] == "Rapid"
            and scenario["inequality"] == variant
            and not scenario.get("hold_shares_fixed")
        ):
            return row
    raise KeyError(variant)


def test_published_transfer_detail_is_the_published_run():
    detail = _load("transfer_detail_buildp_published.json")
    published = _load("ai_scenarios_buildp_published.json")
    for key in (
        "policyengine_version",
        "country_model_version",
        "certified_data_build_id",
    ):
        assert detail["metadata"][key] == published["metadata"][key], key
    assert net_income_accounting(detail["metadata"]) == net_income_accounting(
        published["metadata"]
    )
    assert set(detail["scenarios"]) == {"compressive", "proportional", "expansive"}
    for variant, scenario in detail["scenarios"].items():
        assert math.isclose(
            scenario["deltas_b"]["household_benefits"],
            _rapid(published, variant)["benefits_change_b"],
            abs_tol=1e-6,
        ), variant


def test_head_start_programs_account_for_the_whole_correction():
    """The two programs the correction drops are exactly what it removed.

    Baseline: their published totals equal the fall in household net income,
    mean net income times households (households = the transfer detail's net
    income total over the published mean). Rapid variants: their changes equal
    the change the correction made to each benefit total.
    """
    detail = _load("transfer_detail_buildp_published.json")
    published = _load("ai_scenarios_buildp_published.json")
    corrected = _load("ai_scenarios.json")
    totals = detail["baseline_totals"]
    head_start_b = (totals["early_head_start"] + totals["head_start"]) / 1e9
    mean_before = published["baseline"]["mean_net_income"]
    mean_after = corrected["baseline"]["mean_net_income"]
    households = totals["household_net_income"] / mean_before
    fall_b = (mean_before - mean_after) * households / 1e9
    assert math.isclose(head_start_b, fall_b, abs_tol=0.01), (head_start_b, fall_b)
    for variant, scenario in detail["scenarios"].items():
        dropped_b = (
            scenario["deltas_b"]["early_head_start"]
            + scenario["deltas_b"]["head_start"]
        )
        moved_b = (
            _rapid(published, variant)["benefits_change_b"]
            - _rapid(corrected, variant)["benefits_change_b"]
        )
        assert math.isclose(dropped_b, moved_b, abs_tol=TOL_B), (
            variant,
            dropped_b,
            moved_b,
        )


def test_corrected_run_records_the_exclusion_on_the_published_runtime():
    published = _load("ai_scenarios_buildp_published.json")["metadata"]
    corrected = _load("ai_scenarios.json")["metadata"]
    for key in (
        "policyengine_version",
        "country_model_version",
        "certified_data_build_id",
        "certified_data_artifact_sha256",
    ):
        assert published[key] == corrected[key], key
    assert "net_income_excluded_benefits" not in published
    assert corrected["net_income_excluded_benefits"] == [
        "early_head_start",
        "head_start",
    ]


def test_stability_pair_counts_net_income_the_same_way():
    build_o = _load("ai_scenarios_buildo.json")["metadata"]
    build_p_published = _load("ai_scenarios_buildp_published.json")["metadata"]
    corrected = _load("ai_scenarios.json")["metadata"]
    assert net_income_accounting(build_o) == net_income_accounting(build_p_published)
    assert net_income_accounting(build_o) != net_income_accounting(corrected)


NAMES = st.lists(
    st.sampled_from(["head_start", "early_head_start", "wic", "snap"]),
    unique=True,
)


@given(version=st.sampled_from(["1.764.6", "2.2.1"]), names=NAMES, data=st.data())
def test_accounting_key_ignores_order_and_treats_missing_as_empty(version, names, data):
    shuffled = data.draw(st.permutations(names))
    key = net_income_accounting(
        {"country_model_version": version, "net_income_excluded_benefits": names}
    )
    assert key == net_income_accounting(
        {"country_model_version": version, "net_income_excluded_benefits": shuffled}
    )
    if not names:
        assert key == net_income_accounting({"country_model_version": version})


@given(
    a=st.tuples(st.sampled_from(["1.764.6", "2.2.1"]), NAMES),
    b=st.tuples(st.sampled_from(["1.764.6", "2.2.1"]), NAMES),
)
def test_accounting_keys_match_exactly_when_version_and_set_match(a, b):
    key_a = net_income_accounting(
        {"country_model_version": a[0], "net_income_excluded_benefits": a[1]}
    )
    key_b = net_income_accounting(
        {"country_model_version": b[0], "net_income_excluded_benefits": b[1]}
    )
    assert (key_a == key_b) == (a[0] == b[0] and set(a[1]) == set(b[1]))
