"""Set a shifted branch's labor income where every formula reads it.

policyengine-us builds ``employment_income`` and ``self_employment_income`` by
adding a stored input (``employment_income_before_lsr``,
``self_employment_income_before_lsr``) to a labor supply response, which is
zero unless a reform sets an elasticity. Some formulas read the stored inputs
directly: at policyengine-us 1.764.6, the default TANF earned-income list
(``gov.hhs.tanf.cash.income.sources.earned``), Massachusetts's, Montana's and
South Carolina's TANF lists, and SNAP's self-employment income. A branch that
sets only the built variables leaves those formulas reading pre-shift earnings,
so this sets the stored input to the same values.

That is right only while the labor supply response is zero, so the stored input
equals the built variable. ``set_labor_income`` checks that in the baseline and
refuses otherwise. A dataset can also set the built variable itself and leave
the stored input at zero; the formulas that read the stored input then see zero
in the baseline, so the branch leaves it at zero too.
"""

from __future__ import annotations

import numpy as np

#: Suffix of the stored input policyengine-us adds a labor supply response to.
STORED_INPUT_SUFFIX = "_before_lsr"


def stored_labor_input(sim, variable):
    """The stored input ``variable`` adds, or None if the engine has none.

    A simulation without a tax-benefit system, such as a test stand-in, has none.
    """
    system = getattr(sim, "tax_benefit_system", None)
    stored = f"{variable}{STORED_INPUT_SUFFIX}"
    if system is None or stored not in system.variables:
        return None
    return stored


def set_labor_income(baseline, branch, variable, year, values):
    """Set ``variable`` on ``branch``, and its stored input when the data use it.

    Returns the stored input it set, or None. It sets none when the engine has
    no stored input, or when the baseline's stored input is zero for everyone
    while ``variable`` isn't, which means the dataset set ``variable`` itself.
    Refuses when the baseline's built ``variable`` differs from a stored input
    that holds data, as it does under a labor supply response: the shifted
    values would then mean different things in the two variables.
    """
    values = np.asarray(values, dtype=float)
    stored = stored_labor_input(baseline, variable)
    if stored is not None:
        built = np.asarray(baseline.calculate(variable, period=year), dtype=float)
        before = np.asarray(baseline.calculate(stored, period=year), dtype=float)
        if built.any() and not before.any():
            stored = None
        else:
            gap = np.abs(built - before)
            if gap.size and float(gap.max()) > 1e-6:
                raise ValueError(
                    f"{variable} differs from {stored} by up to {float(gap.max()):,.2f} "
                    "in the baseline, so a labor supply response is active; the shift "
                    "can't set both"
                )
    if stored is not None:
        branch.set_input(stored, year, values)
    branch.set_input(variable, year, values)
    return stored
