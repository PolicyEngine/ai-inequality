"""Health coverage and TANF in the study's revenue lines.

policyengine-us keeps health coverage out of household net income while
``gov.simulation.include_health_benefits_in_net_income`` is false: its
``household_health_benefits`` returns zero, so ``household_benefits``, and the
revenue lines ``fiscal`` builds from it, count no Medicaid, CHIP, Medicare
Savings Program, ACA premium tax credit or state health program. ``tanf`` sits
in ``household_benefits`` but in no state's line, apart from a state TANF
program that ``gov.household.household_state_benefits`` also lists
(Massachusetts's TAFDC at policyengine-us 1.764.6 and 2.2.1).
``household_benefits`` adds that program through ``tanf`` for families that
take TANF up (``takes_up_tanf_if_eligible``) and through
``household_state_benefits`` for every eligible family. The totals that count
health and TANF drop the second copy (``tanf_in_state_benefits``), so each
family's TANF counts once, as ``tanf`` pays it.

This module prices each household's coverage with policyengine-us's
``healthcare_benefit_value`` and splits it between the federal government and
the household's state:

* Medicaid, CHIP and the Medicare Savings Programs follow federal matching
  rules (``federal_benefit_cost`` and ``state_benefit_cost``, which
  policyengine-us builds from ``gov.hhs.medicaid.cost_share``). We also charge
  the state the federal share policyengine-us books for enrollees whose
  immigration status bars federal matching (42 USC 1396b(v)). Federal funds
  still match their emergency care, which this accounting can't separate, so
  the charge overstates the state's cost. CHIP coverage through the
  unborn-child option keeps its federal match (42 CFR 457.10).
* The federal government pays ACA premium tax credits and the Basic Health
  Program.
* The state pays its own health programs: Colorado's OmniSalud and Healthier
  Oregon at policyengine-us 1.764.6, and the state premium subsidies that later
  releases model. Healthier Oregon counts only for people policyengine-us
  doesn't also enroll in Medicaid, because it prices their coverage in both.

Federal law fixes each state's TANF block grant, so we charge every TANF change
to the states, and each TANF dollar counts once.

policyengine-us spreads each state's fixed Medicaid spending over the
enrollees in each simulation (``medicaid_slcsp_state_denominator``). Left to
itself, a branch that adds enrollees cuts every enrollee's cost and keeps the
state's total. ``price_medicaid_at_baseline`` gives a branch the baseline's
denominator, as policyengine-us's reform branches do, so each new enrollee adds
the baseline's cost per enrollee.

The helpers take a simulation and a year and import nothing from
policyengine-us, so they load without the model.
"""

from __future__ import annotations

import sys

import numpy as np

#: policyengine-us's household value of health coverage. Its ``adds`` list
#: every health program the model prices.
HEALTH_VALUE_VARIABLE = "healthcare_benefit_value"
#: Programs whose cost ``federal_benefit_cost`` and ``state_benefit_cost``
#: split between the federal government and the states.
FMAP_SPLIT_HEALTH = ("medicaid_cost", "chip", "msp_cost")
#: Federal programs: ACA premium tax credits, and the Basic Health Program,
#: which federal pass-through funds (95% of the credits enrollees would have
#: received) mostly pay for.
FEDERAL_HEALTH = ("assigned_aca_ptc", "basic_health_program")
#: State health programs across policyengine-us releases. 1.764.6 models
#: OmniSalud and Healthier Oregon; later releases add the premium subsidies.
STATE_HEALTH = (
    "assigned_ca_premium_subsidy",
    "co_omnisalud",
    "assigned_co_premium_assistance",
    "md_premium_assistance",
    "assigned_nm_premium_assistance",
    "or_healthier_oregon_cost",
    "ct_covered_connecticut",
    "ma_connector_care",
    "nj_njhps",
    "vt_premium_assistance",
    "wa_cascade_care_savings",
)
#: Names ``gov.household.household_health_benefits`` uses at 1.764.6 for
#: programs ``healthcare_benefit_value`` adds under the name they add:
#: ``medicaid`` adds ``medicaid_cost`` and ``premium_tax_credit`` adds
#: ``assigned_aca_ptc``.
HEALTH_LIST_ALIASES = {"medicaid": "medicaid_cost", "premium_tax_credit": "assigned_aca_ptc"}
#: The members of ``gov.household.federal_benefit_cost`` and
#: ``gov.household.state_benefit_cost`` this accounting expects.
FEDERAL_SHARE_COSTS = ("medicaid_federal_cost", "chip_federal_cost", "msp_federal_cost")
STATE_SHARE_COSTS = ("medicaid_state_cost", "chip_state_cost", "msp_state_cost")
#: Healthier Oregon covers people federal Medicaid can't. Its cost has no
#: enrollment test, and policyengine-us also enrolls Oregon's undocumented
#: residents in Medicaid, so it would price their coverage twice.
HEALTHIER_OREGON = "or_healthier_oregon_cost"
#: Whether CHIP's From-Conception-to-End-of-Pregnancy option covers a pregnant
#: person. The unborn child is the beneficiary, so federal CHIP funds match the
#: coverage whatever the parent's immigration status.
FCEP_ELIGIBLE = "is_chip_fcep_eligible_person"
CHIP_ENROLLED = "chip_enrolled"
#: Spreads each state's Medicaid spending over that state's enrollees.
MEDICAID_DENOMINATOR = "medicaid_slcsp_state_denominator"
#: Every state TANF program, summed.
TANF_VARIABLE = "tanf"

