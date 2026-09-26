# AI, the tax system, and the bottom of the distribution

*Draft — HELD, not sent.*

*PolicyEngine · prepared with the AV Tax Policy Roundtable of 30 July 2026 in mind*

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
(Iselin and Nunn, 20 July) asks what AI-driven growth does to federal receipts,
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

**1. The tilt toward capital turns growth's poverty gain into a marginal
loss.** In the Rapid scenario — 3.3% annual real GDP growth either way —
poverty falls 1.09 points if the gains split at today's factor shares, and
rises 0.11 points with the tilt forecasters expect under a
distribution-neutral wage spread.

**2. The assumption with the least evidence behind it decides the household
outcome.** The Budget Lab is explicit that nobody knows whether AI compresses or
widens the wage distribution, so they span the range. Across that span in Rapid,
revenue moves 46% while poverty moves **3.26 points**, from 10.59% to 13.85%.

**3. Two definitional choices about the tax base matter more than the choice
between Slow, Moderate and Rapid.** How much AI capital income is realized, and
whether taxable retirement distributions count as capital, together range the
Rapid revenue estimate from −$60B to +$211B.

## Scenario results

Change against the same-year current-law baseline, 2030, $B. Baseline SPM
poverty 12.13%, net Gini 0.4678.

| Scenario | Revenue | Income tax | Payroll | State | Poverty | Δ pp | Net Gini |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Slow / shares fixed | +47 | +29 | +10 | +6 | 11.99% | −0.14 | 0.4680 |
| Slow / compressive | +3 | +3 | −1 | +1 | 12.01% | −0.12 | 0.4675 |
| Slow / proportional | +6 | +11 | −5 | +2 | 12.17% | +0.04 | 0.4685 |
| Slow / expansive | +10 | +19 | −10 | +3 | 12.33% | +0.20 | 0.4695 |
| Moderate / shares fixed | +287 | +178 | +61 | +35 | 11.46% | −0.67 | 0.4690 |
| Moderate / compressive | +125 | +65 | +33 | +15 | 11.18% | −0.95 | 0.4646 |
| Moderate / proportional | +144 | +114 | +7 | +21 | 12.00% | −0.13 | 0.4709 |
| Moderate / expansive | +165 | +164 | −20 | +28 | 12.84% | +0.71 | 0.4771 |
| Rapid / shares fixed | +576 | +358 | +121 | +71 | 11.04% | −1.09 | 0.4703 |
| Rapid / compressive | +173 | +98 | +34 | +24 | 10.59% | −1.54 | 0.4630 |
| Rapid / proportional | +211 | +193 | −16 | +36 | 12.24% | +0.11 | 0.4750 |
| Rapid / expansive | +252 | +294 | −70 | +48 | 13.85% | +1.72 | 0.4875 |

"Shares fixed" grows both factors at the scenario's GDP rate — the counterfactual
behind their finding that revenue gains would be roughly twice as large with
factor shares held at 2026 levels.

Both of their mechanisms reproduce. Within each scenario, moving compressive to
expansive raises income tax revenue through progressivity and lowers payroll
revenue as earnings cross the Social Security cap ($214,200 in 2030; at
baseline, 15.8% of wage income and 5.7% of workers sit above it).

The cap effect runs in both directions, which is worth stating because it is
easy to get backwards: under Rapid / compressive, aggregate labor income *falls*
0.94% and payroll receipts still *rise* $34B, because compression moves earnings
from above the cap to below it.

## What the tilt toward capital costs

| Scenario | Shares fixed | As forecast | Share kept |
| --- | --- | --- | --- |
| Slow | +$47B | +$6B | 14% |
| Moderate | +$287B | +$144B | 50% |
| Rapid | +$576B | +$211B | 37% |

Their "roughly twice as large" claim is specifically about Rapid; their grid
puts it at exactly 2.11×. Our 2.7× above is not directly comparable — it is an
all-government household total with no corporate wedge. Restated on their
federal-plus-corporate basis, our ratios are 3.13× / 1.65× / 2.00× against
their 3.62× / 1.71× / 2.11× — the two models agree on the tilt, scenario by
scenario. The larger household-total ratio mostly reflects the missing wedge:
their corporate wedge grows with the capital shock, so on their basis it
cushions the as-forecast cell. State taxes and the transfer system add to what
the tilt costs in dollars but leave the ratio essentially unchanged.

Their most extreme case checks out too: for Slow with compressive labor
inequality they report the gain 82% lower than with shares and distribution
unchanged; we get 93% lower.

An independent cross-check: they report an average tax rate of 21%–34% on gross
factor income in Rapid. Our Rapid / proportional turns a $760B market income
increase into $211B of receipts — **27.8%**, inside their band, from a different
model on different microdata.

## The two assumptions that dominate

**Realization.** Their capital shock assumes AI does not change the realized
share of capital income; they flag this as a limitation. Since unrealized gains,
retained earnings and accruals inside retirement accounts never reach the
individual tax base, it is doing real work. Holding Rapid / proportional fixed
and varying only how much of the incremental capital flow lands on a tax return:

| Realized share | Revenue |
| --- | --- |
| 0% | −$60B |
| 25% | +$7B |
| 50% | +$74B |
| 75% | +$142B |
| 100% (their assumption) | +$211B |

Linear to within a percent, with **breakeven at 22.5%**. Below that, the
household side of the fiscal system loses money on Rapid AI growth: labor
income still falls, and there is not enough taxable capital income reaching
returns to offset it. One important counterweight sits outside our model:
corporate tax is levied upstream of household realization, so the Budget Lab's
corporate wedge would still collect about $84B on the same shock regardless of
realization — enough to keep the all-in total (household, state and
corporate) positive, about +$24B, even at the 0% floor. Low realization shifts
the entire fiscal burden of an AI boom onto the corporate side; it does not
eliminate it.

