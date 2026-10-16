# AI, the tax system, and the bottom of the distribution

*Draft — HELD, not sent.*

*PolicyEngine · prepared with the AV Tax Policy Roundtable of 30 July 2026 in mind*

**Revision, 16 October 2026.** The Budget Lab revised its report on 9 October.
As first published, it took GDP growth from the economists in the Karger et al.
survey but the 2030 labor shares from all respondents pooled; the revision
takes both from the economists, so the Moderate labor share rises from 53.8% to
54.0% and the Rapid share from 51.3% to 52.0%. It also replaces CBO's rounded
2030 ratios, which lowers their corporate wedge by 1.8% in every cell. We reran
every scenario on the same model and data with the revised inputs, and the
comparison below is against their revised result grid. Rapid aggregate labor
income now grows 0.41% instead of falling 0.94%, and that changes four of our
findings. The tilt toward capital now erodes most of growth's poverty gain
rather than reversing it: under Rapid / proportional, poverty falls 0.17
points where we had reported a 0.11-point rise. Revenue stays positive even if
none of the new capital income is realized (+$26B), where we had reported a
loss below a 22.5% realized share. Excluding retirement distributions now cuts
the Rapid estimate by about a third, not half. And the two tax-base choices
now span nearly as much of the Rapid estimate as the move from Slow to Rapid,
rather than more. Rapid / proportional revenue moves from +$211B to +$272B;
our bridged Rapid / expansive headline moves from +$301B to +$344B, against
their $216B, now $246B. Slow and the shares-fixed counterfactuals move by less
than $0.1B. The September correction below describes the run before this
revision.

**Correction, 26 September 2026.** Earlier versions of this memo counted Head
Start and Early Head Start in household net income. The model version they ran
on, policyengine-us 1.764.6, values both programs at their per-enrollee cost.
The microdata carry a modeled Head Start take-up flag but none for Early Head
Start, so every eligible child under three and every eligible pregnant person counted as
enrolled in Early Head Start. That put $124B of Early Head Start and $5B of
Head Start into 2030 baseline net income, and because eligibility is
income-tested, the amount rose and fell with the wage shocks. We reran every
scenario on the same model and data with both programs kept out of net income,
as current PolicyEngine does. Neither program counts toward SPM resources, so
every poverty figure is unchanged. Every tax cell is also unchanged. Six of the
twelve revenue cells move, by $2B to $8B; net Gini levels rise by about 0.005;
across the Rapid wage-spread variants, revenue now moves 46%, not 36%; and the
transfer system absorbs $43B of the Rapid gross-tax swing, about a third, where
we had reported $57B, nearly half. This version also corrects one explanation:
our household-total tilt ratio (2.72×) exceeds our ratio on their
federal-plus-corporate basis (2.00×) mainly because that basis carries the
Budget Lab's corporate wedge, not because of state taxes and transfers.

