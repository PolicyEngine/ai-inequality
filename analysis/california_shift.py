"""California's revenue under the labor-to-capital income shift.

Runs the sweep's shift (``labor_capital_shift._apply_shift``) and fiscal
accounting (``fiscal.revenue_components``, ``fiscal.state_revenue_components``)
on whatever PolicyEngine bundle is installed, with one fresh microsimulation
per level, the way ``compute_shift_sweep`` does. On top of the sweep payload it
records:

* California's employee SDI contribution. The sweep's state measure,
  ``household_state_tax_before_refundable_credits``, adds state income tax and
  use tax only, so this wage levy sits outside it.
* California's change split by within-state market-income group, with the
  labor income each group gives up and the capital income it receives.
* Federal net revenue, as the all-government total less every state's net
  change.
* A within-state variant of the shift. The sweep scales every positive
  capital-income dollar in the country by one factor, so a state whose share of
  national capital income exceeds its share of labor income gains market
  income from other states. The variant gives each state's freed labor income
  to that state's own capital holders, in proportion to their holdings, so
  every state's market income stays fixed and only the movement of income
  within each state changes its revenue.
* Health spending and TANF, which the sweep's state measure leaves out
  (``*_with_health_tanf`` fields). Household net income excludes health
  benefits (``gov.simulation.include_health_benefits_in_net_income`` is
  false), so Medicaid, CHIP, the Medicare Savings Programs and ACA premium tax
  credits sit in no government's total, and ``tanf`` sits in
  ``household_benefits`` but in no state's line, so the sweep books it federal.
  These fields charge each state its share of Medicaid, CHIP and Medicare
  Savings Program costs under federal matching rules
  (``state_benefit_cost``, from ``gov.hhs.medicaid.cost_share``), the whole
  cost of coverage it funds alone for people whose immigration status rules
  out federal matching, its own health subsidies, and its whole TANF change,
  because the federal TANF block grant is a fixed amount. The all-government
  total adds every program in ``gov.household.household_health_benefits``;
  federal net revenue is again what the states leave.

Usage:
    python -m analysis.california_shift [--levels 0.1,0.2,0.5,1.0]
        [--within-state-levels 0.1,0.5] [--out PATH]
"""

from __future__ import annotations

import argparse
import gc
import json
import os
from importlib.metadata import PackageNotFoundError, version

import numpy as np

from .constants import CAPITAL_INCOME_VARS, YEAR
from .fiscal import (
    net_fiscal_impact,
    revenue_components,
    state_revenue_components,
    state_revenue_delta,
)
from .policyengine_runtime import managed_us_microsimulation, policyengine_bundle

DEFAULT_LEVELS = [0.10, 0.20, 0.50, 1.00]
DEFAULT_WITHIN_STATE_LEVELS = [0.10, 0.50]
STATE = "CA"
SDI_VARIABLE = "ca_employee_state_disability_insurance_contribution"
LABOR_VARS = ["employment_income", "self_employment_income"]

#: The programs in ``gov.household.household_health_benefits``, by who pays.
#: policyengine-us splits these three between federal and state through
#: ``federal_benefit_cost`` and ``state_benefit_cost``.
FMAP_SPLIT_HEALTH = ("medicaid_cost", "chip", "msp_cost")
#: Federal: ACA premium tax credits, and the Basic Health Program, which
#: federal pass-through funds (95% of the credits enrollees would have
#: received) pay for mostly.
FEDERAL_HEALTH = ("assigned_aca_ptc", "basic_health_program")
#: State-funded health subsidies.
STATE_HEALTH = (
    "assigned_ca_premium_subsidy",
    "co_omnisalud",
    "assigned_co_premium_assistance",
    "md_premium_assistance",
    "assigned_nm_premium_assistance",
    "or_healthier_oregon_cost",
)
#: The members of ``gov.household.federal_benefit_cost`` and
#: ``gov.household.state_benefit_cost`` this accounting expects.
FEDERAL_SHARE_COSTS = ("medicaid_federal_cost", "chip_federal_cost", "msp_federal_cost")
STATE_SHARE_COSTS = ("medicaid_state_cost", "chip_state_cost", "msp_state_cost")
#: Every state TANF program; California's is CalWORKs (``ca_tanf``).
TANF_VARIABLE = "tanf"

