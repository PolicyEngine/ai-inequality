"""Shared constants for the analysis package."""

YEAR = 2026

CAPITAL_INCOME_VARS = [
    "long_term_capital_gains",
    "short_term_capital_gains",
    "taxable_interest_income",
    "qualified_dividend_income",
    "non_qualified_dividend_income",
    "rental_income",
]

# Flat employer-side payroll rate (6.2% SS + 1.45% Medicare).
# Exact for workers below the SS wage base, slightly overstates
# for high earners above the cap (where effective rate is only 1.45%).
EMPLOYER_PAYROLL_RATE = 0.0765
