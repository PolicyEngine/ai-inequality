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
  policyengine-us builds from ``gov.hhs.medicaid.cost_share``). Federal law
  bars federal matching, apart from emergency care, for enrollees whose
  immigration status fails its test (42 USC 1396b(v)), and policyengine-us
  books a federal share for them anyway. ``state_only_accounting`` sorts those
  shares by whether a state rule in policyengine-us covers the enrollee:

  - We charge the state the federal share of Medicaid. We also charge it the
    federal share of CHIP in a state whose ``undocumented_immigrant`` rule is
    on, or where California's own rule covers the person, since the state pays
    for that coverage alone.
    Federal funds still match these enrollees' emergency care, labor and
    delivery included (42 USC 1396b(v)(3)), so we likely overstate the
    state's cost.
  - We keep the federal share for a pregnant enrollee in a state that takes
    CHIP's unborn-child option, with income at or under that option's limit.
    Federal CHIP funds match her prenatal care whatever her status, and
    Medicaid matches her delivery as emergency care. CHIP coverage through the
    option itself keeps its federal match too. 42 CFR 457.10 counts an unborn
    child as a child, and CMS read it to cover unborn children whatever the
    parent's status (67 FR 61956, 61965-66); 42 USC 1397ll(f)(1)(A) preserves
    the option.
  - We leave out CHIP that policyengine-us books where no such rule covers the
    person, and the Medicare Savings Programs for these enrollees, from both
    governments' lines: no government pays for that coverage.
    policyengine-us 1.764.6 bars only an ``UNDOCUMENTED`` label from CHIP and
    tests no status for the Medicare Savings Programs.
* The federal government pays ACA premium tax credits and the Basic Health
  Program.
* The state pays its own health programs: Healthier Oregon at policyengine-us
  1.764.6, and the state premium subsidies that later releases model. We leave
  Healthier Oregon out for people policyengine-us also prices in Medicaid or
  CHIP, and for people who don't take Medicaid up, since its cost has no
  enrollment or take-up test of its own. We leave out Colorado's OmniSalud
  (``co_omnisalud``): policyengine-us 1.764.6 prices it as the tax unit's
  benchmark premium, which counts only members who can buy Marketplace
  coverage, so it never prices the people OmniSalud covers.

