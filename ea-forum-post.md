# How Do Policies Mediate AI's Impact on Economic Disempowerment?

_Exploring a research direction at the intersection of AI, inequality, and public policy_

## Summary

PolicyEngine is exploring research on how different policy interventions—current systems, UBI proposals, safety net expansions, capital taxation—would shape distributional outcomes under AI-driven economic change. Rather than forecasting AI's impacts ourselves, we'd provide microsimulation infrastructure for researchers to analyze how policies mediate the relationship between AI scenarios and economic disempowerment.

We're seeking feedback on whether this addresses important gaps, and who might find this infrastructure useful.

## Background

AI's economic impacts involve profound uncertainty at multiple levels:

**Macro uncertainty:** Growth forecasts range from Penn Wharton's 0.01pp TFP boost to scenarios of explosive growth from AI R&D automation.

**Micro uncertainty:** Fundamental disagreement over which workers benefit vs. are displaced. Some argue AI will democratize expertise and elevate middle-skill workers; others find it may reverse historical patterns by favoring lower-skill occupations while displacing higher-skill workers.

This uncertainty creates challenges for policy analysis. Yet policy choices—taxation, transfers, safety nets—will likely play a crucial role in mediating AI's distributional impacts.

## The Research Question

**How do different policy interventions shape distributional outcomes (income, consumption, wealth inequality) under various AI economic scenarios?**

This isn't about:

- Forecasting which AI scenario will occur
- Prescribing optimal policies
- Making claims about AI timelines

It's about:

- Providing infrastructure for translating AI economic scenarios into distributional outcomes under different policy regimes
- Enabling researchers to analyze policy mediation without building microsimulation infrastructure themselves
- Generating probability distributions over inequality metrics, not just point estimates

## Why This Might Matter for EA

**Economic disempowerment as a component of existential risk:** If a large fraction of the population has no economic value or resources in an AI-driven economy, this could create political instability, power concentration, or other dynamics relevant to long-term outcomes.

**Tractability:** While AI's economic trajectory is highly uncertain, policy responses are:

- More tractable to analyze (existing microsimulation methods)
- Potentially more influenceable than AI development trajectories
- Important regardless of which AI scenario unfolds

**Neglectedness:** Substantial work on AI economic impacts and growth models, but less on detailed microsimulation of policy mediation and distributional outcomes.

## Approach

**Microsimulation:** PolicyEngine maintains open-source tax-benefit models for the US, UK, and Canada that simulate how policies affect household-level outcomes.

**Probabilistic forecasting:** Rather than point estimates, generate probability distributions over inequality metrics using:

- Inputs: Forecasts from platforms like Metaculus (wage distributions, labor market shifts, etc.)
- Outputs: Distributions over post-policy metrics (Gini coefficients, poverty rates, etc.)

**Integration potential:** Combine with general equilibrium models (e.g., OG-USA) for comprehensive economic-fiscal analysis.

**Open infrastructure:** All models and code are open source, enabling researchers to test their own assumptions.

## Current Status

We've developed a preliminary framework ([site here](https://policyengine.github.io/ai-inequality/)) incorporating:

- Literature on AI growth, labor impacts, and inequality
- Policy scenarios (current systems, UBI variants, safety net expansions, capital taxation)
- Technical requirements for probabilistic microsimulation
- References from the Economics of Transformative AI curriculum

We're currently seeking feedback from researchers and funders on whether this addresses important gaps.

## How You Can Help

**Feedback welcome on:**

- Does this research direction address important gaps in understanding AI's distributional impacts?
- What AI economic scenarios would be most valuable to analyze?
- What policy questions are most decision-relevant?
- How should this integrate with forecasting platforms?

**Potentially useful if you:**

- Study AI economics and want distributional analysis of your scenarios
- Work on UBI or other policy proposals and want microsimulation under AI scenarios
- Run forecasting initiatives and want policy-level outputs
- Fund research at the intersection of AI, policy, and inequality

**Contact:** hello@policyengine.org or comment below

## Related Work

- Davidson (2021): [Could Advanced AI Drive Explosive Economic Growth?](https://www.openphilanthropy.org/research/could-advanced-ai-drive-explosive-economic-growth/)
- Trammell & Korinek (2023): [Economic Growth Under Transformative AI](https://philiptrammell.com/static/egtai_old.pdf)
- Korinek & Stiglitz (2021): [AI and Its Implications for Income Distribution](https://www.nber.org/papers/w28453)
- Acemoglu (2025): [The Simple Macroeconomics of AI](https://academic.oup.com/economicpolicy/article/40/121/13/7728473)

---

_Disclosure: I run PolicyEngine. This post represents early-stage exploration, not active research. We're genuinely uncertain whether this direction is valuable and welcome critical feedback._