#: Household arrays whose weighted sums ``national_totals`` and
#: ``state_totals`` report.
TOTAL_KEYS = (
    "federal_health",
    "state_health",
    "health_total",
    "health_value",
    "federal_health_split",
    "state_health_split",
    "federal_health_other",
    "state_health_programs",
    "state_only_coverage",
    "healthier_oregon_overlap",
    "tanf",
    "tanf_in_state_benefits",
    "tanf_charge",
)


def _parameters(sim, year):
    return sim.tax_benefit_system.parameters(f"{year}-01-01")


def adds(sim, variable, year):
    """The variables ``variable`` adds, from its list or the parameter it names."""
    names = sim.tax_benefit_system.variables[variable].adds
    if isinstance(names, str):
        node = _parameters(sim, year)
        for part in names.split("."):
            node = getattr(node, part)
        names = node
    return list(names or ())


def classify_health_programs(
    health_value_programs,
    listed_health,
    federal_costs,
    state_costs,
    benefit_lists,
    health_in_net_income,
):
    """Split the programs ``healthcare_benefit_value`` adds by who pays for them.

    ``health_value_programs`` are the variables ``healthcare_benefit_value``
    adds, ``listed_health`` the names in
    ``gov.household.household_health_benefits``, ``federal_costs`` and
    ``state_costs`` the members of ``gov.household.federal_benefit_cost`` and
    ``gov.household.state_benefit_cost``, and ``benefit_lists`` the names in
    ``gov.household.household_benefits`` and
    ``gov.household.household_state_benefits``.

    Returns ``(fmap_split, federal, state)``, each in this module's order.
    Refuses a model this accounting would get wrong: one that puts health
    benefits in net income (``household_benefits`` would already count them),
    prices a health program this module doesn't classify, lists a health
    benefit ``healthcare_benefit_value`` doesn't price, splits other costs
    between federal and state, or lists a health program among the benefits
    the revenue lines already net.
    """
    if health_in_net_income:
        raise ValueError(
            "health benefits are in household net income, so household_benefits "
            "already counts them; the health accounting would count them twice"
        )
    value = set(health_value_programs)
    known = set(FMAP_SPLIT_HEALTH) | set(FEDERAL_HEALTH) | set(STATE_HEALTH)
    unknown = value - known
    if unknown:
        raise ValueError(
            f"{HEALTH_VALUE_VARIABLE} adds programs this accounting doesn't "
            f"classify: {sorted(unknown)}"
        )
    missing = (set(FMAP_SPLIT_HEALTH) | set(FEDERAL_HEALTH)) - value
    if missing:
        raise ValueError(f"{HEALTH_VALUE_VARIABLE} no longer adds {sorted(missing)}")
    listed = {HEALTH_LIST_ALIASES.get(name, name) for name in listed_health}
    unpriced = listed - value
    if unpriced:
        raise ValueError(
            "gov.household.household_health_benefits lists "
            f"{sorted(unpriced)}, which {HEALTH_VALUE_VARIABLE} doesn't add"
        )
    for name, members, want in (
        ("gov.household.federal_benefit_cost", federal_costs, FEDERAL_SHARE_COSTS),
        ("gov.household.state_benefit_cost", state_costs, STATE_SHARE_COSTS),
    ):
        if set(members) != set(want):
            raise ValueError(
                f"{name} changed: unclassified {sorted(set(members) - set(want))}, "
                f"missing {sorted(set(want) - set(members))}"
            )
    netted = (known | set(HEALTH_LIST_ALIASES)) & set(benefit_lists)
    if netted:
        raise ValueError(
            f"household benefit lists include health programs {sorted(netted)}, "
            "which the health accounting would count twice"
        )
    return (
        tuple(p for p in FMAP_SPLIT_HEALTH if p in value),
        tuple(p for p in FEDERAL_HEALTH if p in value),
        tuple(p for p in STATE_HEALTH if p in value),
    )