Congress fixes each state's TANF block grant (42 USC 603(a)(1)), so we charge
every TANF change to the states, and we count each TANF dollar once. Needy
states can also draw on a TANF contingency fund that Congress funded at up to
$608 million for fiscal 2018 (42 USC 603(b)(2)). We can overstate the states'
share by up to that amount a year.

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
#: Healthier Oregon; later releases add the premium subsidies.
STATE_HEALTH = (
    "assigned_ca_premium_subsidy",
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
#: Programs ``healthcare_benefit_value`` adds that we leave out, because
#: policyengine-us prices them for people the program doesn't cover.
#: ``co_omnisalud`` adds the tax unit's ``slcsp``, which sums the benchmark
#: premiums of the members who can buy Marketplace coverage (``pays_aca_premium``
#: excludes ``UNDOCUMENTED`` and ``DACA``), so it prices the lawfully present
#: members, whose premium tax credit already prices the same premium.
EXCLUDED_HEALTH = ("co_omnisalud",)
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
#: enrollment or take-up test, and policyengine-us also enrolls Oregon's
#: undocumented residents in Medicaid and DACA children in CHIP, so it would
#: price their coverage twice.
HEALTHIER_OREGON = "or_healthier_oregon_cost"
HEALTHIER_OREGON_ALSO_PRICED = ("medicaid_enrolled", "chip_enrolled")
MEDICAID_TAKE_UP = "takes_up_medicaid_if_eligible"
#: California's own rule for Medi-Cal regardless of immigration status, which
#: policyengine-us's ``is_medicaid_immigration_status_eligible`` adds to the
#: states' ``undocumented_immigrant`` rule.
CA_STATE_RULE = "is_ca_medicaid_immigration_status_eligible"
#: Whether CHIP's From-Conception-to-End-of-Pregnancy option covers a pregnant
#: person. The unborn child is the beneficiary, so federal CHIP funds match the
#: coverage whatever the parent's immigration status.
FCEP_ELIGIBLE = "is_chip_fcep_eligible_person"
CHIP_ENROLLED = "chip_enrolled"
#: The labels whose federal shares ``state_only_accounting`` may move or leave
#: out. CMS counts neither status as lawfully residing for the election in 42
#: USC 1396b(v)(4)(A), so no state gets federal matching for people who hold
#: them under it.
STATE_ONLY_STATUSES = ("UNDOCUMENTED", "DACA")
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
    "unfunded_federal",
    "unfunded_state",
    "excluded_health_programs",
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

    Returns ``(fmap_split, federal, state, excluded)``, each in this module's
    order; ``excluded`` holds the programs in ``EXCLUDED_HEALTH`` that the model
    prices, which the totals leave out. Refuses a model this accounting would
    get wrong: one that puts health
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
    known = (
        set(FMAP_SPLIT_HEALTH) | set(FEDERAL_HEALTH) | set(STATE_HEALTH) | set(EXCLUDED_HEALTH)
    )
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
        tuple(p for p in EXCLUDED_HEALTH if p in value),
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
    """The programs the health and TANF lines count, by who pays, for a run's record.

    ``excluded`` lists the programs the model prices that the totals leave out,
    and ``unfunded`` names the coverage ``state_only_accounting`` leaves out of
    both governments' lines.
    """
    fmap_split, federal, state, excluded = health_programs(sim, year)
    return {
        "split_by_federal_matching": list(fmap_split),
        "federal": list(federal),
        "state": list(state),
        "excluded": list(excluded),
        "unfunded": (
            "CHIP policyengine-us books for people whose immigration status fails "
            "the federal test, outside states whose undocumented_immigrant rule "
            "is on and outside California's own rule, apart from the "
            "unborn-child option; and Medicare Savings Program benefits "
            "for people whose status fails the federal test"
        ),
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


def pregnancy_match(is_pregnant, income_level, fcep_limit):
    """Whether federal funds still match a pregnant enrollee's coverage, by person.

    Holds for a pregnant person in a state that takes CHIP's unborn-child
    option, with income at or under that option's limit. ``fcep_limit`` gives
    each person's state limit (``gov.hhs.chip.fcep.income_limit``), and
    policyengine-us sets it to ``-inf`` in a state without the option.
    ``income_level`` gives the ``medicaid_income_level`` that policyengine-us's
    FCEP test reads.
    """
    fcep_limit = np.asarray(fcep_limit, dtype=float)
    return (
        np.asarray(is_pregnant, dtype=bool)
        & (fcep_limit > 0)
        & (np.asarray(income_level, dtype=float) <= fcep_limit)
    )


def state_only_split(federal, costs, fcep, pregnancy_match, state_rule):
    """Federal shares to move to the state, and coverage no government pays for, by person.

    ``federal`` says whether each person's immigration status lets federal
    funds match their coverage, and ``costs`` maps each name in
    ``FEDERAL_SHARE_COSTS`` and ``STATE_SHARE_COSTS`` to the share
    policyengine-us books for each person. ``fcep`` says whether CHIP's
    unborn-child (FCEP) option covers the person, ``pregnancy_match`` whether
    she is pregnant in a state that takes that option, with income at or under
    its limit, and ``state_rule`` whether the person lives in a state whose
    ``undocumented_immigrant`` rule is on, or California's own rule covers them
    (``state_only_accounting`` reads both).

    For people federal matching can't cover, returns ``(moved, unfunded_federal,
    unfunded_state)``:

    * ``moved``: the federal share of Medicaid, apart from pregnant enrollees
      in ``pregnancy_match``, plus the federal share of CHIP where
      ``state_rule`` holds, apart from FCEP coverage. policyengine-us enrolls
      such people in Medicaid only through a state rule, so the state pays.
    * ``unfunded_federal`` and ``unfunded_state``: both shares of CHIP outside
      ``state_rule`` (apart from FCEP coverage) and of the Medicare Savings
      Programs. No government pays for that coverage.
    """
    blocked = ~np.asarray(federal, dtype=bool)
    fcep = np.asarray(fcep, dtype=bool)
    keep_medicaid = np.asarray(pregnancy_match, dtype=bool)
    state_rule = np.asarray(state_rule, dtype=bool)

    def cost(name):
        return np.asarray(costs[name], dtype=float)

    chip_blocked = blocked & ~fcep
    moved = np.where(blocked & ~keep_medicaid, cost("medicaid_federal_cost"), 0.0) + np.where(
        chip_blocked & state_rule, cost("chip_federal_cost"), 0.0
    )
    chip_unfunded = chip_blocked & ~state_rule
    unfunded_federal = np.where(chip_unfunded, cost("chip_federal_cost"), 0.0) + np.where(
        blocked, cost("msp_federal_cost"), 0.0
    )
    unfunded_state = np.where(chip_unfunded, cost("chip_state_cost"), 0.0) + np.where(
        blocked, cost("msp_state_cost"), 0.0
    )
    return moved, unfunded_federal, unfunded_state


def check_moved_statuses(status, moved):
    """Raise if anyone whose share we move or leave out carries a label outside ``STATE_ONLY_STATUSES``.

    ``status`` gives each person's immigration status label and ``moved`` the
    share ``state_only_split`` moves or leaves out for them. A state that took
    the election in 42 USC 1396b(v)(4)(A) gets federal matching for lawfully
    residing children and pregnant women with other statuses, and the federal
    test doesn't apply the election.
    """
    status = np.asarray(status).astype(str)
    reached = status[np.asarray(moved, dtype=float) != 0]
    others = sorted(set(reached.tolist()) - set(STATE_ONLY_STATUSES))
    if others:
        raise ValueError(
            "state_only_accounting would move or leave out shares for people "
            f"with {', '.join(others)} status. A state that took the election in "
            "42 USC 1396b(v)(4)(A) gets federal matching for lawfully residing "
            "children and pregnant women, so apply the election to the federal "
            "test before moving their shares."
        )


def _by_state(parameter, state):
    """A state-indexed parameter's value for each entry of ``state``."""
    values = {code: float(getattr(parameter, code, 0.0)) for code in np.unique(state)}
    return np.asarray([values[code] for code in state], dtype=float)


def state_only_accounting(sim, year):
    """Federal shares a state pays alone, and coverage no government pays, by household.

    ``medicaid_federal_share``, ``chip_federal_share`` and
    ``msp_federal_cost`` apply federal matching rates to every enrollee,
    including people whose immigration status fails the federal test. Federal
    law matches only their emergency care, labor and delivery included (42 USC
    1396b(v)(1)-(3)). policyengine-us enrolls such people in Medicaid only
    through a state rule (``undocumented_immigrant``, California's own rule,
    its foster youth rule and Illinois's HBI programs), such as California's
    Medi-Cal for undocumented and DACA residents. Its CHIP test bars only an
    ``UNDOCUMENTED`` label, so it books CHIP for a DACA child in any state
    with a children's CHIP limit. It also books CHIP for a pregnant DACA woman
    in a state whose standard CHIP pregnancy limit exceeds its unborn-child
    limit. It gives the Medicare Savings Programs no status test.
    ``state_only_split`` sorts each share. For CHIP, ``state_rule`` holds for
    anyone in a state whose ``undocumented_immigrant`` rule is on, whatever
    their label, and for anyone California's own rule covers
    (``CA_STATE_RULE``). policyengine-us's
    ``is_medicaid_immigration_status_eligible`` applies the first rule to the
    ``UNDOCUMENTED`` label alone, and its CHIP test bars that label, so in
    those states we also charge the state a DACA child's CHIP. policyengine-us
    1.764.6 gives California CHIP only through the unborn-child option, so
    California's rule moves no CHIP share yet. The state spending totals that
    ``medicaid_cost`` spreads likely count the federally matched emergency
    care. If they do, we overstate the state's cost by a federal share of that
    care we can't measure here.

    The split depends on the immigration status labels the data assign.
    Microcosm treats anyone who reports Medicaid coverage in the prior year
    (the CPS's ``CAID``) as documented. It assigns ``UNDOCUMENTED`` to the
    non-citizens left after its documented-status tests, ``DACA`` by a cohort
    test on work-authorized non-citizens, and no Temporary Protected Status
    label. So some people who carry the ``UNDOCUMENTED`` or ``DACA`` label hold
    a status CMS's letter SHO #10-006 counts as lawfully present, such as TPS,
    and the federal test can't see them.

    The federal test, like policyengine-us 1.764.6, leaves out the election in
    42 USC 1396b(v)(4)(A). Under it, a state can cover lawfully residing
    children under 21 and pregnant women with federal matching, even during the
    five-year bar. policyengine-us 2.25.0 models the election in Medicaid and
    CHIP (PolicyEngine/policyengine-us#9737), so a run on 2.25.0 or later needs
    the federal test to apply it too. For the election, SHO #10-006 counts TPS
    holders as lawfully present, and SHO #12-002 excludes DACA recipients.
    Undocumented immigrants hold none of the statuses SHO #10-006 lists.
    ``check_moved_statuses`` raises if the split reaches a label other than
    ``UNDOCUMENTED`` or ``DACA``, such as a later build's TPS label or a
    permanent resident in the five-year bar.
    """
    parameters = _parameters(sim, year)
    p = parameters.gov.hhs.medicaid.eligibility
    status = np.asarray(sim.calculate("immigration_status", period=year, decode_enums=True))
    years = sim.calculate("years_since_us_entry", period=year)
    federal = federally_eligible_status(status, np.asarray(years), p)
    costs = {
        v: np.asarray(sim.calculate(v, period=year), dtype=float)
        for v in FEDERAL_SHARE_COSTS + STATE_SHARE_COSTS
    }
    fcep = np.asarray(sim.calculate(FCEP_ELIGIBLE, period=year), dtype=bool) & np.asarray(
        sim.calculate(CHIP_ENROLLED, period=year), dtype=bool
    )
    state = np.asarray(sim.calculate("state_code_str", period=year, map_to="person")).astype(str)
    pregnant_match = pregnancy_match(
        sim.calculate("is_pregnant", period=year),
        sim.calculate("medicaid_income_level", period=year),
        _by_state(parameters.gov.hhs.chip.fcep.income_limit, state),
    )
    state_rule = (_by_state(p.undocumented_immigrant, state) > 0) | np.asarray(
        sim.calculate(CA_STATE_RULE, period=year), dtype=bool
    )
    moved, unfunded_federal, unfunded_state = state_only_split(
        federal, costs, fcep, pregnant_match, state_rule
    )
    check_moved_statuses(status, moved + unfunded_federal + unfunded_state)

    def household(values):
        return np.asarray(sim.map_result(values, "person", "household"), dtype=float)

    return {
        "state_only_coverage": household(moved),
        "unfunded_federal": household(unfunded_federal),
        "unfunded_state": household(unfunded_state),
    }


def state_only_coverage(sim, year):
    """The federal share each household's state pays alone (``state_only_accounting``)."""
    return state_only_accounting(sim, year)["state_only_coverage"]


def healthier_oregon_overlap(sim, year):
    """Healthier Oregon cost we leave out, by household.

    Healthier Oregon's cost has no enrollment or take-up test, so we leave it
    out for people policyengine-us also prices in Medicaid or CHIP and for
    people who don't take Medicaid up.
    """
    cost = np.asarray(sim.calculate(HEALTHIER_OREGON, period=year), dtype=float)
    also_priced = np.zeros(cost.shape, dtype=bool)
    for variable in HEALTHIER_OREGON_ALSO_PRICED:
        also_priced |= np.asarray(sim.calculate(variable, period=year), dtype=bool)
    declines = ~np.asarray(sim.calculate(MEDICAID_TAKE_UP, period=year), dtype=bool)
    return np.asarray(
        sim.map_result(np.where(also_priced | declines, cost, 0.0), "person", "household"),
        dtype=float,
    )


def with_derived(frame):
    """Add the measures built from a frame's stored arrays.

    ``state_health`` is each household's health spending that falls on its
    state and ``federal_health`` the part that falls on the federal government;
    between them they hold every program in ``healthcare_benefit_value`` once,
    less the Healthier Oregon overlap, the excluded programs and the coverage
    no government pays for (``unfunded_federal`` and ``unfunded_state``). A
    frame without those last arrays gets zeros. ``tanf_charge`` is the
    household's TANF less the copy its state's line already holds
    (``tanf_in_state_benefits``), so that line and the charge hold its TANF
    once, as ``tanf`` pays it. The charge turns negative for a family eligible
    for a listed program that doesn't take TANF up.
    """
    zeros = np.zeros_like(np.asarray(frame["state_health_split"], dtype=float))
    for key in ("unfunded_federal", "unfunded_state", "excluded_health_programs"):
        if key not in frame:
            frame[key] = zeros.copy()
    frame["state_health"] = (
        frame["state_health_split"]
        + frame["state_only_coverage"]
        - frame["unfunded_state"]
        + frame["state_health_programs"]
    )
    frame["federal_health"] = (
        frame["federal_health_split"]
        - frame["state_only_coverage"]
        - frame["unfunded_federal"]
        + frame["federal_health_other"]
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
    CHIP and Medicare Savings Program costs they split. The state-only move and
    the unfunded federal share together can't exceed the federal share they
    come from, nor the unfunded state share the state share, and none of them
    can fall below zero.
    """
    _refuse_gap(
        "federal_benefit_cost + state_benefit_cost differ from Medicaid, CHIP and MSP cost",
        frame["fmap_split_cost"] - frame["federal_health_split"] - frame["state_health_split"],
        frame["weight"],
        frame["fmap_split_cost"],
    )
    zeros = np.zeros_like(np.asarray(frame["state_only_coverage"], dtype=float))
    moved = frame["state_only_coverage"]
    unfunded_federal = frame.get("unfunded_federal", zeros)
    unfunded_state = frame.get("unfunded_state", zeros)
    if (
        (moved < -1e-6).any()
        or (unfunded_federal < -1e-6).any()
        or (unfunded_state < -1e-6).any()
    ):
        raise AssertionError("the state-only accounting moves or drops a negative share")
    if (moved + unfunded_federal > frame["federal_health_split"] + 1e-6).any():
        raise AssertionError("state-only coverage moves more than the federal share it comes from")
    if (unfunded_state > frame["state_health_split"] + 1e-6).any():
        raise AssertionError("unfunded coverage drops more than the state share it comes from")


def check_frame(frame):
    """Refuse a frame whose pieces don't add up.

    Beyond ``check_health_split``, the federal and state parts must hold
    ``healthcare_benefit_value`` less the Healthier Oregon overlap, the
    excluded programs and the unfunded coverage.
    """
    check_health_split(frame)
    zeros = np.zeros_like(np.asarray(frame["health_value"], dtype=float))
    left_out = (
        frame["healthier_oregon_overlap"]
        + frame.get("excluded_health_programs", zeros)
        + frame.get("unfunded_federal", zeros)
        + frame.get("unfunded_state", zeros)
    )
    _refuse_gap(
        f"the federal and state health parts differ from {HEALTH_VALUE_VARIABLE}",
        frame["health_total"] - (frame["health_value"] - left_out),
        frame["weight"],
        frame["health_value"],
    )


def household_frame(sim, year):
    """Each household's health spending by payer and its TANF, as arrays."""
    fmap_split, federal, state_programs, excluded = health_programs(sim, year)
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
        "excluded_health_programs": total(excluded),
        **state_only_accounting(sim, year),
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
