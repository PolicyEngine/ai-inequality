"""AI scenarios calibrated to forecaster expectations, applied to US microdata.

The earlier experiment in `labor_capital_shift.py` sweeps an arbitrary grid
("shift 10/25/50% of labor income to capital") holding modelled market income
constant. That isolates a composition effect but has two problems: the sweep
points have no external referent, and holding output fixed rules out the
channel forecasters consider most likely -- that AI raises output *and* tilts
its composition toward capital.

This module replaces the arbitrary grid with the scenario set The Budget Lab
used in "How potential AI futures would play out in the current tax system"
(Iselin & Nunn, first published 2026-07-20, revised 2026-10-09), which in turn
draws its macro inputs from the forecaster survey in Karger et al. (2026).
Matching their calibration lets our results sit next to theirs; the
differences that remain are differences in model coverage, not in assumptions.

The 2026-10-09 revision (their AI-Fiscal release v1.0.1) corrected the 2030
labor shares. Version 1.0.0 took GDP growth from the Economists column of
Karger et al. Table 19 but the labor share from the pooled Total column of
Table 39 (Moderate 53.8%, Rapid 51.3%); v1.0.1 takes both from the Economists
column (Moderate 54.0%, Rapid 52.0%). Slow is 55.0% in both columns.

Three channels, following their Table 1:

1. Output.   Cumulative real GDP growth in excess of the CBO baseline path,
             g_Y = (1 + r_ai)^5 / G_CBO - 1.
2. Factor    The labor share of factor income falls from theta0_L to a
   shares.   scenario-specific theta1_L by 2030, implying
             g_K = (theta1_K (1 + g_Y) - theta0_K) / theta0_K   and
             g_L = (theta1_L (1 + g_Y) - theta0_L) / theta0_L.
3. Labor     A log-scale spread transform with parameter lambda = 1 +/- g_Y:
   inequality  ln Y1_i = mu1 + lambda (ln Y0_i - mu0),
             compressive below 1, expansive above 1.

Two calibration inputs sit outside their Table 1: the CBO cumulative baseline
and the pre-shock factor shares. The report gives the CBO path (2.2% growth in
2026, 1.8% a year after), and their AI-Fiscal repository commits both inputs
in `config/scenario_params.yaml`. With those values this module reproduces the
per-cell g_Y, g_K, g_L and lambda in their committed `cell_params` to machine
precision, for v1.0.0 and v1.0.1 alike; see `tests/test_ai_scenarios.py`,
which also re-derives both constants from the rounded Table 1 so they cannot
be quietly nudged.

Two things we model that the Budget Lab analysis does not, and one it models
that we cannot:

  + Benefits and poverty. Their model covers federal taxes plus tax-code
    outlays. Ours carries SNAP, SSI, TANF, WIC, Medicaid/CHIP/ACA and the SPM
    poverty measure, so scenarios can be scored on the bottom of the
    distribution rather than on revenue alone.
  + State tax and benefit systems, which they do not model at all.
  - Corporate income tax. PolicyEngine-US models the household sector only.
    Their headline number includes a corporate tax wedge computed outside
    their microsimulation, so our revenue totals are not comparable to theirs
    without netting it out. See `CORPORATE_TAX_SCOPE_NOTE`.

The `realization_rate` parameter is ours, not theirs. Their capital shock
assumes the realized share of capital income is unchanged by AI, which they
flag as a limitation: a wealthier post-AI world could realize more or less of
its capital income. Because unrealized gains, retained earnings and
accruals inside retirement accounts never reach the individual tax base,
that assumption is doing real work in the revenue estimate. Setting
realization_rate < 1 routes the corresponding fraction of the incremental
capital flow outside the taxable base entirely.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

#: CBO baseline real GDP growth: 2.2% in 2026 and 1.8% in each later year
#: (CBO publication 62105), as the Budget Lab report states and as AI-Fiscal
#: commits them (`cbo_baseline.g_2026`, `cbo_baseline.g_2027plus`).
CBO_GROWTH_2026 = 0.022
CBO_GROWTH_2027_ON = 0.018

#: Cumulative CBO real GDP growth factor over the 2025-2030 window,
#: (1 + g_2026) (1 + g_2027+)^4 = 1.0975947..., which the report describes as
#: 9.7% cumulative growth. AI-Fiscal computes it the same way (`cum_base` in
#: `code/02_params.R`). The four-decimal 1.0976 this module used before
#: reproduced the July Table 1, but it puts the revised Rapid capital growth at
#: 15.5949%, which rounds to 15.59% rather than the published 15.60%.
CBO_CUMULATIVE_GROWTH_FACTOR = (1 + CBO_GROWTH_2026) * (1 + CBO_GROWTH_2027_ON) ** 4

#: Pre-shock labor share of factor income, AI-Fiscal's
#: `shock.baseline_labor_share`. Their v1.0.1 config sources it to Karger et
#: al. (2026) Sec. 3, the 2025 nonfarm-business labor share baseline (55.48%),
#: rounded. The 53.7% the report cites is the measured share in the first
#: quarter of 2026, shown for historical context; it is not a model input.
BASELINE_LABOR_SHARE = 0.555

#: Horizon in years between the baseline and the scenario target year.
HORIZON_YEARS = 5

#: Scenario target year. The Budget Lab reports FY2030.
TARGET_YEAR = 2030

#: Sensitivity of the labor-inequality parameter to the size of the output
#: shock: lambda = 1 +/- k * g_Y. The Budget Lab uses k = 1.
INEQUALITY_SENSITIVITY = 1.0

CORPORATE_TAX_SCOPE_NOTE = (
    "PolicyEngine-US models household taxes and benefits. It has no corporate "
    "income tax, so revenue totals here exclude the corporate channel that "
    "contributes a large share of the Budget Lab's headline figure. Compare "
    "our totals to their individual income tax plus payroll lines, not to "
    "their all-in number."
)

#: Labor income sources. Positive values only: a loss is not income that AI can
#: redistribute.
LABOR_INCOME_VARS = ("employment_income", "self_employment_income")

#: Capital income sources. Wider than the list used by the pure-shift
#: experiment, which omitted passthrough business income and taxable retirement
#: distributions. The Budget Lab counts both as capital: passthrough profits are
#: split between factors (see PASSTHROUGH_CAPITAL_SHARE) and taxable pension and
#: IRA distributions are treated as capital income in their decomposition.
CAPITAL_INCOME_VARS = (
    "long_term_capital_gains",
    "short_term_capital_gains",
    "taxable_interest_income",
    "qualified_dividend_income",
    "non_qualified_dividend_income",
    "rental_income",
    "partnership_s_corp_income",
    "taxable_pension_income",
    "taxable_ira_distributions",
)

#: Retirement distributions are the most debatable members of the capital set.
#: Including them matters for the headline: distributions are taxed at ordinary
#: rates, so routing part of the capital shock through them raises measured
#: revenue and works against the "capital is taxed lightly" result. Defined
#: benefit pension income in particular is annuitised and does not track asset
#: returns year to year. Runners should report both variants rather than pick.
RETIREMENT_INCOME_VARS = (
    "taxable_pension_income",
    "taxable_ira_distributions",
)

CAPITAL_INCOME_VARS_EXCL_RETIREMENT = tuple(
    var for var in CAPITAL_INCOME_VARS if var not in RETIREMENT_INCOME_VARS
)

#: Passthrough profits mix capital and labor. Following Saez and Zucman (2020),
#: The Budget Lab's methodology splits them three ways: passive income 25% labor
#: / 75% capital, and active income 75% labor below the 99.99th wage percentile,
#: 25% labor on the excess. PolicyEngine-US carries no active/passive flag and
#: no percentile refinement is worth the survey data's resolution, so we apply
#: the single active-below-threshold rule to all of it. That under-assigns the
#: passive portion to capital, making our capital shock base slightly smaller
#: than theirs.
PASSTHROUGH_VAR = "partnership_s_corp_income"
PASSTHROUGH_CAPITAL_SHARE = 0.25

INEQUALITY_VARIANTS = ("compressive", "proportional", "expansive")


@dataclass(frozen=True)
class AIScenario:
    """One internally consistent AI future.

    Attributes:
        name: Scenario label ("Slow", "Moderate", "Rapid").
        annual_gdp_growth: Annualised real GDP growth under AI, from the
            Karger et al. (2026) survey.
        target_labor_share: Labor share of factor income in the target year.
        inequality: One of INEQUALITY_VARIANTS, or "none" to hold the labor
            distribution fixed while still applying the aggregate labor shock.
        realization_rate: Fraction of the incremental capital flow that reaches
            the individual tax base. 1.0 reproduces the Budget Lab assumption.
        hold_shares_fixed: If True, both factors grow at g_Y instead of at
            their own rates. This is the counterfactual the Budget Lab uses to
            show how much of the revenue gain the composition shift costs.
    """

    name: str
    annual_gdp_growth: float
    target_labor_share: float
    inequality: str = "proportional"
    realization_rate: float = 1.0
    hold_shares_fixed: bool = False

    baseline_labor_share: float = BASELINE_LABOR_SHARE
    cbo_growth_factor: float = CBO_CUMULATIVE_GROWTH_FACTOR
    horizon_years: int = HORIZON_YEARS
    inequality_sensitivity: float = INEQUALITY_SENSITIVITY

    def __post_init__(self):
        if self.inequality not in INEQUALITY_VARIANTS + ("none",):
            raise ValueError(
                f"inequality must be one of {INEQUALITY_VARIANTS + ('none',)}, "
                f"got {self.inequality!r}"
            )
        if not 0 <= self.realization_rate <= 2:
            raise ValueError(f"realization_rate {self.realization_rate} outside [0, 2]")

    @property
    def gdp_growth(self) -> float:
        """Cumulative real GDP growth in excess of the CBO baseline path."""
        compounded = (1 + self.annual_gdp_growth) ** self.horizon_years
        return compounded / self.cbo_growth_factor - 1

    @property
    def baseline_capital_share(self) -> float:
        return 1 - self.baseline_labor_share

    @property
    def target_capital_share(self) -> float:
        return 1 - self.target_labor_share

    @property
    def capital_growth(self) -> float:
        """Cumulative growth of capital income, in excess of baseline."""
        if self.hold_shares_fixed:
            return self.gdp_growth
        theta_k0 = self.baseline_capital_share
        return (self.target_capital_share * (1 + self.gdp_growth) - theta_k0) / theta_k0

    @property
    def labor_growth(self) -> float:
        """Cumulative growth of labor income, in excess of baseline."""
        if self.hold_shares_fixed:
            return self.gdp_growth
        theta_l0 = self.baseline_labor_share
        return (self.target_labor_share * (1 + self.gdp_growth) - theta_l0) / theta_l0

    @property
    def inequality_lambda(self) -> float:
        """Log-scale spread multiplier on the labor income distribution."""
        if self.inequality in ("proportional", "none"):
            return 1.0
        shift = self.inequality_sensitivity * self.gdp_growth
        return 1 + shift if self.inequality == "expansive" else 1 - shift

    @property
    def effective_capital_growth(self) -> float:
        """Capital growth actually routed into the taxable base."""
        return self.capital_growth * self.realization_rate

    @property
    def label(self) -> str:
        parts = [self.name]
        if self.hold_shares_fixed:
            parts.append("shares fixed")
        elif self.inequality != "none":
            parts.append(self.inequality)
        if self.realization_rate != 1.0:
            parts.append(f"realization {self.realization_rate:.0%}")
        return " / ".join(parts)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "annual_gdp_growth": self.annual_gdp_growth,
            "target_labor_share": self.target_labor_share,
            "baseline_labor_share": self.baseline_labor_share,
            "inequality": self.inequality,
            "realization_rate": self.realization_rate,
            "hold_shares_fixed": self.hold_shares_fixed,
            "gdp_growth": self.gdp_growth,
            "capital_growth": self.capital_growth,
            "effective_capital_growth": self.effective_capital_growth,
            "labor_growth": self.labor_growth,
            "inequality_lambda": self.inequality_lambda,
        }


#: The three survey scenarios, before choosing an inequality variant. Median
#: forecasts from the Economists column of Karger et al. (2026): Table 19 for
#: annualised 2025-30 GDP growth under AI, Table 39 for the 2030 labor share.
#: These are the Budget Lab's revised (2026-10-09, AI-Fiscal v1.0.1) inputs;
#: the July version used the Total column's labor shares, 53.8% for Moderate
#: and 51.3% for Rapid.
SCENARIO_INPUTS = {
    "Slow": {"annual_gdp_growth": 0.020, "target_labor_share": 0.550},
    "Moderate": {"annual_gdp_growth": 0.026, "target_labor_share": 0.540},
    "Rapid": {"annual_gdp_growth": 0.033, "target_labor_share": 0.520},
}


def build_scenario(name: str, **overrides) -> AIScenario:
    """Construct a scenario from the survey inputs, with optional overrides."""
    if name not in SCENARIO_INPUTS:
        raise KeyError(
            f"Unknown scenario {name!r}; expected one of {list(SCENARIO_INPUTS)}"
        )
    return AIScenario(name=name, **{**SCENARIO_INPUTS[name], **overrides})


def default_scenario_grid(realization_rate: float = 1.0) -> list[AIScenario]:
    """Growth-only counterfactual plus three inequality variants per scenario."""
    scenarios = []
    for name in SCENARIO_INPUTS:
        scenarios.append(
            build_scenario(
                name,
                inequality="none",
                hold_shares_fixed=True,
                realization_rate=realization_rate,
            )
        )
        for variant in INEQUALITY_VARIANTS:
            scenarios.append(
                build_scenario(
                    name, inequality=variant, realization_rate=realization_rate
                )
            )
    return scenarios


# ---------------------------------------------------------------------------
# Applying a scenario to a microsimulation
# ---------------------------------------------------------------------------


def _weighted(series):
    return (
        np.asarray(series, dtype=float),
        np.asarray(series.weights, dtype=float),
    )


def rescale_labor_income(values, weights, growth, lam):
    """Return labor income after an aggregate shock and a spread change.

    Applies ln Y1_i = mu1 + lambda (ln Y0_i - mu0) to units with positive
    labor income, with mu1 pinned so the weighted positive-subset aggregate
    hits (1 + growth) times its baseline. In levels this is
    Y1_i = C * Y0_i ** lambda, so C has a closed form and no solver is needed.

    Zero and negative values pass through unchanged: a spread transform on
    log income is undefined for them, and they are not income AI reallocates.
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    out = values.copy()

    positive = values > 0
    if not positive.any():
        return out

    base_total = float((values[positive] * weights[positive]).sum())
    target_total = base_total * (1 + growth)

    if lam == 1.0:
        out[positive] = values[positive] * (1 + growth)
        return out

    powered = values[positive] ** lam
    denominator = float((powered * weights[positive]).sum())
    if denominator <= 0:
        out[positive] = values[positive] * (1 + growth)
        return out

    out[positive] = powered * (target_total / denominator)
    return out