def health_programs(sim, year):
    """``classify_health_programs`` for the model ``sim`` runs."""
    gov = _parameters(sim, year).gov
    return classify_health_programs(
        adds(sim, HEALTH_VALUE_VARIABLE, year),
        list(gov.household.household_health_benefits),
        list(gov.household.federal_benefit_cost),
        list(gov.household.state_benefit_cost),
        list(gov.household.household_benefits) + list(gov.household.household_state_benefits),
        bool(gov.simulation.include_health_benefits_in_net_income),
    )


def programs_metadata(sim, year):
    """The programs the health and TANF lines count, by who pays, for a run's record."""
    fmap_split, federal, state = health_programs(sim, year)
    return {
        "split_by_federal_matching": list(fmap_split),
        "federal": list(federal),
        "state": list(state),
        "tanf_programs_in_state_benefits": tanf_programs_in_state_benefits(
            state_tanf_variables(sim),
            _parameters(sim, year).gov.household.household_state_benefits,
        ),
        "tanf_states_in_state_benefits": tanf_states_in_state_benefits(
            state_tanf_variables(sim),
            _parameters(sim, year).gov.household.household_state_benefits,
        ),
    }


def state_tanf_variables(sim):
    """Every state TANF program ``tanf`` adds, each named with its state's code first.

    policyengine-us 1.764.6 defines the list beside ``tanf``; 2.x moved it
    beside ``tanf_if_takes_up``.
    """
    variable = sim.tax_benefit_system.variables[TANF_VARIABLE]
    module = sys.modules.get(type(variable).__module__)
    names = getattr(module, "STATE_TANF_VARIABLES", None)
    if names is None:
        try:
            from policyengine_us.variables.gov.hhs.tanf.cash.tanf_if_takes_up import (
                STATE_TANF_VARIABLES as names,
            )
        except ImportError:
            names = None
    if not names:
        raise ValueError("can't find the state TANF programs that tanf adds")
    return list(names)


def tanf_programs_in_state_benefits(state_tanf_variables, state_benefits):
    """The state TANF programs ``household_state_benefits`` also lists, in ``tanf``'s order.

    ``tanf`` adds every state program for families that take TANF up;
    ``household_state_benefits`` adds each program it lists for every eligible
    family, with no take-up test.
    """
    listed = set(state_benefits)
    return [v for v in state_tanf_variables if v in listed]


def tanf_states_in_state_benefits(state_tanf_variables, state_benefits):
    """States whose TANF program ``household_state_benefits`` also lists.

    ``state_tanf_variables`` holds every state TANF program, each named with its
    state's code first (``ca_tanf``, ``ma_tafdc``).
    """
    programs = tanf_programs_in_state_benefits(state_tanf_variables, state_benefits)
    return sorted({v.split("_", 1)[0].upper() for v in programs})


def federally_eligible_status(status, years_since_entry, p):
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


def state_only_federal_share(federal, shares, fcep):
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