#: Within-California groups by baseline household market income, as
#: (label, lower weighted percentile, upper weighted percentile).
GROUPS = [
    ("Bottom 50%", 0.0, 0.5),
    ("50th to 90th percentile", 0.5, 0.9),
    ("90th to 99th percentile", 0.9, 0.99),
    ("Top 1%", 0.99, 1.0000001),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def _package_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _hh(sim, var):
    return np.asarray(sim.calculate(var, map_to="household", period=YEAR), dtype=float)


def _parameters(sim):
    return sim.tax_benefit_system.parameters(f"{YEAR}-01-01")


def _check_health_lists(parameters):
    """Refuse a model whose health accounting differs from what this module classifies.

    The ``*_with_health_tanf`` fields assume health benefits sit outside
    household net income, that every program in
    ``gov.household.household_health_benefits`` has a payer here, and that the
    federal and state benefit-cost lists hold the shares of the same three
    programs.
    """
    gov = parameters.gov
    if gov.simulation.include_health_benefits_in_net_income:
        raise ValueError(
            "health benefits are in household net income, so household_benefits "
            "already counts them; the health accounting would count them twice"
        )
    expected = {
        "household_health_benefits": set(FMAP_SPLIT_HEALTH) | set(FEDERAL_HEALTH) | set(STATE_HEALTH),
        "federal_benefit_cost": set(FEDERAL_SHARE_COSTS),
        "state_benefit_cost": set(STATE_SHARE_COSTS),
    }
    for name, want in expected.items():
        listed = set(getattr(gov.household, name))
        if listed != want:
            raise ValueError(
                f"gov.household.{name} changed: unclassified {sorted(listed - want)}, "
                f"missing {sorted(want - listed)}"
            )


def _federally_eligible_status(status, years_since_entry, p):
    """Whether federal Medicaid can match coverage, given each person's immigration status.

    Mirrors the federal branch of policyengine-us's
    ``is_medicaid_immigration_status_eligible``: citizens, and qualified
    statuses that are exempt from the five-year bar or past it. ``p`` is
    ``gov.hhs.medicaid.eligibility``.
    """
    status = np.asarray(status).astype(str)
    citizen = status == "CITIZEN"
    qualified = np.isin(status, list(p.eligible_immigration_statuses))
    bar_exempt = np.isin(status, list(p.bar_exempt_immigration_statuses))
    past_bar = np.asarray(years_since_entry, dtype=float) >= p.five_year_bar_years
    return citizen | (qualified & (bar_exempt | past_bar))


def _state_only_coverage(sim):
    """Federal share policyengine-us books for coverage only a state pays for, by household.

    ``medicaid_federal_share`` and ``chip_federal_share`` apply federal matching
    rates to every enrollee, including people a state covers whatever their
    immigration status, such as California's Medi-Cal for undocumented, DACA
    and TPS residents. Federal funds pay for such people only in emergencies,
    which ``medicaid_cost`` leaves out, so their whole cost is the state's.
    """
    p = _parameters(sim).gov.hhs.medicaid.eligibility
    status = sim.calculate("immigration_status", period=YEAR, decode_enums=True)
    years = sim.calculate("years_since_us_entry", period=YEAR)
    federal = _federally_eligible_status(np.asarray(status), np.asarray(years), p)
    federal_share = sum(
        np.asarray(sim.calculate(v, period=YEAR), dtype=float) for v in FEDERAL_SHARE_COSTS
    )
    moved = np.where(federal, 0.0, federal_share)
    return np.asarray(sim.map_result(moved, "person", "household"), dtype=float)


def _with_derived(frame):
    """Add the measures built from a frame's stored arrays.

    ``state_health`` is each household's health spending that falls on its
    state and ``federal_health`` the part that falls on the federal
    government; between them they hold every program in
    ``gov.household.household_health_benefits``.
    """
    frame["state_net"] = frame["state_tax"] - frame["state_credits"] - frame["state_benefits"]
    frame["state_health"] = (
        frame["state_health_split"] + frame["state_only_coverage"] + frame["state_health_programs"]
    )
    frame["federal_health"] = (
        frame["federal_health_split"] - frame["state_only_coverage"] + frame["federal_health_other"]
    )
    frame["state_net_with_health_tanf"] = (
        frame["state_net"] - frame["state_health"] - frame["tanf"]
    )
    return frame


def _check_health_split(frame):
    """policyengine-us's federal and state shares must add up to the costs they split."""
    residual = frame["fmap_split_cost"] - frame["federal_health_split"] - frame["state_health_split"]
    worst = float(np.abs(residual).max()) if residual.size else 0.0
    weighted = float((residual * frame["weight"]).sum())
    if worst >= 1.0 or abs(weighted) >= 1e6:
        raise AssertionError(
            "federal_benefit_cost + state_benefit_cost differ from Medicaid, CHIP and "
            f"MSP cost by up to ${worst:,.2f} a household (${weighted:,.0f} weighted)"
        )
    moved = frame["state_only_coverage"]
    if (moved < -1e-6).any() or (moved > frame["federal_health_split"] + 1e-6).any():
        raise AssertionError("state-only coverage moves more than the federal share it comes from")


def _household_frame(sim):
    """Household arrays needed for the California accounting."""
    _check_health_lists(_parameters(sim))
    frame = {
        "state": np.asarray(
            sim.calculate("state_code_str", map_to="household", period=YEAR)
        ).astype(str),
        "weight": np.asarray(sim.calculate("household_weight", period=YEAR), dtype=float),
        "market_income": _hh(sim, "household_market_income"),
        "state_tax": _hh(sim, "household_state_tax_before_refundable_credits"),
        "state_credits": _hh(sim, "household_refundable_state_tax_credits"),
        "state_benefits": _hh(sim, "household_state_benefits"),
        "labor": sum(_hh(sim, v) for v in LABOR_VARS),
        "capital": sum(_hh(sim, v) for v in CAPITAL_INCOME_VARS),
        "federal_health_split": _hh(sim, "federal_benefit_cost"),
        "state_health_split": _hh(sim, "state_benefit_cost"),
        "fmap_split_cost": sum(_hh(sim, v) for v in FMAP_SPLIT_HEALTH),
        "federal_health_other": sum(_hh(sim, v) for v in FEDERAL_HEALTH),
        "state_health_programs": sum(_hh(sim, v) for v in STATE_HEALTH),
        "state_only_coverage": _state_only_coverage(sim),
        "tanf": _hh(sim, TANF_VARIABLE),
    }
    try:
        frame["sdi"] = _hh(sim, SDI_VARIABLE)
    except Exception as exc:  # noqa: BLE001 - record, do not fail the run
        print(f"  {SDI_VARIABLE} unavailable: {exc}", flush=True)
        frame["sdi"] = np.zeros_like(frame["weight"])
    _check_health_split(frame)
    return _with_derived(frame)


def _freed_labor(values, shift_pct):
    """Labor income each record gives up: ``shift_pct`` of its positive amount.

    Matches ``labor_capital_shift._apply_shift``: losses free nothing.
    """
    values = np.asarray(values, dtype=float)
    return np.where(values > 0, values * shift_pct, 0.0)


def _weighted_sum_by(keys, values, weights):
    """Weighted sum of ``values`` for each distinct key, as {key: total}."""
    keys = np.asarray(keys).astype(str)
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    return {str(k): float((values[keys == k] * weights[keys == k]).sum()) for k in np.unique(keys)}


def _within_state_scales(freed_by_state, positive_capital_by_state):
    """Factor on each state's positive capital income that absorbs its freed labor.

    A state that frees no labor income keeps a factor of one. A state that frees
    labor income but holds no positive capital income has nowhere to put it, so
    the shift refuses rather than drop or move those dollars.
    """
    scales = {}
    for state, freed in freed_by_state.items():
        if freed <= 0:
            scales[state] = 1.0
            continue
        capital = positive_capital_by_state.get(state, 0.0)
        if capital <= 0:
            raise ValueError(
                f"{state} frees ${freed:,.0f} of labor income but holds no positive "
                "capital income to receive it"
            )
        scales[state] = 1.0 + freed / capital
    return scales


def _scale_by_state(values, states, scales):
    """Multiply each positive value by its state's factor; leave the rest as they are."""
    values = np.asarray(values, dtype=float)
    states = np.asarray(states).astype(str)
    factor = np.ones_like(values)
    for state, scale in scales.items():
        factor[states == state] = scale
    return np.where(values > 0, values * factor, values)


def _states_for(sim, variable):
    """State code of each record of ``variable``'s entity."""
    entity = sim.tax_benefit_system.variables[variable].entity.key
    return np.asarray(sim.calculate("state_code_str", period=YEAR, map_to=entity)).astype(str)


def _apply_within_state_shift(baseline, branch_name, shift_pct):
    """Branch with each state's freed labor income added to its own capital income.

    The labor cut matches ``labor_capital_shift._apply_shift``: positive
    employment and self-employment income fall by ``shift_pct``. Each state's
    freed total then scales that state's positive capital income, in every
    capital variable by the same factor, so each state's capital income rises by
    exactly what its residents gave up in labor income.

    Returns the branch, the national total freed and the total freed by state.
    """
    branch = baseline.get_branch(branch_name)

    freed_by_state = {}
    total_freed = 0.0
    for var in LABOR_VARS:
        result = baseline.calculate(var, period=YEAR)
        raw = np.asarray(result, dtype=float)
        weights = np.asarray(result.weights, dtype=float)
        cut = _freed_labor(raw, shift_pct)
        branch.set_input(var, YEAR, raw - cut)
        for state, freed in _weighted_sum_by(_states_for(baseline, var), cut, weights).items():
            freed_by_state[state] = freed_by_state.get(state, 0.0) + freed
        total_freed += float((cut * weights).sum())

    capital = {}
    capital_by_state = {}
    for var in CAPITAL_INCOME_VARS:
        result = baseline.calculate(var, period=YEAR)
        raw = np.asarray(result, dtype=float)
        weights = np.asarray(result.weights, dtype=float)
        states = _states_for(baseline, var)
        capital[var] = (raw, states, weights)
        for state, held in _weighted_sum_by(states, np.clip(raw, 0, None), weights).items():
            capital_by_state[state] = capital_by_state.get(state, 0.0) + held

    scales = _within_state_scales(freed_by_state, capital_by_state)
    added_by_state = {}
    for var, (raw, states, weights) in capital.items():
        scaled = _scale_by_state(raw, states, scales)
        branch.set_input(var, YEAR, scaled)
        for state, added in _weighted_sum_by(states, scaled - raw, weights).items():
            added_by_state[state] = added_by_state.get(state, 0.0) + added

    # Rounding in raw * scale - raw grows with the capital a state holds, so the
    # tolerance does too.
    for state, freed in freed_by_state.items():
        added = added_by_state.get(state, 0.0)
        tolerance = 1e-9 * (abs(freed) + capital_by_state.get(state, 0.0)) + 1e-6
        assert abs(added - freed) <= tolerance, (
            f"{state}: capital income rose by {added:,.0f}, labor income fell by {freed:,.0f}"
        )
    return branch, total_freed, freed_by_state


def _weighted_rank(values, weights):
    """Weighted percentile rank (0-1) of each household within its group."""
    order = np.argsort(values, kind="mergesort")
    cum = np.cumsum(weights[order])
    ranks = np.empty_like(cum)
    ranks[order] = (cum - weights[order] / 2) / cum[-1]
    return ranks


def _baseline_concentration(base):
    """Shares of California labor and capital income by market-income group."""
    mask = base["state"] == STATE
    w = base["weight"][mask]
    ranks = _weighted_rank(base["market_income"][mask], w)
    labor = np.clip(base["labor"][mask], 0, None)
    capital = np.clip(base["capital"][mask], 0, None)
    rows = []
    for label, lo, hi in GROUPS:
        g = (ranks >= lo) & (ranks < hi)
        rows.append(
            {
                "group": label,
                "households_m": float(w[g].sum() / 1e6),
                "labor_income_share": float((labor[g] * w[g]).sum() / (labor * w).sum()),
                "capital_income_share": float(
                    (capital[g] * w[g]).sum() / (capital * w).sum()
                ),
                "mean_market_income": float(
                    (base["market_income"][mask][g] * w[g]).sum() / w[g].sum()
                ),
            }
        )
    return {
        "households_m": float(w.sum() / 1e6),
        "labor_income_b": float((base["labor"][mask] * w).sum() / 1e9),
        "capital_income_b": float((base["capital"][mask] * w).sum() / 1e9),
        "state_net_revenue_b": float((base["state_net"][mask] * w).sum() / 1e9),
        "state_tax_before_refundable_credits_b": float(
            (base["state_tax"][mask] * w).sum() / 1e9
        ),
        "sdi_b": float((base["sdi"][mask] * w).sum() / 1e9),
        "state_health_b": float((base["state_health"][mask] * w).sum() / 1e9),
        "state_health_split_b": float((base["state_health_split"][mask] * w).sum() / 1e9),
        "state_only_coverage_b": float((base["state_only_coverage"][mask] * w).sum() / 1e9),
        "state_health_programs_b": float((base["state_health_programs"][mask] * w).sum() / 1e9),
        "tanf_b": float((base["tanf"][mask] * w).sum() / 1e9),
        "state_net_with_health_tanf_b": float(
            (base["state_net_with_health_tanf"][mask] * w).sum() / 1e9
        ),
        "groups": rows,
    }


def _california_rows(base, scen):
    """California's change in total and by baseline market-income group, $B."""
    mask = base["state"] == STATE
    assert np.array_equal(base["state"], scen["state"]), "household order changed"
    w = base["weight"][mask]
    ranks = _weighted_rank(base["market_income"][mask], w)

    def delta(key):
        return (scen[key] - base[key])[mask]

    fields = {
        "labor_income_change_b": delta("labor"),
        "capital_income_change_b": delta("capital"),
        "market_income_change_b": delta("market_income"),
        "state_tax_before_refundable_credits_change_b": delta("state_tax"),
        "state_refundable_credits_change_b": delta("state_credits"),
        "state_benefits_change_b": delta("state_benefits"),
        "state_net_change_b": delta("state_net"),
        "sdi_change_b": delta("sdi"),
        "state_health_change_b": delta("state_health"),
        "state_health_split_change_b": delta("state_health_split"),
        "state_only_coverage_change_b": delta("state_only_coverage"),
        "state_health_programs_change_b": delta("state_health_programs"),
        "tanf_change_b": delta("tanf"),
        "state_net_with_health_tanf_change_b": delta("state_net_with_health_tanf"),
    }

    def total(sel):
        out = {k: float((v[sel] * w[sel]).sum() / 1e9) for k, v in fields.items()}
        out["state_net_including_sdi_change_b"] = (
            out["state_net_change_b"] + out["sdi_change_b"]
        )
        out["state_net_with_health_tanf_including_sdi_change_b"] = (
            out["state_net_with_health_tanf_change_b"] + out["sdi_change_b"]
        )
        return out

    everyone = np.ones_like(w, dtype=bool)
    groups = []
    for label, lo, hi in GROUPS:
        g = (ranks >= lo) & (ranks < hi)
        row = {"group": label}
        row.update(total(g))
        groups.append(row)
    return total(everyone), groups


def _health_tanf_accounting(base, scen, state_net, all_government):
    """Each government's change once health spending and TANF count, $B.

    ``state_net`` ($B by state) and ``all_government`` ($B) follow the sweep:
    ``tanf`` sits in all-government benefits but in no state's line, and health
    spending sits in neither. Here each state also pays its health share
    (``state_health``) and its whole TANF change, the all-government total pays
    every health dollar, and federal net revenue is what the states leave, so
    TANF moves from the federal line to the states'.
    """
    assert np.array_equal(base["state"], scen["state"]), "household order changed"
    w = base["weight"]

    def by_state(key):
        return _weighted_sum_by(base["state"], scen[key] - base[key], w)

    state_health = by_state("state_health")
    tanf = by_state("tanf")
    federal_health = float(((scen["federal_health"] - base["federal_health"]) * w).sum())
    states = {
        code: state_net.get(code, 0.0)
        - (state_health.get(code, 0.0) + tanf.get(code, 0.0)) / 1e9
        for code in set(state_net) | set(state_health) | set(tanf)
    }
    all_states = sum(states.values())
    all_government_with_health = (
        all_government - (federal_health + sum(state_health.values())) / 1e9
    )
    return {
        "health_federal_change_b": federal_health / 1e9,
        "health_state_change_b": sum(state_health.values()) / 1e9,
        "tanf_change_b": sum(tanf.values()) / 1e9,
        "all_government_with_health_change_b": all_government_with_health,
        "all_states_net_with_health_tanf_change_b": all_states,
        "federal_net_with_health_tanf_change_b": all_government_with_health - all_states,
        "other_states_net_with_health_tanf_change_b": all_states - states.get(STATE, 0.0),
        "states_losing_with_health_tanf_count": sum(1 for v in states.values() if v < -0.005),
        "state_net_with_health_tanf_change_b": dict(sorted(states.items())),
    }


def _level_row(branch, freed, pct, base, base_rev, base_states, allocation):
    """Fiscal and California accounting for one shifted branch."""
    rev = revenue_components(branch)
    delta = net_fiscal_impact(rev, base_rev)
    states = state_revenue_delta(state_revenue_components(branch), base_states)
    scen = _household_frame(branch)
    ca_total, ca_groups = _california_rows(base, scen)

    state_net = {code: d["state_net_change"] / 1e9 for code, d in states.items()}
    all_states = sum(state_net.values())
    other_states = all_states - state_net.get(STATE, 0.0)
    gainers = sorted(
        (c for c, v in state_net.items() if v > 0.005), key=lambda c: -state_net[c]
    )
    losers = [c for c, v in state_net.items() if v < -0.005]
    health_tanf = _health_tanf_accounting(base, scen, state_net, delta["total_change"] / 1e9)
    return health_tanf | {
        "shift_pct": int(round(pct * 100)),
        "allocation": allocation,
        "labor_income_moved_b": freed / 1e9,
        "all_government_change_b": delta["total_change"] / 1e9,
        "all_states_net_change_b": all_states,
        "federal_net_change_b": delta["total_change"] / 1e9 - all_states,
        "other_states_net_change_b": other_states,
        "states_gaining": gainers,
        "states_losing_count": len(losers),
        "state_net_change_b": dict(sorted(state_net.items())),
        "national_components_b": {
            k: v / 1e9 for k, v in sorted(delta.items()) if isinstance(v, (int, float))
        },
        "california": ca_total,
        "california_by_group": ca_groups,
    }


def _report(row):
    ca = row["california"]
    print(
        f"{row['shift_pct']:>3}% shift ({row['allocation']}): CA net "
        f"{ca['state_net_change_b']:+.2f}B (with SDI "
        f"{ca['state_net_including_sdi_change_b']:+.2f}B; market income "
        f"{ca['market_income_change_b']:+.1f}B); other states "
        f"{row['other_states_net_change_b']:+.2f}B; federal "
        f"{row['federal_net_change_b']:+.1f}B; all-gov "
        f"{row['all_government_change_b']:+.1f}B",
        flush=True,
    )
    print(
        f"     with health and TANF: CA {ca['state_net_with_health_tanf_change_b']:+.2f}B "
        f"(state health {ca['state_health_change_b']:+.2f}B, of which state-only coverage "
        f"{ca['state_only_coverage_change_b']:+.2f}B; CalWORKs {ca['tanf_change_b']:+.2f}B); "
        f"other states {row['other_states_net_with_health_tanf_change_b']:+.2f}B; federal "
        f"{row['federal_net_with_health_tanf_change_b']:+.1f}B; all-gov "
        f"{row['all_government_with_health_change_b']:+.1f}B",
        flush=True,
    )


def run(
    levels,
    microsim_factory=managed_us_microsimulation,
    verbose=True,
    within_state_levels=None,
):
    # labor_capital_shift imports policyengine_us at module load; importing it
    # here keeps this module's accounting helpers testable without the model.
    from .labor_capital_shift import _apply_shift

    if within_state_levels is None:
        within_state_levels = DEFAULT_WITHIN_STATE_LEVELS

    base_sim = microsim_factory()
    bundle = policyengine_bundle(base_sim)
    base_rev = revenue_components(base_sim)
    base_states = state_revenue_components(base_sim)
    base = _household_frame(base_sim)
    baseline = _baseline_concentration(base)
    del base_sim
    gc.collect()
    if verbose:
        print(
            f"Baseline CA net state revenue ${baseline['state_net_revenue_b']:.1f}B, "
            f"SDI ${baseline['sdi_b']:.1f}B",
            flush=True,
        )

    rows = []
    for pct in levels:
        sim = microsim_factory()
        branch, freed = _apply_shift(sim, f"ca_{int(round(pct * 100))}", pct)
        row = _level_row(branch, freed, pct, base, base_rev, base_states, "national")
        rows.append(row)
        if verbose:
            _report(row)
        del branch, sim
        gc.collect()

    within_rows = []
    for pct in within_state_levels:
        sim = microsim_factory()
        branch, freed, freed_by_state = _apply_within_state_shift(
            sim, f"ca_within_{int(round(pct * 100))}", pct
        )
        row = _level_row(branch, freed, pct, base, base_rev, base_states, "within_state")
        row["labor_income_moved_by_state_b"] = {
            state: value / 1e9 for state, value in sorted(freed_by_state.items())
        }
        within_rows.append(row)
        if verbose:
            _report(row)
        del branch, sim
        gc.collect()

    return {
        "year": YEAR,
        "state": STATE,
        "description": (
            "Positive employment and self-employment income fall by the shift "
            "share; the same weighted total is added to positive capital income "
            "(gains, interest, dividends and rent) in proportion to the capital "
            "income each person already receives. Static, current law, no "
            "behavioral response. State net revenue is state income tax plus use "
            "tax, less refundable state credits and the state benefits in "
            "gov.household.household_state_benefits (for California: SSP, CAPI, "
            "child care subsidies, CVRP, CARE, FERA and three Los Angeles "
            "programs; no Medi-Cal or CalWORKs); California's employee SDI "
            "contribution is reported separately. The *_with_health_tanf fields "
            "also charge each state its share of Medicaid, CHIP and Medicare "
            "Savings Program costs under federal matching rules (state_benefit_cost), "
            "the whole cost of coverage it funds alone for people whose immigration "
            "status rules out federal matching, its own health subsidies (for "
            "California, the Covered California premium subsidy) and its whole TANF "
            "change (CalWORKs for California), since the federal TANF block grant is "
            "fixed; the all-government total adds every program in "
            "gov.household.household_health_benefits. "
            "'levels' allocate the new capital income across the country, as the "
            "published sweep does; 'within_state_levels' give each state's freed "
            "labor income to that state's own capital holders."
        ),
        "metadata": {
            "policyengine_version": bundle.get("policyengine_version")
            or _package_version("policyengine"),
            "policyengine_us_version": bundle.get("model_version")
            or _package_version("policyengine-us"),
            "policyengine_core_version": _package_version("policyengine-core"),
            "certified_data_build_id": bundle.get("certified_data_build_id"),
            "runtime_dataset_uri": bundle.get("runtime_dataset_uri"),
        },
        "baseline_california": baseline,
        "levels": rows,
        "within_state_levels": within_rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--levels",
        default=",".join(str(x) for x in DEFAULT_LEVELS),
        help="Comma-separated shift shares, e.g. 0.1,0.2,0.5,1.0",
    )
    parser.add_argument(
        "--within-state-levels",
        default=",".join(str(x) for x in DEFAULT_WITHIN_STATE_LEVELS),
        help="Shift shares for the within-state variant; empty to skip it",
    )
    parser.add_argument("--out", default=None, help="Output JSON path")
    args = parser.parse_args()
    levels = [float(x) for x in args.levels.split(",") if x.strip()]
    within = [float(x) for x in args.within_state_levels.split(",") if x.strip()]
    result = run(levels, within_state_levels=within)
    out = args.out or os.path.join(
        OUTPUT_DIR,
        f"california_shift_pe{result['metadata']['policyengine_version']}.json",
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Saved {out}", flush=True)


if __name__ == "__main__":
    main()