The Budget Lab's [How potential AI futures would play out in the current tax
system](https://budgetlab.yale.edu/research/how-potential-ai-futures-would-play-out-current-tax-system)
(Iselin and Nunn, 20 July, revised 9 October) asks what AI-driven growth does to federal receipts,
and finds the answer is less than you would hope, because growth skewed toward
capital is growth the tax base collects less of.

PolicyEngine has been running an open labor-to-capital income-shift analysis
since last fall — an experiment that sweeps a 0–100% shift of labor income into
capital income and measures the revenue, poverty and inequality consequences at
each step, live at
[policyengine.org/us/ai-inequality/income-shift](https://policyengine.org/us/ai-inequality/income-shift).
The Budget Lab's report gave that work an external anchor. We extended the same
framework to the Karger et al. scenarios they calibrate to, deliberately
adopting their calibration so that what differs is model coverage rather than
assumptions. PolicyEngine carries the transfer system, the SPM poverty measure,
and the state codes their tax model does not. Three things follow that a
revenue-only score cannot show.

**1. The tilt toward capital erodes most of growth's poverty gain.** In the
Rapid scenario — 3.3% annual real GDP growth either way — poverty falls 1.09
points if the gains split at today's factor shares, and only 0.17 points with
the tilt forecasters expect under a distribution-neutral wage spread.

**2. The assumption with the least evidence behind it decides the household
outcome.** The Budget Lab is explicit that nobody knows whether AI compresses or
widens the wage distribution, so they span the range. Across that span in Rapid,
revenue moves 34% while poverty moves **3.23 points**, from 10.49% to 13.72%.

**3. Two definitional choices about the tax base matter nearly as much as the
choice between Slow and Rapid.** How much AI capital income is realized, and
whether taxable retirement distributions count as capital, together range the
Rapid revenue estimate from +$26B to +$272B, a $245B span against the $265B
between the Slow and Rapid estimates.

## Scenario results

Change against the same-year current-law baseline, 2030, $B. Baseline SPM
poverty 12.13%, net Gini 0.4678.

| Scenario | Revenue | Income tax | Payroll | State | Poverty | Δ pp | Net Gini |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Slow / shares fixed | +47 | +29 | +10 | +6 | 11.99% | −0.14 | 0.4680 |
| Slow / compressive | +3 | +3 | −1 | +1 | 12.01% | −0.12 | 0.4675 |
| Slow / proportional | +7 | +11 | −5 | +2 | 12.17% | +0.04 | 0.4685 |
| Slow / expansive | +10 | +19 | −10 | +3 | 12.33% | +0.20 | 0.4695 |
| Moderate / shares fixed | +287 | +178 | +61 | +35 | 11.46% | −0.67 | 0.4690 |
| Moderate / compressive | +141 | +72 | +39 | +17 | 11.11% | −1.02 | 0.4644 |
| Moderate / proportional | +161 | +121 | +13 | +22 | 11.89% | −0.24 | 0.4706 |
| Moderate / expansive | +182 | +172 | −13 | +29 | 12.77% | +0.64 | 0.4769 |
| Rapid / shares fixed | +576 | +358 | +121 | +71 | 11.04% | −1.09 | 0.4703 |
| Rapid / compressive | +233 | +124 | +58 | +30 | 10.49% | −1.64 | 0.4620 |
| Rapid / proportional | +272 | +220 | +7 | +42 | 11.96% | −0.17 | 0.4742 |
| Rapid / expansive | +313 | +322 | −47 | +54 | 13.72% | +1.59 | 0.4867 |

"Shares fixed" grows both factors at the scenario's GDP rate — the counterfactual
behind their finding that revenue gains would be nearly twice as large with
factor shares held at 2026 levels.

Both of their mechanisms reproduce. Within each scenario, moving compressive to
expansive raises income tax revenue through progressivity and lowers payroll
revenue as earnings cross the Social Security cap ($214,200 in 2030; at
baseline, 15.8% of wage income and 5.7% of workers sit above it).

The cap effect runs in both directions, which is worth stating because it is
easy to get backwards: every Rapid variant grows aggregate labor income by the
same 0.41%, yet payroll receipts *rise* $58B under compression, against $7B
when that growth is spread proportionally, because compression moves earnings
from above the cap to below it.

## What the tilt toward capital costs

| Scenario | Shares fixed | As forecast | Share kept |
| --- | --- | --- | --- |
| Slow | +$47B | +$7B | 14% |
| Moderate | +$287B | +$161B | 56% |
| Rapid | +$576B | +$272B | 47% |

Their "nearly twice as large" claim is specifically about Rapid; their grid
puts it at 1.79×. Our 2.1× above is not directly comparable — it is an
all-government household total with no corporate wedge. Restated on their
federal-plus-corporate basis, our ratios are 3.16× / 1.53× / 1.72× against
their 3.68× / 1.58× / 1.79× — the two models agree on the tilt, scenario by
scenario. The larger household-total ratio mostly reflects the missing wedge:
their corporate wedge grows with the capital shock, so on their basis it
cushions the as-forecast cell. State taxes and the transfer system add to what
the tilt costs in dollars but leave the ratio essentially unchanged.

Their most extreme case checks out too: for Slow with compressive labor
inequality they report the gain 82% lower than with shares and distribution
unchanged; we get 93% lower.

An independent cross-check: they report an average tax rate of 21%–32% on gross
factor income in Rapid. Our Rapid / proportional turns an $887B market income
increase into $272B of receipts — **30.7%**, inside their band, from a different
model on different microdata.

## The two assumptions that dominate

**Realization.** Their capital shock assumes AI does not change the realized
share of capital income; they flag this as a limitation. Since unrealized gains,
retained earnings and accruals inside retirement accounts never reach the
individual tax base, it is doing real work. Holding Rapid / proportional fixed
and varying only how much of the incremental capital flow lands on a tax return:

| Realized share | Revenue |
| --- | --- |
| 0% | +$26B |
| 25% | +$87B |
| 50% | +$148B |
| 75% | +$209B |
| 100% (their assumption) | +$272B |

Linear to within a percent, and **positive all the way down**: Rapid labor
income grows 0.41% on the revised inputs, so the household side of the fiscal
system still gains on Rapid AI growth when none of the new capital income
reaches a return. (On their July inputs, under which Rapid labor income fell,
this sweep turned negative below a 22.5% realized share.) One counterweight
sits outside our model: corporate tax is levied upstream of household
realization, so the Budget Lab's corporate wedge would still collect about $74B
on the same shock regardless of realization, lifting the all-in total
(household, state and corporate) to about +$101B at the 0% floor. Low
realization shifts the fiscal gain from an AI boom toward the corporate side; it
does not eliminate it.

Poverty is flat across the entire sweep, 11.96% to 12.03%. Whether AI's capital
gains are taxable moves net revenue by roughly a quarter-trillion dollars
($245B) and moves poor households essentially not at all.

**What counts as capital.** Taxable pension and IRA distributions are taxed at
ordinary rates. Counting them as capital — which the Budget Lab does, and we
followed — raises the revenue estimate and softens the "capital is taxed
lightly" conclusion:

| Scenario | Full capital set | Excl. retirement | Difference |
| --- | --- | --- | --- |
| Slow | +$7B | −$4B | −$10B, sign flips |
| Moderate | +$161B | +$118B | −$43B |
| Rapid | +$272B | +$177B | −$95B |

Excluding them cuts the Rapid estimate by about a third and flips Slow
negative.

## Who gains, in wage terms

The inequality parameter is a spread transform on log wages, so each variant has
a crossover wage: below it workers lose, above it they gain.

| Rapid variant | λ | Crossover |
| --- | --- | --- |
| Compressive | 0.928 | $142,922 — workers below this gain |
| Expansive | 1.072 | $139,212 — workers below this lose |

Under Rapid / expansive, that puts the great majority of workers on the losing
side of a scenario that adds $313B to government net revenue.

## The transfer system

The Revenue column above nets transfers out; pulling them apart shows the
safety net doing exactly what it is built to do. Across the Rapid wage-spread
variants — identical aggregate labor income, only its distribution varies —
gross tax collections swing $123B, and automatic transfer responses absorb
$43B of that swing, about a third. Non-credit transfers alone swing **$28B**:
−$15B under compressive, as rising low-end wages pull households off
means-tested programs, to +$13B under expansive, as falling ones push them on.
SNAP carries $19B of the swing (−$10B to +$9B) and SSI $3B; Moderate shows the
same shape at −$8B to +$6B. Refundable credits contribute the remaining $15B
— a response their accounting does capture, through its tax-credit outlays
line. The $28B of program spending is the piece outside their model's
coverage.

This is the outlay side of the 3.23-point poverty span: the variant
uncertainty their report scores as a revenue question arrives at households as
a benefits question, and transfers expand exactly when workers lose. One scope
note: these totals carry no health-program response in either direction — the
model values Medicaid, CHIP and ACA subsidies, but a simulation switch, off in
these runs, keeps health coverage out of the net-income accounting.

## States

The State column of the scenario table is the other fiscal response their
federal model does not carry: **+$42B** under Rapid / proportional, nearly
doubling from +$30B to +$54B across the wage-spread variants as progressive
state codes concentrate collections at the top the way federal brackets do. On
the Rapid / expansive cell we bridge to their headline below, state tax net of
state credits adds $54B — another 16% on top of the +$344B federal take.

That revenue concentrates almost entirely in a handful of states — California
+$11.6B, New York +$6.4B, New Jersey +$2.0B, Massachusetts +$1.5B, Maryland
+$1.4B.

Seven states collect **exactly nothing** from the capital shock: Florida,
Nevada, New Hampshire, South Dakota, Tennessee, Texas and Wyoming. Alaska
rounds to zero.

Washington is the instructive exception. It has no income tax either, but its
capital gains excise tax collects **+$1.1B** — more than all seven
zero-collecting states combined, many times over. A state that taxes capital
gains participates in an AI capital boom; a state that taxes only wages does
not participate in an economy where wages are the shrinking share.

Whatever AI does to the federal fiscal picture, it does almost nothing for most
of the states that would bear the cost of absorbing displaced workers — unless
they have a capital tax to collect it with.

## Scope and method

We adopted their calibration exactly, as revised on 9 October. The two inputs
outside their Table 1 — the cumulative CBO baseline, 1.022 × 1.018⁴ from the
CBO path their report states, and the pre-shock labor share of 0.555 their
repository commits — reproduce their committed per-cell growth rates to machine
precision, and all nine of their Table 1 derived values to within 0.005pp.

**We model and they do not:** SPM poverty, the transfer system (SNAP, SSI, TANF,
WIC — health programs, Head Start and Early Head Start are valued in the model
but excluded from these runs' net-income accounting), and state tax and benefit
codes.

**They model and we cannot:** the corporate income tax. Their microsimulation
covers federal individual income tax plus payroll; the corporate effect is a
single aggregate wedge layered on top, not attributed to households. The wedge
reduces to the capital growth rate times CBO's 2030 corporate anchor of $477B —
the capital base cancels — which their committed results confirm on all
eighteen cells.

Their code and full result grid are public (`Budget-Lab-Yale/AI-Fiscal`, MIT),
so the comparison can be made cell by cell on an identical accounting basis:
federal individual income tax net of refundable credits, plus payroll, plus
their wedge. On that basis:

| Rapid + expansive | Fed income tax (net) | Payroll | + their wedge | Total |
| --- | --- | --- | --- | --- |
| ours | +$316B | −$47B | +$74B | **+$344B** |
| theirs | +$220B | −$48B | +$74B | +$246B |

**We are 1.39× their estimate** — 5.2% of CBO 2030 revenue against their 3.7%.
And the divergence has a clean anatomy: **payroll responses agree remarkably
well in every cell** (ours +7/+58/−47 against theirs +5/+54/−48 across the
Rapid variants — two independent models putting similar wage distributions
against the same cap), while the gap is concentrated in the **income tax
response to the capital shock**: on the proportional cell, where the wage
spread is neutral and the income tax response is almost entirely the capital
shock, ours is 1.82× theirs (1.44× on this expansive cell). The absolute gap
says it more plainly: nearly constant at $98B / $100B / $96B across the three
Rapid variants, which is what a difference in the shared capital shock —
rather than in the varying wage channel — looks like. Three things point the
same way: their committed cell parameters put their baseline realized taxable
capital base at $4.51T against our $5.27T, 17% larger; allocation by realized
income rather than SCF total wealth, which they note is the more
top-concentrated choice; and our ordinary-rate retirement routing.

Their grid quantifies their "nearly twice as large" tilt claim at 1.79× for
Rapid; on the same federal-plus-corporate basis ours is 1.72× (Slow 3.16× vs
their 3.68×, Moderate 1.53× vs 1.58×) — agreement, not divergence, with the
same ordering across scenarios. Our household-total 2.12×
runs higher mainly because that basis has no corporate wedge, which grows with
the capital shock and so cushions the as-forecast cell; states and transfers
add to the tilt's dollar cost but barely move the ratio. One basis caveat:
their "82% lower" figure for Slow/compressive uses a shares-fixed *compressive*
counterfactual; ours uses shares-fixed proportional, so our 93% is not exactly
the same comparison.

`reconcile_budget_lab.py` reproduces every number in this section from our run
output and their committed workbook. The borrowed wedge is not PolicyEngine
modelling corporate tax, and it inherits every constant-rate assumption they
list.

**Both static:** no labor supply response, no behavioural response, no change in
avoidance or enforcement.

**Known limits of ours.** The incremental capital flow is apportioned in
proportion to households' existing realized capital income; they apportion by
SCF-imputed assets, which reaches households holding wealth but realizing
nothing, so ours concentrates the shock more than theirs. Poverty is anchored,
not relative — SPM thresholds do not respond to the simulated distribution, so a
fully relative line would show larger increases. Gini is household-level and
unequivalized, so changes are meaningful but levels are not comparable to
published series.

**Levels versus changes.** PolicyEngine's absolute SPM poverty level sits above
the Census published rate — a known calibration gap, and one that moves whenever
BLS revises thresholds (as it did for 2019–2024 in July 2026). Every poverty
figure here is therefore reported as a change against a same-year baseline
computed on the identical threshold. Because the threshold is identical in
baseline and scenario, those changes are close to unaffected by the level gap;
the levels are context, the deltas are the result.

**Stability across data builds.** These results were first computed on the
prior populace build (build o, 22 July) and rerun on build p (28 July, with
revised capital gains calibration) under the identical model version — a
data-only change. Both runs predate the Head Start correction and the October
revision, so this comparison uses the net-income accounting and the July
scenario inputs they shared. No scenario's revenue
estimate moved by more than $5.9B:
Moderate and Rapid by at most 2.8%, and the Slow cells, whose revenue changes
are as small as $3B, by up to 12%. No poverty change moved by more than 0.11pp,
and no conclusion changed. The recalibration's
visible effect is distributional: the baseline top-1% net income share rises
from 8.77% to 9.00% (9.06% after the correction), and New York's state take
under Rapid rises from $3.8B to $5.8B as more of the gains land where they are
taxed.

**Diagnostics.** The net-income identity closes to $0.000B in every scenario,
and the labor shock hits its target aggregate to within 2e-16.

## Reproducibility

Everything above runs from open source against openly published microdata:
policyengine-us 1.764.6, policyengine.py 5.0.1, populace-us `populace_us_2024`
(certified build `populace-us-2024-buildp-sparse-rmloss100-cae8640`), with
Head Start and Early Head Start kept out of household net income. The
Budget Lab notes their PUF-based data cannot be released publicly, so this is a
complement rather than a competitor: anyone can rerun these scenarios, or score
a different reform against them.

Code: `PolicyEngine/ai-inequality`, `analysis/ai_scenarios.py`.
Method notes: `analysis/AI_SCENARIOS.md`.
