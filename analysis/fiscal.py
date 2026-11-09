"""Shared fiscal helpers for analysis scenarios.

The decomposition below is non-overlapping and reconciles to the PolicyEngine-US
household net-income identity:

    household_net_income
        = household_market_income
        + household_benefits
        + household_refundable_tax_credits
        - household_tax_before_refundable_credits

Government net revenue (total) = taxes - transfers, where

    taxes     = household_tax_before_refundable_credits + employer_payroll_tax
    transfers = household_refundable_tax_credits + household_benefits

`household_tax_before_refundable_credits` already bundles federal income tax
(before refundable credits), employee payroll tax, self-employment tax, flat
tax, and state income tax before refundable credits. The federal-income-tax
subcomponents (main rates, capital-gains preferential tax, AMT, NIIT,
nonrefundable credits) are pulled out for attribution but their sum equals the
federal income tax portion - they must not be added to the aggregate.

Individual programs (EITC, refundable CTC, SNAP, SSI, ...) are also pulled out
for attribution only; they are already inside the refundable-credit and
benefit aggregates.

Health coverage and TANF: ``household_benefits`` holds no health coverage,
because policyengine-us keeps it out of household net income, and it counts a
state TANF program twice when ``gov.household.household_state_benefits`` also
lists it (Massachusetts's TAFDC at policyengine-us 1.764.6). Pass a
``health_tanf.household_frame`` as ``health_frame`` to add each household's
health spending by payer and its TANF; ``net_fiscal_impact`` then reports

    total_change_excluding_health = total_change + TANF counted twice
    total_change_with_health_tanf = total_change_excluding_health
                                    - health spending

Build the frame only on a simulation whose Medicaid enrollees cost what they
cost in the baseline (``health_tanf.price_medicaid_at_baseline``).
"""

import numpy as np

from . import health_tanf
from .constants import YEAR

#: Taxes inside ``household_tax_before_refundable_credits`` that the site's
#: charts put in no band. The US federal chart adds federal income tax, the
#: employee Social Security and Medicare taxes, self-employment tax and
#: ``employer_payroll_tax``; the state charts add each state's
#: ``household_state_tax_before_refundable_credits``. That leaves the
#: Additional Medicare Tax and workers' state payroll taxes (both inside
#: ``employee_payroll_tax``), the flat tax, and the city and county taxes.
OUTSIDE_CHART_TAXES = (
    "additional_medicare_tax",
    "employee_state_payroll_tax",
    "flat_tax",
    "local_income_tax_before_refundable_credits",
    "local_occupational_tax",
)

#: The health and TANF totals ``revenue_components`` and
#: ``state_revenue_components`` add from a ``health_frame``. ``tanf`` is
#: already a revenue component.
HEALTH_TANF_KEYS = tuple(k for k in health_tanf.TOTAL_KEYS if k != "tanf")


def _hh_sum(sim, var, year=YEAR):
    return float(sim.calculate(var, map_to="household", period=year).sum())


def _tu_sum(sim, var, year=YEAR):
    return float(sim.calculate(var, period=year).sum())


