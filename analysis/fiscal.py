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
"""

import numpy as np

from .constants import YEAR


def _hh_sum(sim, var):
    return float(sim.calculate(var, map_to="household", period=YEAR).sum())


def _tu_sum(sim, var):
    return float(sim.calculate(var, period=YEAR).sum())


def revenue_components(sim):
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
    """
    return {
        # --- Aggregates (use these for totals) ---
        "household_tax_before_refundable_credits": _hh_sum(
            sim, "household_tax_before_refundable_credits"
        ),
        "household_refundable_tax_credits": _hh_sum(
            sim, "household_refundable_tax_credits"
        ),
        "household_benefits": _hh_sum(sim, "household_benefits"),
        "employer_payroll_tax": _hh_sum(sim, "employer_payroll_tax"),
        # --- Federal income tax subcomponents (sum to fed income tax portion) ---
        "fed_income_tax_main_rates": _tu_sum(sim, "income_tax_main_rates"),
        "fed_capital_gains_tax": _tu_sum(sim, "capital_gains_tax"),
        "fed_alternative_minimum_tax": _tu_sum(sim, "alternative_minimum_tax"),
        "fed_net_investment_income_tax": _tu_sum(sim, "net_investment_income_tax"),
        "fed_nonrefundable_credits": _tu_sum(
            sim, "income_tax_capped_non_refundable_credits"
        ),
        # Catch-all for the three minor additive items inside
        # income_tax_before_refundable_credits that don't get their own line:
        # recapture of investment credit, unreported payroll tax,
        # qualified-retirement penalty. Near-zero in current law, but
        # exposed so the 5-bucket decomposition stays MECE for any reform.
        "fed_other_income_tax_items": (
            _tu_sum(sim, "recapture_of_investment_credit")
            + _tu_sum(sim, "unreported_payroll_tax")
            + _tu_sum(sim, "qualified_retirement_penalty")
        ),
        "fed_income_tax_before_refundable_credits": _tu_sum(
            sim, "income_tax_before_refundable_credits"
        ),
        # --- Payroll / self-employment ---
        "employee_social_security_tax": _hh_sum(sim, "employee_social_security_tax"),
        "employee_medicare_tax": _hh_sum(sim, "employee_medicare_tax"),
        "employer_social_security_tax": _hh_sum(sim, "employer_social_security_tax"),
        "employer_medicare_tax": _hh_sum(sim, "employer_medicare_tax"),
        "self_employment_tax": _hh_sum(sim, "self_employment_tax"),
        # --- State ---
        "state_tax_before_refundable_credits": _hh_sum(
            sim, "household_state_tax_before_refundable_credits"
        ),
        "state_refundable_credits": _hh_sum(
            sim, "household_refundable_state_tax_credits"
        ),
        "state_benefits": _hh_sum(sim, "household_state_benefits"),
        # --- Federal refundable credit components ---
        "income_tax_refundable_credits": _hh_sum(sim, "income_tax_refundable_credits"),
        "eitc": _hh_sum(sim, "eitc"),
        "refundable_ctc": _hh_sum(sim, "refundable_ctc"),
        # --- Benefit components ---
        "snap": _hh_sum(sim, "snap"),
        "ssi": _hh_sum(sim, "ssi"),
        "tanf": _hh_sum(sim, "tanf"),
        "wic": _hh_sum(sim, "wic"),
        "health_benefits": _hh_sum(sim, "household_health_benefits"),
        # --- Identity-check variables ---
        "household_market_income": _hh_sum(sim, "household_market_income"),
        "household_net_income": _hh_sum(sim, "household_net_income"),
    }


def net_fiscal_impact(components, baseline_components):
    """Return delta dictionary. Positive = more government revenue.

    Total change is computed from the *aggregates only* to avoid double-counting
    the subcomponents. Subcomponent deltas are reported for attribution.
    """
    delta = {
        f"{k}_change": components[k] - baseline_components[k] for k in components
    }

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

    return delta


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


def state_revenue_components(sim):
    """Return per-state totals for state tax/credit/benefit lines.

    All variables are mapped to the household entity so per-state sums use the
    household weights and household state_code. TaxUnit-level variables like
    capital_gains_tax are aggregated across tax units within each household.
    """
    state_code = np.asarray(
        sim.calculate("state_code_str", map_to="household", period=YEAR)
    )
    hh_weight = np.asarray(
        sim.calculate("household_weight", period=YEAR), dtype=float
    )

    unique_states = np.unique(state_code)
    per_state = {str(code): {"household_weight": 0.0} for code in unique_states}
    for code in unique_states:
        mask = state_code == code
        per_state[str(code)]["household_weight"] = float(hh_weight[mask].sum())

    for var in STATE_BREAKDOWN_VARIABLES:
        values = np.asarray(
            sim.calculate(var, map_to="household", period=YEAR), dtype=float
        )
        weighted = values * hh_weight
        for code in unique_states:
            mask = state_code == code
            per_state[str(code)][var] = float(weighted[mask].sum())

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
