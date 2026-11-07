"""California's revenue under the labor-to-capital income shift.

Runs the sweep's shift (``labor_capital_shift._apply_shift``) and fiscal
accounting (``fiscal.revenue_components``, ``fiscal.state_revenue_components``)
on whatever PolicyEngine bundle is installed, with one fresh microsimulation
per level, the way ``compute_shift_sweep`` does. On top of the sweep payload it
records:

* California's employee SDI contribution. The sweep's state measure,
  ``household_state_tax_before_refundable_credits``, adds state income tax and
  use tax only, so this wage levy sits outside it.
* California's change split by within-state market-income group, with the
  labor income each group gives up and the capital income it receives.
* Federal net revenue, as the all-government total less every state's net
  change.

Usage:
    python -m analysis.california_shift [--levels 0.1,0.2,0.5,1.0] [--out PATH]
"""

from __future__ import annotations

import argparse
import gc
import json
import os
from importlib.metadata import PackageNotFoundError, version

import numpy as np

from .constants import CAPITAL_INCOME_VARS, YEAR
from .fiscal import (
    net_fiscal_impact,
    revenue_components,
    state_revenue_components,
    state_revenue_delta,
)
from .policyengine_runtime import managed_us_microsimulation, policyengine_bundle

DEFAULT_LEVELS = [0.10, 0.20, 0.50, 1.00]
STATE = "CA"
SDI_VARIABLE = "ca_employee_state_disability_insurance_contribution"
LABOR_VARS = ["employment_income", "self_employment_income"]

