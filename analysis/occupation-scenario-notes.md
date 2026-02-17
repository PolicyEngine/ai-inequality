# Occupation-based AI exposure scenarios

## Status: Research notes (not yet implemented)

## What we found

PolicyEngine-US has a `detailed_occupation_recode` variable (CPS field `POCCU2`) with 54 broad occupation categories (codes 0–53) at the person level.

### Data quality
- **54 unique codes** across ~50k person records
- Code 0 = not employed (~60M people, $0 mean employment income)
- Code 53 = likely "not in labor force" (~106M people, ~$4k mean income)
- Codes 1–52 = major occupation groups with meaningful employment income variation ($24k–$216k mean)
- Labels are **not included** in PolicyEngine — codes are raw integers from the CPS

### Limitation
The CPS ASEC uses ~50 major occupation groups, not the ~800 granular SOC codes that AI exposure studies typically use. Still enough for major-group-level analysis (e.g., "office/admin" vs "construction" vs "computer/math").

## Mapping codes to labels

The codes come from the CPS ASEC `POCCU2` field. We couldn't extract labels from Census PDFs programmatically. Next steps to get the mapping:

- Download the [CPS ASEC technical documentation](https://www.census.gov/programs-surveys/cps/technical-documentation/methodology/industry-and-occupation-classification.html) and find the POCCU2 table
- Check the [NBER CPS supplements page](https://www.nber.org/research/data/current-population-survey-cps-supplements-annual-demographic-file) for Stata/SAS dictionaries with value labels
- Or manually map by inspecting mean incomes per code against known occupation income distributions

## Scenario idea: differential AI wage shocks

1. Map the ~50 occupation codes to AI exposure scores using research like:
   - [Eloundou et al. (2023) "GPTs are GPTs"](https://arxiv.org/abs/2303.10130) — maps GPT exposure to occupations
   - [Acemoglu (2024)](https://www.nber.org/papers/w32487) — estimates 0.5–0.7% wage effects from AI exposure
   - [Webb (2020)](https://web.stanford.edu/~mwebb/webb_ai.pdf) — AI exposure by occupation using patent data

2. Apply differential shocks to `employment_income` by occupation code:
   - High-exposure occupations: cut income 20–30%
   - Low-exposure occupations: boost income 5–10%
   - Keep total GDP constant (pure redistribution scenario)

3. Run through PolicyEngine to measure inequality/poverty/revenue effects with existing tax-benefit system

## Alternative: simpler scenarios that don't need occupation codes

These can be done right now with the existing capital income doubling infrastructure:

- **Labor→capital shift at constant GDP**: reduce all employment income by X%, increase all capital income to compensate. Models aggregate automation without needing occupation granularity.
- **Unemployment spike**: zero out earnings for a random X% of workers, measure safety net adequacy.
- **Capital gains rate reform**: raise rates on the doubled-capital-income scenario to see how much inequality it offsets.
- **Expanded CTC/EITC vs UBI**: compare cost-equivalent alternatives to UBI for redistributing the capital windfall.
