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
* Federal net revenue: the all-government total less every state's net
  change and less the state payroll taxes (``STATE_PAYROLL_TAXES``) and local
  taxes (``LOCAL_TAXES``) that the all-government total counts but no state's
  line holds. ``federal_net_published_definition_change_b`` keeps those
  taxes: it is the all-government total less every state's net change, the
  split ``california_summary`` applies to the published sweep. The site's
  federal chart instead adds up its own bands, so its payroll band holds
  employers' state and local payroll taxes, and it leaves out workers' state
  payroll taxes, the Additional Medicare Tax,
  ``local_income_tax_before_refundable_credits`` and ``local_occupational_tax``.
  New York City's and Maryland's local income taxes sit in those states'
  income tax.
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
  false), so Medicaid, CHIP, the Medicare Savings Programs, ACA premium tax
  credits and state premium subsidies sit in no government's total. ``tanf``
  sits in ``household_benefits`` but in no state's line, so the sweep books it
  federal; the exception is a state whose program
  ``gov.household.household_state_benefits`` also lists (Massachusetts's
  TAFDC in policyengine-us 2.2.1, which later releases drop from that list).
  That list holds the program at its full amount for every eligible family,
  and ``tanf`` adds it again for families that take TANF up. These fields
  charge each state its share of Medicaid, CHIP and Medicare Savings Program
  costs under federal matching rules (``state_benefit_cost``, from
  ``gov.hhs.medicaid.cost_share``), the federal share policyengine-us books
  for people whose immigration status rules out federal matching (federal
  funds still match their emergency care, so this overstates the state's
  cost; CHIP's unborn-child coverage keeps its federal match), its own health
  subsidies, and its TANF change beyond the copy its line holds, because
  federal law fixes each state's TANF block grant. The all-government total
  adds every program in ``healthcare_benefit_value`` and counts TANF once, as
  ``tanf`` pays it; federal net revenue is again what the states and
  localities leave.
* Medicaid at the baseline's cost per enrollee. policyengine-us spreads each
  state's fixed Medicaid spending over the enrollees in each simulation
  (``medicaid_slcsp_state_denominator``), so on its own a shifted branch that
  adds enrollees cuts every enrollee's cost and keeps the state's total. Each
  branch here takes the baseline's denominator, as policyengine-us's reform
  branches do, so a new enrollee adds cost.

Both shifts set each labor variable's stored ``*_before_lsr`` input along with
the variable (``labor_inputs.set_labor_income``), so the formulas that read the
stored inputs see the wage cut: policyengine-us's default TANF earned-income
list, Massachusetts's, Montana's and South Carolina's TANF lists, and SNAP's
self-employment income. Runs before that change set only the variables, so
those programs saw pre-shift earnings; California's CalWORKs list reads the
variables, so California's line never had that gap. The health and TANF
accounting lives in ``health_tanf``, which the published sweep shares.

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

from . import health_tanf
from .constants import CAPITAL_INCOME_VARS, YEAR
from .fiscal import (
    net_fiscal_impact,
    revenue_components,
    state_revenue_components,
    state_revenue_delta,
)
from .labor_inputs import set_labor_income
from .policyengine_runtime import managed_us_microsimulation, policyengine_bundle

DEFAULT_LEVELS = [0.10, 0.20, 0.50, 1.00]
DEFAULT_WITHIN_STATE_LEVELS = [0.10, 0.50]
STATE = "CA"
SDI_VARIABLE = "ca_employee_state_disability_insurance_contribution"
LABOR_VARS = ["employment_income", "self_employment_income"]

#: Taxes the all-government total counts that go to states and localities but
#: sit outside the sweep's state measure: payroll taxes such as California's
#: SDI withholding and state unemployment insurance, and city wage taxes.
STATE_PAYROLL_TAXES = ("employee_state_payroll_tax", "employer_state_payroll_tax")
LOCAL_TAXES = (
    "local_income_tax_before_refundable_credits",
    "local_occupational_tax",
    "employer_local_payroll_tax",
)
#: Federal payroll taxes that ``fiscal.revenue_components`` doesn't list,
#: which the summary's federal split needs to add up.
FEDERAL_PAYROLL_UNLISTED = ("additional_medicare_tax", "employer_federal_unemployment_tax")
#: The taxes above, kept by variable in each household frame.
OTHER_TAX_VARIABLES = STATE_PAYROLL_TAXES + LOCAL_TAXES + FEDERAL_PAYROLL_UNLISTED

#: Within-California groups by baseline household market income, as
#: (label, lower weighted percentile, upper weighted percentile).
GROUPS = [
    ("Bottom 50%", 0.0, 0.5),
    ("50th to 90th percentile", 0.5, 0.9),
    ("90th to 99th percentile", 0.9, 0.99),
    ("Top 1%", 0.99, 1.0000001),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")

#: What a run measures, saved with its output.
RUN_DESCRIPTION = (
    "Positive employment and self-employment income fall by the shift "
    "share; the same weighted total is added to positive capital income "
    "(gains, interest, dividends and rent) in proportion to the capital "
    "income each person already receives. Static, current law, no "
    "behavioral response. State net revenue is state income tax plus use "
    "tax, less refundable state credits and the state benefits in "
    "gov.household.household_state_benefits (for California: SSP, CAPI, "
    "child care subsidies, CVRP, CARE, FERA and three Los Angeles "
    "programs; no Medi-Cal or CalWORKs); California's employee SDI "
    "contribution is reported separately. Federal net revenue is the "
    "all-government change less every state's net change and less state "
    "payroll taxes (employee and employer) and local taxes, which the "
    "all-government total counts but no state's line holds; "
    "federal_net_published_definition_change_b keeps them (all governments "
    "less the states). Each shifted branch prices Medicaid enrollees at the "
    "baseline's cost per enrollee (the baseline's "
    "medicaid_slcsp_state_denominator), so state Medicaid totals move with "
    "enrollment. The *_with_health_tanf fields "
    "also charge each state its share of Medicaid, CHIP and Medicare "
    "Savings Program costs under federal matching rules (state_benefit_cost), "
    "the whole cost of coverage it funds alone for people whose immigration "
    "status rules out federal matching (CHIP coverage through the "
    "unborn-child option keeps its federal match), its own health programs "
    "that healthcare_benefit_value prices (California's Covered California "
    "premium subsidy from policyengine-us 2.x, which 1.764.6 doesn't model; "
    "Healthier Oregon only for people not also enrolled in Medicaid) and the TANF "
    "change its line doesn't already hold (CalWORKs for California; "
    "Massachusetts's TAFDC already sits in its state benefits), since the "
    "federal TANF block grant is fixed; the all-government total adds every "
    "program in healthcare_benefit_value and counts TANF once. "
    "The shift sets employment_income and self_employment_income and their "
    "stored *_before_lsr inputs, so the TANF and SNAP formulas that read the "
    "stored inputs see the wage cut. "
    "'levels' allocate the new capital income across the country, as the "
    "published sweep does; 'within_state_levels' give each state's freed "
    "labor income to that state's own capital holders."
)


def _package_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _hh(sim, var):
    return np.asarray(sim.calculate(var, map_to="household", period=YEAR), dtype=float)


def _with_derived(frame):
    """Add the measures built from a frame's stored arrays.

    ``health_tanf.with_derived`` adds each household's health spending by payer
    (``state_health``, ``federal_health``, ``health_total``) and the TANF its
    state's line doesn't already hold (``tanf_charge``). ``state_net`` is the
    sweep's state measure before health and TANF, ``state_net_with_health_tanf``
    also nets those, and ``state_payroll_tax`` and ``local_tax`` are the taxes
    the all-government total counts outside every state's line.
    """
    health_tanf.with_derived(frame)
    frame["state_net"] = frame["state_tax"] - frame["state_credits"] - frame["state_benefits"]
    frame["state_net_with_health_tanf"] = (
        frame["state_net"] - frame["state_health"] - frame["tanf_charge"]
    )
    frame["state_payroll_tax"] = sum(frame[v] for v in STATE_PAYROLL_TAXES)
    frame["local_tax"] = sum(frame[v] for v in LOCAL_TAXES)
    return frame


def _household_frame(sim):
    """Household arrays needed for the California accounting.

    The health and TANF arrays come from ``health_tanf.household_frame``, which
    also checks policyengine-us's health lists and the frame's sums.
    """
    frame = health_tanf.household_frame(sim, YEAR)
    frame.update(
        {
            "market_income": _hh(sim, "household_market_income"),
            "state_tax": _hh(sim, "household_state_tax_before_refundable_credits"),
            # Both sit inside state_tax: use tax beside income tax, and
            # California's 1% tax on taxable income above $1 million inside its
            # income tax.
            "state_use_tax": _hh(sim, "state_use_tax"),
            "mental_health_services_tax": _hh(sim, "ca_mental_health_services_tax"),
            "state_credits": _hh(sim, "household_refundable_state_tax_credits"),
            "state_benefits": _hh(sim, "household_state_benefits"),
            "labor": sum(_hh(sim, v) for v in LABOR_VARS),
            "capital": sum(_hh(sim, v) for v in CAPITAL_INCOME_VARS),
        }
    )
    for variable in OTHER_TAX_VARIABLES:
        frame[variable] = _hh(sim, variable)
    try:
        frame["sdi"] = _hh(sim, SDI_VARIABLE)
    except Exception as exc:  # noqa: BLE001 - record, do not fail the run
        print(f"  {SDI_VARIABLE} unavailable: {exc}", flush=True)
        frame["sdi"] = np.zeros_like(frame["weight"])
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
    employment and self-employment income fall by ``shift_pct``, in the
    variables and their stored ``*_before_lsr`` inputs. Each state's
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
        set_labor_income(baseline, branch, var, YEAR, raw - cut)
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
        "state_payroll_tax_b": float((base["state_payroll_tax"][mask] * w).sum() / 1e9),
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
        "state_use_tax_change_b": delta("state_use_tax"),
        "mental_health_services_tax_change_b": delta("mental_health_services_tax"),
        "state_refundable_credits_change_b": delta("state_credits"),
        "state_benefits_change_b": delta("state_benefits"),
        "state_net_change_b": delta("state_net"),
        "sdi_change_b": delta("sdi"),
        "state_health_change_b": delta("state_health"),
        "state_health_split_change_b": delta("state_health_split"),
        "state_only_coverage_change_b": delta("state_only_coverage"),
        "state_health_programs_change_b": delta("state_health_programs"),
        # TANF the state's line doesn't already hold: for California, CalWORKs.
        "tanf_change_b": delta("tanf_charge"),
        "state_net_with_health_tanf_change_b": delta("state_net_with_health_tanf"),
        "state_payroll_tax_change_b": delta("state_payroll_tax"),
        "local_tax_change_b": delta("local_tax"),
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


def _outside_state_measure(base, scen):
    """Changes in taxes the all-government total counts outside every state's line, $B."""
    assert np.array_equal(base["state"], scen["state"]), "household order changed"
    w = base["weight"]

    def total(key):
        return float(((scen[key] - base[key]) * w).sum()) / 1e9

    return {
        "state_payroll_tax_change_b": total("state_payroll_tax"),
        "local_tax_change_b": total("local_tax"),
    }


def _other_tax_components_b(base, scen):
    """National change in each of ``OTHER_TAX_VARIABLES``, $B, keyed as ``fiscal`` keys its deltas."""
    w = base["weight"]
    return {
        f"{v}_change": float(((scen[v] - base[v]) * w).sum()) / 1e9 for v in OTHER_TAX_VARIABLES
    }


def _health_tanf_accounting(base, scen, state_net, all_government):
    """Each government's change once health spending and TANF count, $B.

    ``state_net`` ($B by state) and ``all_government`` ($B) follow the sweep:
    ``tanf`` sits in all-government benefits but in no state's line, except a
    program ``household_state_benefits`` also lists: that list holds it, in
    its state's line and the all-government total, at its full amount for
    every eligible family, and ``tanf`` adds it again for families that take
    TANF up. Health spending sits in neither. Here each state also pays its
    health share (``state_health``) and its TANF change beyond the copy its
    line holds, the all-government total pays every health dollar and counts
    TANF once, as ``tanf`` pays it, and federal net revenue is
    what the states and localities leave, so TANF moves from the federal line to
    the states'.
    """
    assert np.array_equal(base["state"], scen["state"]), "household order changed"
    w = base["weight"]

    def by_state(key):
        return _weighted_sum_by(base["state"], scen[key] - base[key], w)

    def total(key):
        return float(((scen[key] - base[key]) * w).sum())

    state_health = by_state("state_health")
    tanf_charge = by_state("tanf_charge")
    federal_health = total("federal_health")
    tanf_copy = total("tanf_in_state_benefits")
    states = {
        code: state_net.get(code, 0.0)
        - (state_health.get(code, 0.0) + tanf_charge.get(code, 0.0)) / 1e9
        for code in set(state_net) | set(state_health) | set(tanf_charge)
    }
    all_states = sum(states.values())
    all_government_with_health = (
        all_government - (federal_health + sum(state_health.values()) - tanf_copy) / 1e9
    )
    outside = _outside_state_measure(base, scen)
    return {
        "health_federal_change_b": federal_health / 1e9,
        "health_state_change_b": sum(state_health.values()) / 1e9,
        "healthier_oregon_overlap_change_b": total("healthier_oregon_overlap") / 1e9,
        "tanf_change_b": total("tanf") / 1e9,
        # The copy of TANF in household_state_benefits, under the name the
        # committed outputs and california_summary use.
        "tanf_counted_twice_change_b": tanf_copy / 1e9,
        "all_government_with_health_change_b": all_government_with_health,
        "all_states_net_with_health_tanf_change_b": all_states,
        "federal_net_with_health_tanf_change_b": all_government_with_health
        - all_states
        - outside["state_payroll_tax_change_b"]
        - outside["local_tax_change_b"],
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
    all_government = delta["total_change"] / 1e9
    outside = _outside_state_measure(base, scen)
    health_tanf = _health_tanf_accounting(base, scen, state_net, all_government)
    components = {k: v / 1e9 for k, v in sorted(delta.items()) if isinstance(v, (int, float))}
    components.update(_other_tax_components_b(base, scen))
    return health_tanf | outside | {
        "shift_pct": int(round(pct * 100)),
        "allocation": allocation,
        "labor_income_moved_b": freed / 1e9,
        "all_government_change_b": all_government,
        "all_states_net_change_b": all_states,
        "federal_net_change_b": all_government
        - all_states
        - outside["state_payroll_tax_change_b"]
        - outside["local_tax_change_b"],
        # All governments less the states, the split california_summary
        # applies to the published sweep.
        "federal_net_published_definition_change_b": all_government - all_states,
        "other_states_net_change_b": other_states,
        "states_gaining": gainers,
        "states_losing_count": len(losers),
        "state_net_change_b": dict(sorted(state_net.items())),
        "national_components_b": dict(sorted(components.items())),
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
        f"{row['federal_net_change_b']:+.1f}B; state payroll "
        f"{row['state_payroll_tax_change_b']:+.2f}B; local {row['local_tax_change_b']:+.2f}B; "
        f"all-gov {row['all_government_change_b']:+.1f}B",
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


def _medicaid_denominator(sim):
    """``health_tanf.medicaid_denominator`` for this module's year."""
    return health_tanf.medicaid_denominator(sim, YEAR)


def _price_medicaid_at_baseline(branch, denominator):
    """``health_tanf.price_medicaid_at_baseline`` for this module's year."""
    health_tanf.price_medicaid_at_baseline(branch, denominator, YEAR)


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
    medicaid_denominator = _medicaid_denominator(base_sim)
    programs = health_tanf.programs_metadata(base_sim, YEAR)
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
        _price_medicaid_at_baseline(branch, medicaid_denominator)
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
        _price_medicaid_at_baseline(branch, medicaid_denominator)
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
        "description": RUN_DESCRIPTION,
        "metadata": {
            "policyengine_version": bundle.get("policyengine_version")
            or _package_version("policyengine"),
            "policyengine_us_version": bundle.get("model_version")
            or _package_version("policyengine-us"),
            "policyengine_core_version": _package_version("policyengine-core"),
            "certified_data_build_id": bundle.get("certified_data_build_id"),
            "runtime_dataset_uri": bundle.get("runtime_dataset_uri"),
            # Runs before this flag set only the built labor variables, so
            # formulas reading the stored *_before_lsr inputs missed the cut.
            "sets_stored_labor_inputs": True,
            # The programs the *_with_health_tanf fields net, by who pays.
            "health_tanf_programs": programs,
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
