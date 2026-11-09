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
  line holds. The published site's federal line keeps those taxes;
  ``federal_net_published_definition_change_b`` reproduces it.
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
  TAFDC in policyengine-us 2.2.1, which later releases drop from that list),
  which the state's line holds and the all-government total counts twice.
  These fields charge each state its share of Medicaid, CHIP and Medicare
  Savings Program costs under federal matching rules
  (``state_benefit_cost``, from ``gov.hhs.medicaid.cost_share``), the whole
  cost of coverage it funds alone for people whose immigration status rules
  out federal matching (CHIP's unborn-child coverage keeps its federal match),
  its own health subsidies, and the TANF change its line doesn't already hold,
  because the federal TANF block grant is a fixed amount. The all-government
  total adds every program in ``healthcare_benefit_value`` and counts TANF
  once; federal net revenue is again what the states and localities leave.
* Medicaid at the baseline's cost per enrollee. policyengine-us spreads each
  state's fixed Medicaid spending over the enrollees in each simulation
  (``medicaid_slcsp_state_denominator``), so on its own a shifted branch that
  adds enrollees cuts every enrollee's cost and keeps the state's total. Each
  branch here takes the baseline's denominator, as policyengine-us's reform
  branches do, so a new enrollee adds cost.

The shift sets ``employment_income`` and ``self_employment_income`` on each
branch, so anything that reads their ``*_before_lsr`` inputs sees pre-shift
earnings. policyengine-us's default TANF earned-income list reads those inputs,
as do Massachusetts's, Montana's and South Carolina's lists, so those states'
TANF benefits respond to the added capital income and not to the wage cut, and
can fall. The TANF, other-states and all-government lines and the study
measure's federal lines miss the response to the wage cut. SNAP's gross
self-employment income reads those inputs too. California's CalWORKs list reads
the shifted variables, so California's line holds the response. The published
sweep's shift (``_apply_shift``) has the same limit.

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
#: State premium subsidies that ``healthcare_benefit_value`` counts and
#: policyengine-us 2.2.1's ``gov.household.household_health_benefits`` leaves
#: out; later releases list them there (PolicyEngine/policyengine-us#9514).
#: Each lowers premiums on top of the federal premium tax credit, and this
#: accounting charges it to the state.
STATE_HEALTH_UNLISTED = (
    "ct_covered_connecticut",
    "ma_connector_care",
    "nj_njhps",
    "vt_premium_assistance",
    "wa_cascade_care_savings",
)
#: policyengine-us's household value of health coverage. Its ``adds`` list
#: every health program, including those ``household_health_benefits`` omits.
HEALTH_VALUE_VARIABLE = "healthcare_benefit_value"
#: Healthier Oregon covers people federal Medicaid can't. Its cost has no
#: enrollment test, and policyengine-us also enrolls Oregon's undocumented
#: residents in Medicaid (``gov.hhs.medicaid.eligibility.undocumented_immigrant``
#: is true for Oregon), so it prices their coverage twice. Their Medicaid cost
#: stays here and their Healthier Oregon cost goes.
HEALTHIER_OREGON = "or_healthier_oregon_cost"
#: The members of ``gov.household.federal_benefit_cost`` and
#: ``gov.household.state_benefit_cost`` this accounting expects.
FEDERAL_SHARE_COSTS = ("medicaid_federal_cost", "chip_federal_cost", "msp_federal_cost")
STATE_SHARE_COSTS = ("medicaid_state_cost", "chip_state_cost", "msp_state_cost")
#: Whether CHIP's From-Conception-to-End-of-Pregnancy option covers a
#: pregnant person. The unborn child is the beneficiary (42 CFR 457.10), so
#: federal CHIP funds match the coverage whatever the parent's immigration
#: status.
FCEP_ELIGIBLE = "is_chip_fcep_eligible_person"
CHIP_ENROLLED = "chip_enrolled"
#: Every state TANF program; California's is CalWORKs (``ca_tanf``).
TANF_VARIABLE = "tanf"
#: Spreads each state's Medicaid spending over that state's enrollees.
MEDICAID_DENOMINATOR = "medicaid_slcsp_state_denominator"
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
    "federal_net_published_definition_change_b keeps them, as the published "
    "site does. Each shifted branch prices Medicaid enrollees at the "
    "baseline's cost per enrollee (the baseline's "
    "medicaid_slcsp_state_denominator), so state Medicaid totals move with "
    "enrollment. The *_with_health_tanf fields "
    "also charge each state its share of Medicaid, CHIP and Medicare "
    "Savings Program costs under federal matching rules (state_benefit_cost), "
    "the whole cost of coverage it funds alone for people whose immigration "
    "status rules out federal matching (CHIP coverage through the "
    "unborn-child option keeps its federal match), its own health subsidies "
    "(for California, the Covered California premium subsidy; Healthier "
    "Oregon only for people not also enrolled in Medicaid) and the TANF "
    "change its line doesn't already hold (CalWORKs for California; "
    "Massachusetts's TAFDC already sits in its state benefits), since the "
    "federal TANF block grant is fixed; the all-government total adds every "
    "program in healthcare_benefit_value and counts TANF once. "
    "The shift sets employment_income and self_employment_income on each "
    "branch, so anything that reads their *_before_lsr inputs sees pre-shift "
    "earnings: the default TANF earned-income list and Massachusetts's, "
    "Montana's and South Carolina's lists, so those states' TANF benefits "
    "respond to the added capital income and not to the wage cut, and can "
    "fall. The TANF, other-states and all-government lines and the study "
    "measure's federal lines miss the response to the wage cut (SNAP's gross "
    "self-employment income reads those inputs too). "
    "California's CalWORKs list reads the shifted variables. "
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


def _parameters(sim):
    return sim.tax_benefit_system.parameters(f"{YEAR}-01-01")


def _check_health_lists(parameters, health_value_programs):
    """Refuse a model whose health accounting differs from what this module classifies.

    The ``*_with_health_tanf`` fields assume health benefits sit outside
    household net income, that every program in
    ``gov.household.household_health_benefits`` and in
    ``healthcare_benefit_value``'s ``adds`` (``health_value_programs``) has a
    payer here, that the federal and state benefit-cost lists hold the shares
    of the same three programs, and that no health program sits in
    ``gov.household.household_state_benefits``, which the state measure already
    nets.
    """
    gov = parameters.gov
    if gov.simulation.include_health_benefits_in_net_income:
        raise ValueError(
            "health benefits are in household net income, so household_benefits "
            "already counts them; the health accounting would count them twice"
        )
    listed_health = set(FMAP_SPLIT_HEALTH) | set(FEDERAL_HEALTH) | set(STATE_HEALTH)
    every_health = listed_health | set(STATE_HEALTH_UNLISTED)
    expected = {
        # Releases after 2.2.1 also list the unlisted state subsidies here.
        "gov.household.household_health_benefits": (
            set(gov.household.household_health_benefits) - set(STATE_HEALTH_UNLISTED),
            listed_health,
        ),
        f"{HEALTH_VALUE_VARIABLE}'s adds": (set(health_value_programs), every_health),
        "gov.household.federal_benefit_cost": (
            set(gov.household.federal_benefit_cost),
            set(FEDERAL_SHARE_COSTS),
        ),
        "gov.household.state_benefit_cost": (
            set(gov.household.state_benefit_cost),
            set(STATE_SHARE_COSTS),
        ),
    }
    for name, (listed, want) in expected.items():
        if listed != want:
            raise ValueError(
                f"{name} changed: unclassified {sorted(listed - want)}, "
                f"missing {sorted(want - listed)}"
            )
    in_state_benefits = every_health & set(gov.household.household_state_benefits)
    if in_state_benefits:
        raise ValueError(
            "gov.household.household_state_benefits lists health programs "
            f"{sorted(in_state_benefits)}, which the health accounting would count twice"
        )


def _tanf_states_in_state_benefits(state_tanf_variables, state_benefits):
    """States whose TANF program ``household_state_benefits`` already lists.

    ``state_tanf_variables`` holds every state TANF program, each named with its
    state's code first (``ca_tanf``, ``ma_tafdc``).
    """
    listed = set(state_benefits)
    return sorted({v.split("_", 1)[0].upper() for v in state_tanf_variables if v in listed})


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


def _state_only_federal_share(federal, shares, fcep):
    """Federal share to move to the state, by person.

    ``federal`` says whether each person's immigration status lets federal
    funds match their coverage, ``shares`` maps each name in
    ``FEDERAL_SHARE_COSTS`` to the federal share policyengine-us books for each
    person, and ``fcep`` says whether CHIP's unborn-child (FCEP) option covers
    each person. For people federal matching can't cover, the Medicaid,
    Medicare Savings Program and CHIP shares move, except CHIP for people the
    FCEP option covers, which federal funds match whatever the parent's status.
    """
    chip = np.where(
        np.asarray(fcep, dtype=bool),
        0.0,
        np.asarray(shares["chip_federal_cost"], dtype=float),
    )
    movable = (
        np.asarray(shares["medicaid_federal_cost"], dtype=float)
        + chip
        + np.asarray(shares["msp_federal_cost"], dtype=float)
    )
    return np.where(np.asarray(federal, dtype=bool), 0.0, movable)


def _state_only_coverage(sim):
    """Federal share policyengine-us books for coverage only a state pays for, by household.

    ``medicaid_federal_share`` and ``chip_federal_share`` apply federal matching
    rates to every enrollee, including people a state covers whatever their
    immigration status, such as California's Medi-Cal for undocumented, DACA
    and TPS residents. Federal law matches only emergency care for such people
    (42 USC 1396b(v)), so this moves their whole federal share to the state.
    If the state totals that ``medicaid_cost`` spreads (KFF and MACPAC totals of
    Medicaid spending) count that federally matched emergency care, the move
    overstates the state's cost by the federal share of their emergency care,
    an amount this accounting can't measure. CHIP's unborn-child coverage keeps
    its federal match (``_state_only_federal_share``).

    This line depends on the immigration status the data assigns, and it doesn't
    estimate California's actual state-only Medi-Cal cost. Microcosm treats
    anyone who reports Medicaid in the CPS as documented, and from 2026
    California's enrollment freeze keeps undocumented adults without existing
    coverage out at every income, so the line stays small and only the groups
    the freeze exempts can enter it.
    """
    p = _parameters(sim).gov.hhs.medicaid.eligibility
    status = sim.calculate("immigration_status", period=YEAR, decode_enums=True)
    years = sim.calculate("years_since_us_entry", period=YEAR)
    federal = _federally_eligible_status(np.asarray(status), np.asarray(years), p)
    shares = {v: np.asarray(sim.calculate(v, period=YEAR), dtype=float) for v in FEDERAL_SHARE_COSTS}
    fcep = np.asarray(sim.calculate(FCEP_ELIGIBLE, period=YEAR), dtype=bool) & np.asarray(
        sim.calculate(CHIP_ENROLLED, period=YEAR), dtype=bool
    )
    moved = _state_only_federal_share(federal, shares, fcep)
    return np.asarray(sim.map_result(moved, "person", "household"), dtype=float)


def _healthier_oregon_overlap(sim):
    """Healthier Oregon cost for people policyengine-us also enrolls in Medicaid, by household."""
    cost = np.asarray(sim.calculate(HEALTHIER_OREGON, period=YEAR), dtype=float)
    enrolled = np.asarray(sim.calculate("medicaid_enrolled", period=YEAR), dtype=bool)
    return np.asarray(
        sim.map_result(np.where(enrolled, cost, 0.0), "person", "household"), dtype=float
    )


def _adds(sim, variable):
    """The variables ``variable`` adds, from its list or the parameter it names."""
    adds = sim.tax_benefit_system.variables[variable].adds
    if isinstance(adds, str):
        node = _parameters(sim)
        for part in adds.split("."):
            node = getattr(node, part)
        adds = node
    return list(adds)


def _with_derived(frame):
    """Add the measures built from a frame's stored arrays.

    ``state_health`` is each household's health spending that falls on its
    state and ``federal_health`` the part that falls on the federal
    government; between them they hold every program in
    ``healthcare_benefit_value`` once. ``tanf_charge`` is the TANF its state's
    line doesn't already hold. ``state_payroll_tax`` and ``local_tax`` are the
    taxes the all-government total counts outside every state's line.
    """
    frame["state_net"] = frame["state_tax"] - frame["state_credits"] - frame["state_benefits"]
    frame["state_health"] = (
        frame["state_health_split"] + frame["state_only_coverage"] + frame["state_health_programs"]
    )
    frame["federal_health"] = (
        frame["federal_health_split"] - frame["state_only_coverage"] + frame["federal_health_other"]
    )
    frame["tanf_charge"] = frame["tanf"] - frame["tanf_in_state_benefits"]
    frame["state_net_with_health_tanf"] = (
        frame["state_net"] - frame["state_health"] - frame["tanf_charge"]
    )
    frame["state_payroll_tax"] = sum(frame[v] for v in STATE_PAYROLL_TAXES)
    frame["local_tax"] = sum(frame[v] for v in LOCAL_TAXES)
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
    # Imported here, as in run(), so the accounting helpers load without the model.
    from policyengine_us.variables.gov.hhs.tanf.cash.tanf_if_takes_up import (
        STATE_TANF_VARIABLES,
    )

    parameters = _parameters(sim)
    _check_health_lists(parameters, _adds(sim, HEALTH_VALUE_VARIABLE))
    state = np.asarray(sim.calculate("state_code_str", map_to="household", period=YEAR)).astype(str)
    tanf = _hh(sim, TANF_VARIABLE)
    tanf_states = _tanf_states_in_state_benefits(
        STATE_TANF_VARIABLES, parameters.gov.household.household_state_benefits
    )
    overlap = _healthier_oregon_overlap(sim)
    frame = {
        "state": state,
        "weight": np.asarray(sim.calculate("household_weight", period=YEAR), dtype=float),
        "market_income": _hh(sim, "household_market_income"),
        "state_tax": _hh(sim, "household_state_tax_before_refundable_credits"),
        # Both sit inside state_tax: use tax beside income tax, and California's
        # 1% tax on taxable income above $1 million inside its income tax.
        "state_use_tax": _hh(sim, "state_use_tax"),
        "mental_health_services_tax": _hh(sim, "ca_mental_health_services_tax"),
        "state_credits": _hh(sim, "household_refundable_state_tax_credits"),
        "state_benefits": _hh(sim, "household_state_benefits"),
        "labor": sum(_hh(sim, v) for v in LABOR_VARS),
        "capital": sum(_hh(sim, v) for v in CAPITAL_INCOME_VARS),
        "federal_health_split": _hh(sim, "federal_benefit_cost"),
        "state_health_split": _hh(sim, "state_benefit_cost"),
        "fmap_split_cost": sum(_hh(sim, v) for v in FMAP_SPLIT_HEALTH),
        "federal_health_other": sum(_hh(sim, v) for v in FEDERAL_HEALTH),
        "state_health_programs": sum(_hh(sim, v) for v in STATE_HEALTH + STATE_HEALTH_UNLISTED)
        - overlap,
        "healthier_oregon_overlap": overlap,
        "state_only_coverage": _state_only_coverage(sim),
        "tanf": tanf,
        "tanf_in_state_benefits": np.where(np.isin(state, tanf_states), tanf, 0.0),
    }
    for variable in OTHER_TAX_VARIABLES:
        frame[variable] = _hh(sim, variable)
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
    program ``household_state_benefits`` also lists, which sits in its state's
    line and twice in the all-government total; health spending sits in
    neither. Here each state also pays its health share (``state_health``) and
    the TANF change its line doesn't already hold, the all-government total
    pays every health dollar and counts TANF once, and federal net revenue is
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
    counted_twice = total("tanf_in_state_benefits")
    states = {
        code: state_net.get(code, 0.0)
        - (state_health.get(code, 0.0) + tanf_charge.get(code, 0.0)) / 1e9
        for code in set(state_net) | set(state_health) | set(tanf_charge)
    }
    all_states = sum(states.values())
    all_government_with_health = (
        all_government - (federal_health + sum(state_health.values()) - counted_twice) / 1e9
    )
    outside = _outside_state_measure(base, scen)
    return {
        "health_federal_change_b": federal_health / 1e9,
        "health_state_change_b": sum(state_health.values()) / 1e9,
        "healthier_oregon_overlap_change_b": total("healthier_oregon_overlap") / 1e9,
        "tanf_change_b": total("tanf") / 1e9,
        "tanf_counted_twice_change_b": counted_twice / 1e9,
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
        # The published site's federal line: all governments less the states.
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
    """Each person's ``medicaid_slcsp_state_denominator`` in ``sim``."""
    return np.asarray(sim.calculate(MEDICAID_DENOMINATOR, period=YEAR), dtype=float)


def _price_medicaid_at_baseline(branch, denominator):
    """Price a shifted branch's Medicaid enrollees at the baseline's cost per enrollee.

    ``medicaid_cost_if_enrolled`` is the state's spending times the person's
    cost index over ``medicaid_slcsp_state_denominator``, the weighted sum of
    the cost indices of the state's enrollees in the same simulation. Left to
    itself, a branch that adds enrollees raises its own denominator, so every
    enrollee's cost falls and the state's total stays fixed. With the
    baseline's denominator, each enrollee costs what an enrollee with that cost
    index costs in the baseline, so the total moves with enrollment, as in
    policyengine-us's reform branches.
    """
    if branch.get_holder(MEDICAID_DENOMINATOR).get_known_periods():
        raise RuntimeError(
            f"{MEDICAID_DENOMINATOR} is already calculated in this branch; set the "
            "baseline's before calculating anything that depends on it"
        )
    branch.set_input(MEDICAID_DENOMINATOR, YEAR, np.asarray(denominator, dtype=float))


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