Poverty is flat across the entire sweep, 12.24% to 12.27%. Whether AI's capital
gains are taxable moves the federal balance sheet by more than a
quarter-trillion dollars and moves poor households essentially not at all.

**What counts as capital.** Taxable pension and IRA distributions are taxed at
ordinary rates. Counting them as capital — which the Budget Lab does, and we
followed — raises the revenue estimate and softens the "capital is taxed
lightly" conclusion:

| Scenario | Full capital set | Excl. retirement | Difference |
| --- | --- | --- | --- |
| Slow | +$6B | −$4B | −$10B, sign flips |
| Moderate | +$144B | +$98B | −$46B |
| Rapid | +$211B | +$106B | −$105B |

Excluding them halves the Rapid estimate and flips Slow negative.

## Who gains, in wage terms

The inequality parameter is a spread transform on log wages, so each variant has
a crossover wage: below it workers lose, above it they gain.

| Rapid variant | λ | Crossover |
| --- | --- | --- |
| Compressive | 0.928 | $118,287 — workers below this gain |
| Expansive | 1.072 | $168,205 — workers below this lose |

Under Rapid / expansive, that puts the great majority of workers on the losing
side of a scenario that adds $252B to government net revenue.

## The transfer system

The Revenue column above nets transfers out; pulling them apart shows the
safety net doing exactly what it is built to do. Across the Rapid wage-spread
variants — identical aggregate labor income, only its distribution varies —
gross tax collections swing $122B, and automatic transfer responses absorb
$43B of that swing, about a third. Non-credit transfers alone swing **$28B**:
−$14B under compressive, as rising low-end wages pull households off
means-tested programs, to +$14B under expansive, as falling ones push them on.
SNAP carries $19B of the swing (−$9B to +$10B) and SSI $3B; Moderate shows the
same shape at −$8B to +$6B. Refundable credits contribute the remaining $15B
— a response their accounting does capture, through its tax-credit outlays
line. The $28B of program spending is the piece outside their model's
coverage.

This is the outlay side of the 3.26-point poverty span: the variant
uncertainty their report scores as a revenue question arrives at households as
a benefits question, and transfers expand exactly when workers lose. One scope
note: these totals carry no health-program response in either direction — the
model values Medicaid, CHIP and ACA subsidies, but a simulation switch, off in
these runs, keeps health coverage out of the net-income accounting.

## States

The State column of the scenario table is the other fiscal response their
federal model does not carry: **+$36B** under Rapid / proportional, doubling
from +$24B to +$48B across the wage-spread variants as progressive state codes
concentrate collections at the top the way federal brackets do. On the
Rapid / expansive cell we bridge to their headline below, state tax net of
state credits adds $47B — another 16% on top of the +$301B federal take.

That revenue concentrates almost entirely in a handful of states — California
+$10.0B, New York +$5.8B, New Jersey +$1.6B, Massachusetts +$1.3B, Maryland
+$1.2B.

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

We adopted their calibration exactly. Two inputs their report does not print —
the cumulative CBO baseline (1.0976, against their stated 9.7%) and the
pre-shock labor share (0.5550) — we recovered by inverting their published
formulas, reproducing all nine of their Table 1 derived values to within
0.005pp.

**We model and they do not:** SPM poverty, the transfer system (SNAP, SSI, TANF,
WIC — health programs, Head Start and Early Head Start are valued in the model
but excluded from these runs' net-income accounting), and state tax and benefit
codes.

**They model and we cannot:** the corporate income tax. Their microsimulation
covers federal individual income tax plus payroll; the corporate effect is a
single aggregate wedge layered on top, not attributed to households. The wedge
reduces to the capital growth rate times CBO's 2030 corporate anchor of $486B —
the capital base cancels — which their committed results confirm on all
eighteen cells.

Their code and full result grid are public (`Budget-Lab-Yale/AI-Fiscal`, MIT),
so the comparison can be made cell by cell on an identical accounting basis:
federal individual income tax net of refundable credits, plus payroll, plus
their wedge. On that basis:

| Rapid + expansive | Fed income tax (net) | Payroll | + their wedge | Total |
| --- | --- | --- | --- | --- |
| ours | +$287B | −$70B | +$84B | **+$301B** |
| theirs | +$195B | −$63B | +$84B | +$216B |

**We are 1.40× their estimate** — 4.6% of CBO 2030 revenue against their 3.3%.
And the divergence has a clean anatomy: **payroll responses agree remarkably
well in every cell** (ours −16/+34/−70 against theirs −11/+37/−63 across the
Rapid variants — two independent models putting similar wage distributions
against the same cap), while the gap is concentrated in the **income tax
response to the capital shock**: on the proportional cell, where the wage
spread is neutral and the income tax response is almost entirely the capital
shock, ours is 1.97× theirs (1.47× on this expansive cell). The absolute gap
says it more plainly: nearly constant at $93B / $95B / $91B across the three
Rapid variants, which is what a difference in the shared capital shock —
rather than in the varying wage channel — looks like. Three things point the
same way: their committed cell parameters put their baseline realized taxable
capital base at $4.51T against our $5.27T, 17% larger; allocation by realized
income rather than SCF total wealth, which they note is the more
top-concentrated choice; and our ordinary-rate retirement routing.

Their grid quantifies their "roughly twice as large" tilt claim at exactly
2.11× for Rapid; on the same federal-plus-corporate basis ours is 2.00×
(Slow 3.13× vs their 3.62×, Moderate 1.65× vs 1.71×) — agreement, not
divergence, with the same ordering across scenarios. Our household-total 2.72×
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
data-only change. Both runs predate the Head Start correction, so this
comparison uses the net-income accounting they shared. No scenario's revenue
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