def labor_transform_constant(values, weights, growth, lam):
    """Return C in Y1 = C * Y0 ** lambda, or None when lambda is 1.

    Exposed because C fixes the income at which the spread transform is
    neutral: below it workers lose, above it they gain. That crossover is the
    most legible summary of what an inequality variant actually does to people,
    and it is not something the aggregate growth rate reveals.
    """
    if lam == 1.0:
        return None

    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    positive = values > 0
    if not positive.any():
        return None

    base_total = float((values[positive] * weights[positive]).sum())
    denominator = float((values[positive] ** lam * weights[positive]).sum())
    if denominator <= 0:
        return None
    return base_total * (1 + growth) / denominator


def labor_crossover_income(values, weights, growth, lam):
    """Income at which the labor transform leaves a worker unchanged.

    Solves C * Y ** lambda = Y, i.e. Y = C ** (1 / (1 - lambda)). Returns None
    for the proportional case, where every worker moves by the same percentage
    and no crossover exists.
    """
    constant = labor_transform_constant(values, weights, growth, lam)
    if constant is None or constant <= 0:
        return None
    return float(constant ** (1 / (1 - lam)))


def _labor_totals(sim, year):
    """Person-level positive labor income and its employment/SE split."""
    components = {}
    for var in LABOR_INCOME_VARS:
        values, weights = _weighted(sim.calculate(var, period=year))
        components[var] = (values, weights)

    positive_stack = np.stack(
        [np.where(values > 0, values, 0) for values, _ in components.values()]
    )
    combined = positive_stack.sum(axis=0)
    weights = next(iter(components.values()))[1]
    return components, combined, weights