def state_only_coverage(sim, year):
    """Federal share policyengine-us books for coverage only a state pays for, by household.

    ``medicaid_federal_share`` and ``chip_federal_share`` apply federal matching
    rates to every enrollee, including people a state covers whatever their
    immigration status, such as California's Medi-Cal for undocumented and
    DACA residents. Federal law matches only emergency care for such people
    (42 USC 1396b(v)), so this moves their whole federal share to the state. If
    the state spending totals that ``medicaid_cost`` spreads count that
    federally matched emergency care, the move overstates the state's cost by
    the federal share of their emergency care, an amount this accounting can't
    measure. The line depends on the immigration status the data assign:
    Microcosm treats anyone who reports Medicaid in the CPS as documented.

    The federal test leaves out the election in 42 USC 1396b(v)(4)(A). Under
    it, a state can cover lawfully residing children under 21 and pregnant
    women with federal matching, even during the five-year bar.
    policyengine-us 1.764.6 models no such election. Microcosm's build p
    assigns no one Temporary Protected Status and leaves
    ``years_since_us_entry`` at its default of 5, so everyone this moves has
    undocumented or DACA status. The Marketplace rule, 45 CFR 155.20, counts
    TPS holders as lawfully present and leaves out both of those groups.
    """
    p = _parameters(sim, year).gov.hhs.medicaid.eligibility
    status = sim.calculate("immigration_status", period=year, decode_enums=True)
    years = sim.calculate("years_since_us_entry", period=year)
    federal = federally_eligible_status(np.asarray(status), np.asarray(years), p)
    shares = {
        v: np.asarray(sim.calculate(v, period=year), dtype=float) for v in FEDERAL_SHARE_COSTS
    }
    fcep = np.asarray(sim.calculate(FCEP_ELIGIBLE, period=year), dtype=bool) & np.asarray(
        sim.calculate(CHIP_ENROLLED, period=year), dtype=bool
    )
    moved = state_only_federal_share(federal, shares, fcep)
    return np.asarray(sim.map_result(moved, "person", "household"), dtype=float)


def healthier_oregon_overlap(sim, year):
    """Healthier Oregon cost for people policyengine-us also enrolls in Medicaid, by household."""
    cost = np.asarray(sim.calculate(HEALTHIER_OREGON, period=year), dtype=float)
    enrolled = np.asarray(sim.calculate("medicaid_enrolled", period=year), dtype=bool)
    return np.asarray(
        sim.map_result(np.where(enrolled, cost, 0.0), "person", "household"), dtype=float
    )


def with_derived(frame):
    """Add the measures built from a frame's stored arrays.

    ``state_health`` is each household's health spending that falls on its
    state and ``federal_health`` the part that falls on the federal government;
    between them they hold every program in ``healthcare_benefit_value`` once,
    less the Healthier Oregon overlap. ``tanf_charge`` is the household's TANF
    less the copy its state's line already holds (``tanf_in_state_benefits``),
    so that line and the charge hold its TANF once, as ``tanf`` pays it. The
    charge turns negative for a family eligible for a listed program that
    doesn't take TANF up.
    """
    frame["state_health"] = (
        frame["state_health_split"] + frame["state_only_coverage"] + frame["state_health_programs"]
    )
    frame["federal_health"] = (
        frame["federal_health_split"] - frame["state_only_coverage"] + frame["federal_health_other"]
    )
    frame["health_total"] = frame["federal_health"] + frame["state_health"]
    frame["tanf_charge"] = frame["tanf"] - frame["tanf_in_state_benefits"]
    return frame


#: policyengine-us stores float32 values, which hold about seven significant
#: digits, so a sum it builds can differ from the same sum built here in float64
#: by a few units in the seventh digit.
FLOAT32_TOLERANCE = 1e-6


def _refuse_gap(name, residual, weights, scale):
    """Refuse a residual beyond float32 rounding of the amounts it compares.

    A household's residual may reach $1 or a millionth of its ``scale``,
    whichever is larger, and the weighted residual $1 million or a millionth of
    the weighted ``scale``.
    """
    residual = np.asarray(residual, dtype=float)
    scale = np.abs(np.asarray(scale, dtype=float))
    weights = np.asarray(weights, dtype=float)
    allowed = np.maximum(1.0, FLOAT32_TOLERANCE * scale)
    worst = float(np.abs(residual).max()) if residual.size else 0.0
    weighted = float((residual * weights).sum())
    weighted_allowed = max(1e6, FLOAT32_TOLERANCE * float((scale * np.abs(weights)).sum()))
    if (np.abs(residual) >= allowed).any() or abs(weighted) >= weighted_allowed:
        raise AssertionError(
            f"{name} by up to ${worst:,.2f} a household (${weighted:,.0f} weighted)"
        )


