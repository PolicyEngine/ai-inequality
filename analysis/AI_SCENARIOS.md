# AI scenarios: method

How the forecaster-calibrated AI scenarios in `ai_scenarios.py` are built, what
they inherit from The Budget Lab's analysis, and where this model can say things
theirs cannot.

## What changed, and why

The original experiment (`labor_capital_shift.py`, `compute_shift_sweep.py`)
sweeps a grid: move 10%, 20% ... 100% of positive labor income into capital
income, holding modelled market income constant. It isolates a composition
effect cleanly, but two things limit what it can support:

- **No external referent.** "A 40% shift" is not a quantity anyone forecasts, so
  the sweep cannot be placed against anyone else's estimate, or against history.
- **Output is held fixed.** The channel forecasters consider most likely is that
  AI raises output *and* tilts its composition toward capital. A pure
  reallocation rules that out by construction, and the revenue answer is
  dominated by the missing growth term.

`ai_scenarios.py` keeps the sweep (it still answers "what does composition alone
do?") and adds a scenario set calibrated to the same forecasts The Budget Lab
used in [How potential AI futures would play out in the current tax
system](https://budgetlab.yale.edu/research/how-potential-ai-futures-would-play-out-current-tax-system)
(Iselin and Nunn, 20 July 2026), whose macro inputs come from the forecaster
survey in Karger et al. (2026), [NBER w35046](https://www.nber.org/papers/w35046).

Matching their calibration is deliberate: it makes the remaining differences
differences in *model coverage*, not in assumptions.

## The three channels

| Channel | Parameter | Source |
| --- | --- | --- |
| Output | `g_Y = (1 + r_ai)^5 / G_CBO - 1` | Karger et al. survey GDP growth |
| Factor shares | `g_K`, `g_L` implied by a 2030 labor-share target | Karger et al. labor share |
| Labor inequality | `lambda = 1 +/- g_Y` on log labor income | Budget Lab stylisation |

Given a target labor share `theta1_L` and pre-shock shares `theta0_L`,
`theta0_K`:

```
g_K = (theta1_K (1 + g_Y) - theta0_K) / theta0_K
g_L = (theta1_L (1 + g_Y) - theta0_L) / theta0_L
```

The inequality channel is a spread transform on log labor income,
`ln Y1_i = mu1 + lambda (ln Y0_i - mu0)`, with `mu1` pinned so the weighted
positive-labor aggregate lands on `(1 + g_L)` times baseline. In levels this is
`Y1_i = C Y0_i^lambda`, so `C` has a closed form and no solver is needed.
Applied at the person level, because the Social Security taxable maximum — the
margin the payroll result turns on — is a per-person threshold.

### Scenario inputs

| | Slow | Moderate | Rapid |
| --- | --- | --- | --- |
| Annual real GDP growth under AI | 2.0% | 2.6% | 3.3% |
| 2030 labor share of factor income | 55.0% | 53.8% | 51.3% |

## Two recovered constants

The report prints its derived growth rates but not two inputs they depend on:
the cumulative CBO baseline growth factor and the pre-shock factor shares. Both
are recoverable by inverting the published formulas against the nine derived
values in their Table 1:

- `CBO_CUMULATIVE_GROWTH_FACTOR = 1.0976` — the report states 9.7% cumulative.
- `BASELINE_LABOR_SHARE = 0.5550` — least-squares fit over all six published
  factor growth rates.

`test_ai_scenarios.py` reproduces all nine published values from these two
constants to within 0.005 percentage points, and re-derives the labor share by
grid search so the constants cannot be quietly nudged. Note that 55.5% is *not*
the 53.7% nonfarm business labor share the report cites for historical context;
that series has a narrower denominator.

## Every shocked variable reaches the tax base

Several of the variables the shock writes to are aggregates rather than raw
inputs, so it is worth confirming that overriding them actually moves taxable
income rather than being recomputed away. Traced against
`gov.irs.gross_income.sources` and `gov.household.market_income_sources` in
policyengine-us 1.764.6:

| Shocked variable | Route into `irs_gross_income` | Route into `household_market_income` |
| --- | --- | --- |
| `employment_income` | `irs_employment_income`, net of pre-tax contributions | listed source |
| `self_employment_income` | listed source | listed source |
| `long_term_capital_gains`, `short_term_capital_gains` | `capital_gains` | `capital_gains` |
| `qualified_dividend_income`, `non_qualified_dividend_income` | `ordinary_dividend_income`, `dividend_income` | same |
| `taxable_interest_income` | listed source | `interest_income` |
| `rental_income` | listed source | listed source |
| `partnership_s_corp_income` | listed source | listed source |
| `taxable_pension_income` | listed source | `pension_income` |
| `taxable_ira_distributions` | `taxable_retirement_distributions` | `retirement_distributions` |

No double counting: qualified and non-qualified dividends are the two
components of ordinary dividends, and short- and long-term gains are the two
components of capital gains. `tax_exempt_interest_income` is deliberately
outside the shocked set — it is not gross income. Because every shocked
variable reaches `household_market_income`, the net-income identity in
`fiscal.py` still closes; each run reports its residual.

## What this model adds

**Benefits and poverty.** The Budget Lab models federal taxes plus tax-code
outlays. This model carries SNAP, SSI, TANF, WIC, Medicaid, CHIP and ACA premium
tax credits, and reports the SPM poverty rate. A scenario that raises federal
revenue and raises poverty is a scenario their model cannot express.

**What household net income leaves out.** Two sets of programs are valued in the
model but kept out of household net income, and so out of the benefits and
revenue totals. Health programs (Medicaid, CHIP, ACA premium tax credits) are
out because `gov.simulation.include_health_benefits_in_net_income` defaults to
false. Head Start and Early Head Start are out because
`analysis/policyengine_runtime.py` drops `NET_INCOME_EXCLUDED_BENEFITS` from
`gov.household.household_benefits`, through a prebuilt tax-benefit system in
`managed_us_microsimulation` (`RUNTIME_REVISION` 3). policyengine-us 1.764.6
lists both programs there and values them at per-enrollee cost. Build p records
Head Start take-up (`takes_up_head_start_if_eligible`) but carries no Early
Head Start take-up flag, so the default counts every eligible person as
enrolled in Early Head Start. On the published runtime that came to $124B of
Early Head Start and $5B of Head Start in 2030 baseline net income
(`analysis/outputs/transfer_detail_buildp_published.json`). Each run records the names it removed as
`net_income_excluded_benefits` in its metadata. policyengine-us 2.x does not
list the two programs and counts them only when
`gov.simulation.include_head_start_benefits_in_net_income` is set (default
false), so there the runtime removes nothing. A 1.764.6 run built without this
runtime counts both and will not match the committed outputs. Neither program
is in SPM resources, so poverty is the same either way. The committed mechanism
sweep (`src/data/shiftSweepData.json`, committed 30 July 2026) predates the exclusion and
still counts both.

**State systems.** Per-state tax, refundable credit and benefit deltas. They do
not model states at all.

**Realization rate.** Their capital shock assumes the realized share of capital
income is unchanged by AI, which they flag as a limitation. Because unrealized
gains, retained earnings and accruals inside retirement accounts never reach the
individual tax base, that assumption carries weight in the revenue estimate.
`realization_rate` routes the corresponding fraction of the incremental capital
flow outside the taxable base; `1.0` reproduces their assumption.

**Capital scope sensitivity.** Taxable pension and IRA distributions are taxed at
ordinary rates, so including them in the capital set raises measured revenue and
works against the "capital is taxed lightly" result. Both variants are reported
rather than chosen.

**Shares-fixed counterfactual.** Both factors grown at `g_Y`, isolating what the
composition tilt costs. This is the comparison behind their finding that revenue
gains would be roughly twice as large with shares held at 2026 levels.

## What this model cannot say

**No corporate income tax.** PolicyEngine-US models the household sector. The
Budget Lab's headline number includes a corporate wedge computed outside their
microsimulation as `Delta R_CIT = X * (R_CIT_baseline / Y0_K)`. Totals here are
not comparable to their all-in figure — compare to their individual income tax
and payroll lines.

**Static.** No labor supply response, no behavioural response, no change in
avoidance or enforcement. The same is true of their tax microsimulation.

**Apportionment is narrower than theirs.** The incremental capital flow is
distributed proportional to households' existing positive capital income. Their
methodology document is explicit that they apportion by SCF-imputed *total*
wealth — cash, equities, bonds, retirement balances, life insurance, annuities,
trusts, real-estate funds, home equity and pass-through equity — and that
"pinning to a narrower base would push the distributional incidence further
toward the top". Ours is that narrower base, so it concentrates the shock more
than theirs by their own account. The data would support their approach:
`stock_assets` is populated for 31% of households and `net_worth` for 99.7%.

**Pass-through split is coarser than theirs.** Their rule is active/passive
aware — passive 25% labor / 75% capital, active 75% labor below the 99.99th wage
percentile and 25% on the excess. PolicyEngine-US carries no active/passive
flag, so we apply the single active-below-threshold rule throughout, which
under-assigns the passive portion to capital.

**Modelled shares are not national shares.** The scenarios are calibrated on
national factor shares (55.5% labor pre-shock). The microdata's own positive
market income is far more labor-weighted, because survey and tax data miss
unrealized gains, retained earnings and imputed returns. Growth rates derived
from national accounts are applied to the observed taxable flows — the same
choice the Budget Lab makes with the PUF. Both baseline shares are reported in
every run so the gap is visible rather than assumed away.

**Uprating.** Scenario growth is defined as growth *in excess of* the CBO
baseline path, applied on top of PolicyEngine's own uprating of the 2024
microdata to the target year. That is only exactly right where PolicyEngine's
uprating factors track CBO's projection; they are not guaranteed to.

**Gini is household-level and unequivalized.** `extract_results` takes the Gini
of `household_net_income` weighted by household weights, without an equivalence
scale. Changes against the same-year baseline are meaningful; the levels are not
comparable to published equivalized-income Ginis.

**Poverty is anchored, not relative.** `spm_unit_spm_threshold` is rebuilt from
each unit's composition, tenure and geography against base reference thresholds;
it does not respond to the income distribution inside the simulation. So the
poverty results hold the poverty line fixed at its baseline-uprated level while
incomes move. Over a five-year horizon in which output grows several percent
faster than baseline, a fully relative threshold would drift upward and poverty
would rise by more than reported here.

## Comparing totals with The Budget Lab

Their total is federal individual income tax plus payroll plus a corporate
wedge, with no states and no non-tax benefits. Ours is the household sector
across federal and state, net of refundable credits and the benefit programs in
household net income (everything but the health programs, Head Start and Early
Head Start; see above). Setting the two
side by side without an explicit bridge is wrong, so `reconcile_budget_lab.py`
builds one, using only our run output and parameters they publish.

The bridge rests on their corporate wedge, which their methodology document
states in full: `dR_CIT = X * (R_CIT_CBO / Y0_K) = X * tau_stat * eta * kappa`,
with a 21% statutory rate, `kappa` about 0.50 from NIPA, a CBO 2030 CIT anchor
near $486B, and `eta` "roughly one in practice" — an effective 10.5% on the
excess capital flow. Applying their formula to our capital flow estimates what
their corporate line would add to our estimate. It is not PolicyEngine
modelling corporate tax, and it inherits every constant-rate assumption they
list.

Inverting the same identity recovers the baseline realized taxable capital
income their run starts from, which they do not publish: about **$4.6T** against
our **$5.3T**, so our capital base is roughly 14% larger. That is the single
most useful cross-check available on our capital aggregate, and it explains most
of why our bridged totals exceed theirs.

## Identified next steps

**Asset-based apportionment.** Distribute the incremental capital flow by
household assets rather than by existing realized capital income, matching the
Budget Lab's SCF-imputed approach and reaching households that hold wealth but
realize nothing. The data supports it: in `populace_us_2024` at 2030,
`stock_assets` totals $35.7T and is non-zero for 31.2% of households,
`net_worth` totals $202.0T and is non-zero for 99.7%. (`bond_assets` is thin at
0.9% of households, and `household_business_assets_value` is not populated.)
The open modelling question is which person and which income type receives the
new flow in a household that currently reports none.

**Structural inequality channel.** The `lambda` parameter is a stylised stand-in
for "AI widens or narrows the wage distribution" with no evidence behind the
magnitude — the Budget Lab says as much. `compute_occupation_shock.py` in this
repo already maps Yale AI-Employment-Model task exposure scores onto CPS
occupation codes. Distributing the labor shock by measured exposure instead of
by a scalar spread parameter would replace an assumption with a measurement, and
would let the implied `lambda` be an output rather than an input.

This is also on their roadmap. Their methodology numbers the redistribution
rules S0 (proportional), S2 (compressive) and S3 (expansive), and notes that
"the omitted S1 is a planned future expansion involving occupation-level AI
exposure". We already hold the exposure mapping.

**Policy response.** `labor_capital_shift.py` recycles the net fiscal gain into a
flat UBI. Running that on the calibrated scenarios would answer the question the
revenue estimate raises but does not settle: whether the additional receipts are
enough to hold the bottom of the distribution harmless.

## Running it

```bash
python -m analysis.compute_ai_scenarios
```

Writes `analysis/outputs/ai_scenarios.json`: per scenario, the revenue
decomposition, inequality and poverty metrics, decile shares, per-state deltas,
Social Security cap diagnostics, and the shock diagnostics needed to confirm the
labor aggregate landed on its target.

Unit tests need no PolicyEngine install:

```bash
pytest analysis/tests/test_ai_scenarios.py -q
```