def apply_ai_scenario(
    baseline,
    branch_name,
    scenario,
    year=TARGET_YEAR,
    capital_income_vars=CAPITAL_INCOME_VARS,
):
    """Create a branch with the scenario's labor and capital shocks applied.

    Labor and capital are shocked independently -- unlike the pure-shift
    experiment, modelled market income is not conserved, because the scenario
    includes output growth.

    The inequality transform applies to wage and self-employment income only.
    The labor portion of passthrough profits takes the aggregate labor growth
    rate without a spread change, because the passthrough split is itself an
    approximation and compounding a distributional assumption onto it would
    claim more precision than the split supports.

    Returns:
        (branch, diagnostics) where diagnostics records the aggregates that
        went in and out, so callers can verify the shock hit its targets.
    """
    branch = baseline.get_branch(branch_name)

    components, combined_labor, labor_weights = _labor_totals(baseline, year)
    baseline_labor_total = float((combined_labor * labor_weights).sum())

    shocked_labor = rescale_labor_income(
        combined_labor,
        labor_weights,
        scenario.labor_growth,
        scenario.inequality_lambda,
    )

    # Split the new person-level total back across employment and
    # self-employment in each person's original proportions, so that
    # self-employment tax treatment is preserved. Negative self-employment
    # income passes through untouched.
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(combined_labor > 0, shocked_labor / combined_labor, 1.0)
    for var, (values, _) in components.items():
        branch.set_input(var, year, np.where(values > 0, values * scale, values))

    capital_growth = scenario.effective_capital_growth
    baseline_capital_total = 0.0
    for var in capital_income_vars:
        values, weights = _weighted(baseline.calculate(var, period=year))
        positive = np.where(values > 0, values, 0)

        # Passthrough profits are part labor, part capital. Only the capital
        # part takes the capital shock; the labor part already moved with the
        # labor shock above is not double-counted here because passthrough
        # income is not in LABOR_INCOME_VARS -- so its labor portion instead
        # takes the labor growth rate.
        if var == PASSTHROUGH_VAR:
            capital_part = positive * PASSTHROUGH_CAPITAL_SHARE
            labor_part = positive * (1 - PASSTHROUGH_CAPITAL_SHARE)
            shocked = capital_part * (1 + capital_growth) + labor_part * (
                1 + scenario.labor_growth
            )
            baseline_capital_total += float((capital_part * weights).sum())
        else:
            shocked = positive * (1 + capital_growth)
            baseline_capital_total += float((positive * weights).sum())

        branch.set_input(var, year, np.where(values > 0, shocked, values))

    diagnostics = {
        "baseline_positive_labor": baseline_labor_total,
        "shocked_positive_labor": float((shocked_labor * labor_weights).sum()),
        "baseline_positive_capital": baseline_capital_total,
        "target_labor_growth": scenario.labor_growth,
        "target_capital_growth": scenario.capital_growth,
        "effective_capital_growth": capital_growth,
        "inequality_lambda": scenario.inequality_lambda,
        "capital_income_vars": list(capital_income_vars),
        "labor_crossover_income": labor_crossover_income(
            combined_labor,
            labor_weights,
            scenario.labor_growth,
            scenario.inequality_lambda,
        ),
    }
    achieved = (
        diagnostics["shocked_positive_labor"] / baseline_labor_total - 1
        if baseline_labor_total
        else 0.0
    )
    diagnostics["achieved_labor_growth"] = achieved
    diagnostics["labor_growth_error"] = achieved - scenario.labor_growth

    return branch, diagnostics