def revenue_components(sim, year=YEAR, health_frame=None):
    """Return a comprehensive, non-overlapping revenue/transfer decomposition.

    Top-line aggregates (these reconcile to household net income):
      - household_tax_before_refundable_credits
      - household_refundable_tax_credits
      - household_benefits
      - employer_payroll_tax (government revenue, not in household_tax)

    Attribution subcomponents (already inside the aggregates above):
      Federal income tax before refundable credits:
        - income_tax_main_rates (ordinary-rate tax)
        - capital_gains_tax (preferential LTCG/qualified-dividend tax)
        - alternative_minimum_tax
        - net_investment_income_tax
        - income_tax_capped_non_refundable_credits (reduces tax)
      Payroll / self-employment:
        - employee_social_security_tax, employee_medicare_tax
        - employer_social_security_tax, employer_medicare_tax
        - self_employment_tax
      State:
        - household_state_tax_before_refundable_credits
        - household_refundable_state_tax_credits
        - household_state_benefits
      Federal refundable credits:
        - eitc, refundable_ctc
        - income_tax_refundable_credits (total federal refundable)
      Benefits:
        - snap, ssi, tanf, wic, household_health_benefits
      Taxes no chart band holds: ``OUTSIDE_CHART_TAXES``.

    With a ``health_frame`` (``health_tanf.household_frame`` of ``sim``), it
    also returns the national totals in ``HEALTH_TANF_KEYS``: health spending
    by payer and the TANF that ``household_state_benefits`` already holds.
    """
    components = {
        # --- Aggregates (use these for totals) ---
        "household_tax_before_refundable_credits": _hh_sum(
            sim, "household_tax_before_refundable_credits", year
        ),
        "household_refundable_tax_credits": _hh_sum(
            sim, "household_refundable_tax_credits", year
        ),
        "household_benefits": _hh_sum(sim, "household_benefits", year),
        "employer_payroll_tax": _hh_sum(sim, "employer_payroll_tax", year),
        # --- Federal income tax subcomponents (sum to fed income tax portion) ---
        "fed_income_tax_main_rates": _tu_sum(sim, "income_tax_main_rates", year),
        "fed_capital_gains_tax": _tu_sum(sim, "capital_gains_tax", year),
        "fed_alternative_minimum_tax": _tu_sum(sim, "alternative_minimum_tax", year),
        "fed_net_investment_income_tax": _tu_sum(
            sim, "net_investment_income_tax", year
        ),
        "fed_nonrefundable_credits": _tu_sum(
            sim, "income_tax_capped_non_refundable_credits", year
        ),
        # Catch-all for the three minor additive items inside
        # income_tax_before_refundable_credits that don't get their own line:
        # recapture of investment credit, unreported payroll tax,
        # qualified-retirement penalty. Near-zero in current law, but
        # exposed so the 5-bucket decomposition stays MECE for any reform.
        "fed_other_income_tax_items": (
            _tu_sum(sim, "recapture_of_investment_credit", year)
            + _tu_sum(sim, "unreported_payroll_tax", year)
            + _tu_sum(sim, "qualified_retirement_penalty", year)
        ),
        "fed_income_tax_before_refundable_credits": _tu_sum(
            sim, "income_tax_before_refundable_credits", year
        ),
        # --- Payroll / self-employment ---
        "employee_social_security_tax": _hh_sum(
            sim, "employee_social_security_tax", year
        ),
        "employee_medicare_tax": _hh_sum(sim, "employee_medicare_tax", year),
        "employer_social_security_tax": _hh_sum(
            sim, "employer_social_security_tax", year
        ),
        "employer_medicare_tax": _hh_sum(sim, "employer_medicare_tax", year),
        "self_employment_tax": _hh_sum(sim, "self_employment_tax", year),
        # --- State ---
        "state_tax_before_refundable_credits": _hh_sum(
            sim, "household_state_tax_before_refundable_credits", year
        ),
        "state_refundable_credits": _hh_sum(
            sim, "household_refundable_state_tax_credits", year
        ),
        "state_benefits": _hh_sum(sim, "household_state_benefits", year),
        # --- Federal refundable credit components ---
        "income_tax_refundable_credits": _hh_sum(
            sim, "income_tax_refundable_credits", year
        ),
        "eitc": _hh_sum(sim, "eitc", year),
        "refundable_ctc": _hh_sum(sim, "refundable_ctc", year),
        # --- Benefit components ---
        "snap": _hh_sum(sim, "snap", year),
        "ssi": _hh_sum(sim, "ssi", year),
        "tanf": _hh_sum(sim, "tanf", year),
        "wic": _hh_sum(sim, "wic", year),
        "health_benefits": _hh_sum(sim, "household_health_benefits", year),
        # --- Identity-check variables ---
        "household_market_income": _hh_sum(sim, "household_market_income", year),
        "household_net_income": _hh_sum(sim, "household_net_income", year),
    }
    for variable in OUTSIDE_CHART_TAXES:
        components[variable] = _hh_sum(sim, variable, year)
    if health_frame is not None:
        totals = health_tanf.national_totals(health_frame)
        components.update({key: totals[key] for key in HEALTH_TANF_KEYS})
    return components


def net_fiscal_impact(components, baseline_components):
    """Return delta dictionary. Positive = more government revenue.

    Total change is computed from the *aggregates only* to avoid double-counting
    the subcomponents. Subcomponent deltas are reported for attribution.
    ``taxes_outside_charts_change`` adds the ``OUTSIDE_CHART_TAXES`` deltas.
    When the components carry health spending (a ``health_frame``),
    ``total_change_excluding_health`` counts TANF once and
    ``total_change_with_health_tanf`` also pays for health coverage, and
    ``_chart_identity_residual`` is what the site's charts and the taxes
    outside them leave of that total, which should be zero.
    """
    delta = {f"{k}_change": components[k] - baseline_components[k] for k in components}

    # Government net revenue = taxes - transfers
    # Taxes = household_tax_before_refundable_credits + employer_payroll_tax
    # Transfers = household_refundable_tax_credits + household_benefits
    total_change = (
        delta["household_tax_before_refundable_credits_change"]
        + delta["employer_payroll_tax_change"]
        - delta["household_refundable_tax_credits_change"]
        - delta["household_benefits_change"]
    )
    delta["total_change"] = total_change

    # Identity: change in (market - net) should equal the household-side of net
    # revenue change (total excluding employer payroll).
    market_minus_net_change = (
        delta["household_market_income_change"] - delta["household_net_income_change"]
    )
    household_side_change = total_change - delta["employer_payroll_tax_change"]
    delta["_identity_residual"] = market_minus_net_change - household_side_change

    delta["taxes_outside_charts_change"] = sum(
        delta.get(f"{variable}_change", 0.0) for variable in OUTSIDE_CHART_TAXES
    )
    if "health_total" in components:
        delta["total_change_excluding_health"] = (
            total_change + delta["tanf_in_state_benefits_change"]
        )
        delta["total_change_with_health_tanf"] = (
            delta["total_change_excluding_health"] - delta["health_total_change"]
        )
        delta["_chart_identity_residual"] = (
            delta["total_change_with_health_tanf"]
            - federal_chart_change(delta)
            - states_chart_change(delta)
            - delta["taxes_outside_charts_change"]
        )

    return delta