def check_health_split(frame):
    """Refuse a frame whose federal and state shares don't add up.

    policyengine-us's federal and state shares must add up to the Medicaid,
    CHIP and Medicare Savings Program costs they split, and the state-only move
    can't exceed the federal share it comes from.
    """
    _refuse_gap(
        "federal_benefit_cost + state_benefit_cost differ from Medicaid, CHIP and MSP cost",
        frame["fmap_split_cost"] - frame["federal_health_split"] - frame["state_health_split"],
        frame["weight"],
        frame["fmap_split_cost"],
    )
    moved = frame["state_only_coverage"]
    if (moved < -1e-6).any() or (moved > frame["federal_health_split"] + 1e-6).any():
        raise AssertionError("state-only coverage moves more than the federal share it comes from")


def check_frame(frame):
    """Refuse a frame whose pieces don't add up.

    Beyond ``check_health_split``, the federal and state parts must hold
    ``healthcare_benefit_value`` less the Healthier Oregon overlap.
    """
    check_health_split(frame)
    _refuse_gap(
        f"the federal and state health parts differ from {HEALTH_VALUE_VARIABLE}",
        frame["health_total"] - (frame["health_value"] - frame["healthier_oregon_overlap"]),
        frame["weight"],
        frame["health_value"],
    )


def household_frame(sim, year):
    """Each household's health spending by payer and its TANF, as arrays."""
    fmap_split, federal, state_programs = health_programs(sim, year)
    parameters = _parameters(sim, year)

    def hh(variable):
        return np.asarray(sim.calculate(variable, map_to="household", period=year), dtype=float)

    weight = np.asarray(sim.calculate("household_weight", period=year), dtype=float)

    def total(variables):
        return sum((hh(v) for v in variables), np.zeros_like(weight))

    state = np.asarray(
        sim.calculate("state_code_str", map_to="household", period=year)
    ).astype(str)
    overlap = (
        healthier_oregon_overlap(sim, year)
        if HEALTHIER_OREGON in state_programs
        else np.zeros_like(weight)
    )
    tanf = hh(TANF_VARIABLE)
    # The copy of TANF that household_state_benefits holds: each program it
    # lists at its full amount, whether or not the family takes TANF up.
    tanf_in_state_benefits = total(
        tanf_programs_in_state_benefits(
            state_tanf_variables(sim), parameters.gov.household.household_state_benefits
        )
    )
    frame = {
        "state": state,
        "weight": weight,
        "federal_health_split": hh("federal_benefit_cost"),
        "state_health_split": hh("state_benefit_cost"),
        "fmap_split_cost": total(fmap_split),
        "federal_health_other": total(federal),
        "state_health_programs": total(state_programs) - overlap,
        "healthier_oregon_overlap": overlap,
        "state_only_coverage": state_only_coverage(sim, year),
        "health_value": hh(HEALTH_VALUE_VARIABLE),
        "tanf": tanf,
        "tanf_in_state_benefits": tanf_in_state_benefits,
    }
    with_derived(frame)
    check_frame(frame)
    return frame


def national_totals(frame):
    """Weighted national total of each array in ``TOTAL_KEYS``."""
    weight = frame["weight"]
    return {key: float((frame[key] * weight).sum()) for key in TOTAL_KEYS}


def state_totals(frame):
    """Weighted total of each array in ``TOTAL_KEYS`` for each state, by state code."""
    weight = frame["weight"]
    state = frame["state"]
    out = {}
    for code in sorted(np.unique(state)):
        mask = state == code
        out[str(code)] = {
            key: float((frame[key][mask] * weight[mask]).sum()) for key in TOTAL_KEYS
        }
    return out


def medicaid_denominator(sim, year):
    """Each person's ``medicaid_slcsp_state_denominator`` in ``sim``."""
    return np.asarray(sim.calculate(MEDICAID_DENOMINATOR, period=year), dtype=float)


def price_medicaid_at_baseline(branch, denominator, year):
    """Price a branch's Medicaid enrollees at the baseline's cost per enrollee.

    ``medicaid_cost_if_enrolled`` is the state's spending times the person's
    cost index over ``medicaid_slcsp_state_denominator``, the weighted sum of
    the cost indices of the state's enrollees in the same simulation. With the
    baseline's denominator, each enrollee costs what an enrollee with that cost
    index costs in the baseline, so the state's total moves with enrollment.
    """
    if branch.get_holder(MEDICAID_DENOMINATOR).get_known_periods():
        raise RuntimeError(
            f"{MEDICAID_DENOMINATOR} is already calculated in this branch; set the "
            "baseline's before calculating anything that depends on it"
        )
    branch.set_input(MEDICAID_DENOMINATOR, year, np.asarray(denominator, dtype=float))