#: Within-California groups by baseline household market income, as
#: (label, lower weighted percentile, upper weighted percentile).
GROUPS = [
    ("Bottom 50%", 0.0, 0.5),
    ("50th to 90th percentile", 0.5, 0.9),
    ("90th to 99th percentile", 0.9, 0.99),
    ("Top 1%", 0.99, 1.0000001),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def _package_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _hh(sim, var):
    return np.asarray(sim.calculate(var, map_to="household", period=YEAR), dtype=float)


def _household_frame(sim):
    """Household arrays needed for the California accounting."""
    frame = {
        "state": np.asarray(
            sim.calculate("state_code_str", map_to="household", period=YEAR)
        ).astype(str),
        "weight": np.asarray(sim.calculate("household_weight", period=YEAR), dtype=float),
        "market_income": _hh(sim, "household_market_income"),
        "state_tax": _hh(sim, "household_state_tax_before_refundable_credits"),
        "state_credits": _hh(sim, "household_refundable_state_tax_credits"),
        "state_benefits": _hh(sim, "household_state_benefits"),
        "labor": sum(_hh(sim, v) for v in LABOR_VARS),
        "capital": sum(_hh(sim, v) for v in CAPITAL_INCOME_VARS),
    }
    try:
        frame["sdi"] = _hh(sim, SDI_VARIABLE)
    except Exception as exc:  # noqa: BLE001 - record, do not fail the run
        print(f"  {SDI_VARIABLE} unavailable: {exc}", flush=True)
        frame["sdi"] = np.zeros_like(frame["weight"])
    frame["state_net"] = frame["state_tax"] - frame["state_credits"] - frame["state_benefits"]
    return frame


def _weighted_rank(values, weights):
    """Weighted percentile rank (0-1) of each household within its group."""
    order = np.argsort(values, kind="mergesort")
    cum = np.cumsum(weights[order])
    ranks = np.empty_like(cum)
    ranks[order] = (cum - weights[order] / 2) / cum[-1]
    return ranks


def _baseline_concentration(base):
    """Shares of California labor and capital income by market-income group."""
    mask = base["state"] == STATE
    w = base["weight"][mask]
    ranks = _weighted_rank(base["market_income"][mask], w)
    labor = np.clip(base["labor"][mask], 0, None)
    capital = np.clip(base["capital"][mask], 0, None)
    rows = []
    for label, lo, hi in GROUPS:
        g = (ranks >= lo) & (ranks < hi)
        rows.append(
            {
                "group": label,
                "households_m": float(w[g].sum() / 1e6),
                "labor_income_share": float((labor[g] * w[g]).sum() / (labor * w).sum()),
                "capital_income_share": float(
                    (capital[g] * w[g]).sum() / (capital * w).sum()
                ),
                "mean_market_income": float(
                    (base["market_income"][mask][g] * w[g]).sum() / w[g].sum()
                ),
            }
        )
    return {
        "households_m": float(w.sum() / 1e6),
        "labor_income_b": float((base["labor"][mask] * w).sum() / 1e9),
        "capital_income_b": float((base["capital"][mask] * w).sum() / 1e9),
        "state_net_revenue_b": float((base["state_net"][mask] * w).sum() / 1e9),
        "state_tax_before_refundable_credits_b": float(
            (base["state_tax"][mask] * w).sum() / 1e9
        ),
        "sdi_b": float((base["sdi"][mask] * w).sum() / 1e9),
        "groups": rows,
    }


def _california_rows(base, scen):
    """California's change in total and by baseline market-income group, $B."""
    mask = base["state"] == STATE
    assert np.array_equal(base["state"], scen["state"]), "household order changed"
    w = base["weight"][mask]
    ranks = _weighted_rank(base["market_income"][mask], w)

    def delta(key):
        return (scen[key] - base[key])[mask]

    fields = {
        "labor_income_change_b": delta("labor"),
        "capital_income_change_b": delta("capital"),
        "market_income_change_b": delta("market_income"),
        "state_tax_before_refundable_credits_change_b": delta("state_tax"),
        "state_refundable_credits_change_b": delta("state_credits"),
        "state_benefits_change_b": delta("state_benefits"),
        "state_net_change_b": delta("state_net"),
        "sdi_change_b": delta("sdi"),
    }

    def total(sel):
        out = {k: float((v[sel] * w[sel]).sum() / 1e9) for k, v in fields.items()}
        out["state_net_including_sdi_change_b"] = (
            out["state_net_change_b"] + out["sdi_change_b"]
        )
        return out

    everyone = np.ones_like(w, dtype=bool)
    groups = []
    for label, lo, hi in GROUPS:
        g = (ranks >= lo) & (ranks < hi)
        row = {"group": label}
        row.update(total(g))
        groups.append(row)
    return total(everyone), groups


def run(levels, microsim_factory=managed_us_microsimulation, verbose=True):
    # labor_capital_shift imports policyengine_us at module load; importing it
    # here keeps this module's accounting helpers testable without the model.
    from .labor_capital_shift import _apply_shift

    base_sim = microsim_factory()
    bundle = policyengine_bundle(base_sim)
    base_rev = revenue_components(base_sim)
    base_states = state_revenue_components(base_sim)
    base = _household_frame(base_sim)
    baseline = _baseline_concentration(base)
    del base_sim
    gc.collect()
    if verbose:
        print(
            f"Baseline CA net state revenue ${baseline['state_net_revenue_b']:.1f}B, "
            f"SDI ${baseline['sdi_b']:.1f}B",
            flush=True,
        )

    rows = []
    for pct in levels:
        sim = microsim_factory()
        branch, freed = _apply_shift(sim, f"ca_{int(round(pct * 100))}", pct)
        rev = revenue_components(branch)
        delta = net_fiscal_impact(rev, base_rev)
        states = state_revenue_delta(state_revenue_components(branch), base_states)
        scen = _household_frame(branch)
        ca_total, ca_groups = _california_rows(base, scen)

        state_net = {code: d["state_net_change"] / 1e9 for code, d in states.items()}
        all_states = sum(state_net.values())
        other_states = all_states - state_net.get(STATE, 0.0)
        gainers = sorted(
            (c for c, v in state_net.items() if v > 0.005), key=lambda c: -state_net[c]
        )
        losers = [c for c, v in state_net.items() if v < -0.005]
        row = {
            "shift_pct": int(round(pct * 100)),
            "labor_income_moved_b": freed / 1e9,
            "all_government_change_b": delta["total_change"] / 1e9,
            "all_states_net_change_b": all_states,
            "federal_net_change_b": delta["total_change"] / 1e9 - all_states,
            "other_states_net_change_b": other_states,
            "states_gaining": gainers,
            "states_losing_count": len(losers),
            "state_net_change_b": dict(sorted(state_net.items())),
            "national_components_b": {
                k: v / 1e9 for k, v in sorted(delta.items()) if isinstance(v, (int, float))
            },
            "california": ca_total,
            "california_by_group": ca_groups,
        }
        rows.append(row)
        if verbose:
            print(
                f"{row['shift_pct']:>3}% shift: CA net {ca_total['state_net_change_b']:+.2f}B "
                f"(with SDI {ca_total['state_net_including_sdi_change_b']:+.2f}B); "
                f"other states {other_states:+.2f}B; federal "
                f"{row['federal_net_change_b']:+.1f}B; all-gov "
                f"{row['all_government_change_b']:+.1f}B",
                flush=True,
            )
        del branch, sim, scen
        gc.collect()

    return {
        "year": YEAR,
        "state": STATE,
        "description": (
            "Positive employment and self-employment income fall by the shift "
            "share; the same weighted total is added to positive capital income "
            "in proportion to existing holdings. Static, current law, no "
            "behavioral response. State net revenue is state income tax plus use "
            "tax, less refundable state credits and state-funded benefits; "
            "California's employee SDI contribution is reported separately."
        ),
        "metadata": {
            "policyengine_version": bundle.get("policyengine_version")
            or _package_version("policyengine"),
            "policyengine_us_version": bundle.get("model_version")
            or _package_version("policyengine-us"),
            "policyengine_core_version": _package_version("policyengine-core"),
            "certified_data_build_id": bundle.get("certified_data_build_id"),
            "runtime_dataset_uri": bundle.get("runtime_dataset_uri"),
        },
        "baseline_california": baseline,
        "levels": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--levels",
        default=",".join(str(x) for x in DEFAULT_LEVELS),
        help="Comma-separated shift shares, e.g. 0.1,0.2,0.5,1.0",
    )
    parser.add_argument("--out", default=None, help="Output JSON path")
    args = parser.parse_args()
    levels = [float(x) for x in args.levels.split(",") if x.strip()]
    result = run(levels)
    out = args.out or os.path.join(
        OUTPUT_DIR,
        f"california_shift_pe{result['metadata']['policyengine_version']}.json",
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Saved {out}", flush=True)


if __name__ == "__main__":
    main()