def modelled_factor_shares(
    sim, year=TARGET_YEAR, capital_income_vars=CAPITAL_INCOME_VARS
):
    """Labor and capital shares of positive modelled market income.

    These are shares of the income the microdata observes, not of national
    factor income. They differ from the national shares the scenarios are
    calibrated on because survey and tax microdata miss unrealized gains,
    retained earnings and imputed returns. Reported so the gap between the
    two concepts is visible rather than assumed away.

    The labor portion of passthrough profits counts toward labor, matching
    how the shock treats it.
    """
    _, combined_labor, labor_weights = _labor_totals(sim, year)
    labor_total = float((combined_labor * labor_weights).sum())

    capital_total = 0.0
    for var in capital_income_vars:
        values, weights = _weighted(sim.calculate(var, period=year))
        positive_total = float((np.where(values > 0, values, 0) * weights).sum())
        if var == PASSTHROUGH_VAR:
            capital_total += positive_total * PASSTHROUGH_CAPITAL_SHARE
            labor_total += positive_total * (1 - PASSTHROUGH_CAPITAL_SHARE)
        else:
            capital_total += positive_total

    total = labor_total + capital_total
    return {
        "positive_labor_income": labor_total,
        "positive_capital_income": capital_total,
        "modelled_labor_share": labor_total / total if total else 0.0,
        "modelled_capital_share": capital_total / total if total else 0.0,
    }


def social_security_cap_diagnostics(sim, year=TARGET_YEAR):
    """Share of wage income above the Social Security taxable maximum.

    The Budget Lab attributes their falling payroll receipts under expansive
    inequality to labor income crossing the cap. This exposes the same margin
    so the mechanism can be checked rather than asserted.
    """
    values, weights = _weighted(sim.calculate("employment_income", period=year))
    cap = float(
        sim.tax_benefit_system.parameters(
            f"{year}-01-01"
        ).gov.irs.payroll.social_security.cap
    )
    positive = np.where(values > 0, values, 0)
    above = np.maximum(values - cap, 0)
    positive_total = float((positive * weights).sum())
    return {
        "social_security_cap": cap,
        "wage_income_above_cap": float((above * weights).sum()),
        "share_of_wages_above_cap": (
            float((above * weights).sum()) / positive_total if positive_total else 0.0
        ),
        "share_of_workers_above_cap": (
            float(weights[values > cap].sum()) / float(weights[values > 0].sum())
            if float(weights[values > 0].sum())
            else 0.0
        ),
    }