def federal_chart_change(delta):
    """The US federal chart's total, built from ``net_fiscal_impact`` deltas.

    Mirrors ``buildFederalRow`` in ``src/components/ShiftSweep.jsx``: federal
    income tax less federal refundable credits, payroll taxes (employee Social
    Security and Medicare, self-employment and every employer payroll tax), less
    benefits outside ``household_state_benefits`` and TANF, less the federal
    government's health spending.
    """
    income_tax = delta["fed_income_tax_before_refundable_credits_change"] - (
        delta["household_refundable_tax_credits_change"]
        - delta["state_refundable_credits_change"]
    )
    payroll = (
        delta["employer_payroll_tax_change"]
        + delta["employee_social_security_tax_change"]
        + delta["employee_medicare_tax_change"]
        + delta["self_employment_tax_change"]
    )
    benefits = (
        delta["household_benefits_change"]
        - delta["state_benefits_change"]
        - delta["tanf_change"]
    )
    return income_tax + payroll - benefits - delta["federal_health_change"]


def states_chart_change(delta):
    """Every state chart's total added up, from national ``net_fiscal_impact`` deltas.

    Mirrors ``buildStateRow`` in ``src/components/ShiftSweep.jsx``: state tax
    before refundable credits, less refundable state credits, the benefits in
    ``household_state_benefits``, the TANF those benefits don't already hold,
    and the states' health spending.
    """
    return (
        delta["state_tax_before_refundable_credits_change"]
        - delta["state_refundable_credits_change"]
        - delta["state_benefits_change"]
        - delta["tanf_charge_change"]
        - delta["state_health_change"]
    )


STATE_BREAKDOWN_VARIABLES = (
    "household_state_tax_before_refundable_credits",
    "household_refundable_state_tax_credits",
    "household_state_benefits",
    "household_tax_before_refundable_credits",
    "household_refundable_tax_credits",
    "household_benefits",
    "eitc",
    "snap",
    "capital_gains_tax",
    "alternative_minimum_tax",
    "net_investment_income_tax",
)


def state_revenue_components(sim, year=YEAR, health_frame=None):
    """Return per-state totals for state tax/credit/benefit lines.

    All variables are mapped to the household entity so per-state sums use the
    household weights and household state_code. TaxUnit-level variables like
    capital_gains_tax are aggregated across tax units within each household.
    With a ``health_frame`` (``health_tanf.household_frame`` of ``sim``), each
    state also gets its totals in ``HEALTH_TANF_KEYS``.
    """
    state_code = np.asarray(
        sim.calculate("state_code_str", map_to="household", period=year)
    )
    hh_weight = np.asarray(sim.calculate("household_weight", period=year), dtype=float)

    unique_states = np.unique(state_code)
    per_state = {str(code): {"household_weight": 0.0} for code in unique_states}
    for code in unique_states:
        mask = state_code == code
        per_state[str(code)]["household_weight"] = float(hh_weight[mask].sum())

    for var in STATE_BREAKDOWN_VARIABLES:
        values = np.asarray(
            sim.calculate(var, map_to="household", period=year), dtype=float
        )
        weighted = values * hh_weight
        for code in unique_states:
            mask = state_code == code
            per_state[str(code)][var] = float(weighted[mask].sum())

    if health_frame is not None:
        if not np.array_equal(np.asarray(health_frame["state"]).astype(str), state_code.astype(str)):
            raise ValueError("the health frame's households differ from the simulation's")
        for code, totals in health_tanf.state_totals(health_frame).items():
            per_state[code].update({key: totals[key] for key in HEALTH_TANF_KEYS})
            per_state[code]["tanf"] = totals["tanf"]

    return per_state


def state_revenue_delta(scenario_state, baseline_state):
    """Compute per-state delta dicts, aligned on state codes."""
    states = set(scenario_state) | set(baseline_state)
    out = {}
    for state in states:
        scen = scenario_state.get(state, {})
        base = baseline_state.get(state, {})
        keys = set(scen) | set(base)
        out[state] = {k: scen.get(k, 0.0) - base.get(k, 0.0) for k in keys}
        # Net state fiscal impact: state tax before refundable credits minus
        # state refundable credits minus state benefits.
        out[state]["state_net_change"] = (
            out[state].get("household_state_tax_before_refundable_credits", 0.0)
            - out[state].get("household_refundable_state_tax_credits", 0.0)
            - out[state].get("household_state_benefits", 0.0)
        )
    return out


def compute_ubi_amount(extra_budget, total_population):
    """Convert fiscal space into a flat per-person annual payment."""
    if extra_budget <= 0 or total_population <= 0:
        return 0.0
    return extra_budget / total_population
