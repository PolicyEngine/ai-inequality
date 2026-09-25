"""Rank states by how exposed their own-source revenue is to the AI shock.

The scenario run already stores per-state deltas; what it does not store is the
2030 per-state baseline those deltas should be measured against. This script
runs one baseline simulation to get those levels, joins them to the deltas in
`ai_scenarios.json`, and writes a normalized exposure ranking.

SCOPE, and it decides how the ranking may be read
-------------------------------------------------
`household_state_tax_before_refundable_credits` adds exactly two things at
policyengine-us 1.764.6: `state_income_tax_before_refundable_credits` and
`state_use_tax`. So the channel measured here is **state income tax** (plus a
small use-tax component), net of refundable state credits and state-funded
benefits.

It is *not* state own-source revenue in the budgetary sense. General sales
tax, property tax, corporate income tax, severance taxes and fees are outside
the model. Nationally those are roughly half of state and local own-source
revenue, and they are exactly the bases that no-income-tax states rely on.

A state that scores near zero here is therefore making a statement about the
**income-tax channel**, not about budgetary resilience: Texas and Florida
collect through sales taxes this model does not carry, so their true exposure
to an AI boom is unmeasured rather than absent. The one informative
zero-income-tax case is Washington, whose capital-gains excise is modelled and
so does register.

Usage:
    python -m analysis.compute_state_exposure
"""

from __future__ import annotations

import json
import os
import warnings

from .ai_scenarios import TARGET_YEAR
from .fiscal import state_revenue_components
from .policyengine_runtime import managed_us_microsimulation, runtime_fingerprint

SCENARIOS_PATH = os.path.join(os.path.dirname(__file__), "outputs", "ai_scenarios.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "outputs", "state_exposure.json")
WEBSITE_OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "data", "stateExposureData.json"
)
BASELINE_CACHE = os.path.join(
    os.path.expanduser("~"),
    ".policyengine-runs",
    "ai-inequality-state-baseline-2030.json",
)

#: Cells to rank. The wage-spread variants bracket the range the Budget Lab
#: spans, so a state's exposure is reported as a band rather than a point.
VARIANTS = ["compressive", "proportional", "expansive"]

#: States whose modelled "income tax" reaches capital income only, so the
#: percentage is a share of a narrow instrument rather than of a broad tax.
#: Verified from the variable composition at policyengine-us 1.764.6:
#: `wa_income_tax_before_refundable_credits` adds exactly
#: `wa_capital_gains_tax` and `wa_millionaires_tax` — no wage income tax.
#: Low-rate broad-base states (AZ, LA, MS) are NOT in this category: their
#: percentages are comparable, they simply tax at lower rates.
CAPITAL_ONLY_INCOME_TAX_STATES = {"WA"}

SCOPE_NOTE = (
    "State income tax (plus use tax) net of refundable state credits and "
    "state-funded benefits. Sales, property, corporate and severance taxes are "
    "outside the model, so a low score means low exposure through the "
    "income-tax channel, not budgetary resilience."
)


def _verify_capital_only_states(sim):
    """Re-check, on the running engine, that each capital-only state's income
    tax adds only capital-income taxes; the constant was read at 1.764.6."""
    expected = {"WA": {"wa_capital_gains_tax", "wa_millionaires_tax"}}
    variables = sim.tax_benefit_system.variables
    for state in CAPITAL_ONLY_INCOME_TAX_STATES:
        name = f"{state.lower()}_income_tax_before_refundable_credits"
        adds = set(getattr(variables.get(name), "adds", None) or ())
        if adds != expected[state]:
            raise ValueError(
                f"{name} adds {sorted(adds)} on this engine, not the capital-only "
                f"{sorted(expected[state])}; revisit CAPITAL_ONLY_INCOME_TAX_STATES."
            )


def baseline_state_levels(year=TARGET_YEAR, verbose=True, cache_path=None):
    """Per-state baseline own-source levels, cached so this runs once.

    The cache records the runtime fingerprint and year, and is reused only by
    the same runtime; a cache from another engine or dataset is recomputed.
    """
    cache_path = BASELINE_CACHE if cache_path is None else cache_path
    fingerprint = runtime_fingerprint()["digest"]
    if cache_path and os.path.exists(cache_path):
        with open(cache_path) as handle:
            cached = json.load(handle)
        if (
            isinstance(cached, dict)
            and cached.get("fingerprint") == fingerprint
            and cached.get("year") == year
        ):
            if verbose:
                print("baseline state levels ... (cached)", flush=True)
            return cached["per_state"]
        warnings.warn(
            f"{cache_path} was written by another runtime or year; recomputing.",
            stacklevel=2,
        )

    if verbose:
        print("baseline state levels ... (running simulation)", flush=True)
    sim = managed_us_microsimulation()
    _verify_capital_only_states(sim)
    per_state = state_revenue_components(sim, year=year)

    if cache_path:
        _ensure_parent_dir(cache_path)
        with open(cache_path, "w") as handle:
            json.dump(
                {"fingerprint": fingerprint, "year": year, "per_state": per_state},
                handle,
                default=float,
            )
    return per_state


def _ensure_parent_dir(path):
    """Create the directory a file will be written to; a bare filename needs none."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _baseline_net(state_totals):
    """Baseline modelled state net own-source revenue, $B."""
    return (
        state_totals.get("household_state_tax_before_refundable_credits", 0.0)
        - state_totals.get("household_refundable_state_tax_credits", 0.0)
        - state_totals.get("household_state_benefits", 0.0)
    ) / 1e9


def build(
    year=TARGET_YEAR,
    verbose=True,
    scenarios_path=None,
    output_path=None,
    website_output_path=None,
    cache_path=None,
):
    with open(scenarios_path or SCENARIOS_PATH) as handle:
        scenarios = json.load(handle)

    # The deltas come from the scenarios file and the denominators from this
    # runtime's baseline; both must be the same runtime or the percentages mix
    # vintages.
    scenario_fingerprint = (
        scenarios.get("metadata", {}).get("runtime_fingerprint") or {}
    ).get("digest")
    current_fingerprint = runtime_fingerprint()["digest"]
    if scenario_fingerprint is None:
        warnings.warn(
            "The scenarios file carries no runtime fingerprint; its deltas may "
            "come from another runtime than this baseline.",
            stacklevel=2,
        )
    elif scenario_fingerprint != current_fingerprint:
        raise ValueError(
            f"The scenarios file was computed by runtime {scenario_fingerprint}, "
            f"this baseline by {current_fingerprint}; rerun one of them."
        )

    rows_by_label = {r["scenario"]["label"]: r for r in scenarios["scenarios"]}
    baseline = baseline_state_levels(year=year, verbose=verbose, cache_path=cache_path)

    states = {}
    for variant in VARIANTS:
        row = rows_by_label.get(f"Rapid / {variant}")
        if row is None:
            continue
        for code, delta in row["state_deltas"].items():
            if not isinstance(delta, dict):
                continue
            entry = states.setdefault(
                code,
                {
                    "state": code,
                    "baseline_net_revenue_b": _baseline_net(baseline.get(code, {})),
                    "_households": baseline.get(code, {}).get("household_weight", 0.0),
                    "deltas_b": {},
                    "exposure_pct": {},
                },
            )
            change = delta.get("state_net_change_b", 0.0)
            entry["deltas_b"][variant] = change
            base = entry["baseline_net_revenue_b"]
            entry["exposure_pct"][variant] = (
                None if base <= 0 else 100.0 * change / base
            )

    ranked = []
    for entry in states.values():
        pcts = [v for v in entry["exposure_pct"].values() if v is not None]
        entry["exposure_pct_proportional"] = entry["exposure_pct"].get("proportional")
        entry["exposure_pct_min"] = min(pcts) if pcts else None
        entry["exposure_pct_max"] = max(pcts) if pcts else None

        # Three buckets, because the percentage means different things in each.
        # A state with no modelled base is unmeasured, not unexposed. A state
        # whose modelled income tax reaches only capital income has a narrow
        # denominator, so its percentage is not comparable to a broad-base
        # state's — that is a fact about the instrument, not about the rate.
        households = entry.pop("_households", 0.0)
        base = entry["baseline_net_revenue_b"]
        entry["modelled_base_per_household"] = (
            (base * 1e9 / households) if households > 0 else 0.0
        )
        if base <= 0:
            kind = "none"
        elif entry["state"] in CAPITAL_ONLY_INCOME_TAX_STATES:
            kind = "capital_only"
        else:
            kind = "broad"
        entry["modelled_base_kind"] = kind
        entry["comparable_percentage"] = kind == "broad"
        ranked.append(entry)

    ranked.sort(
        key=lambda e: (
            e["exposure_pct_proportional"] is None,
            -(e["exposure_pct_proportional"] or 0.0),
        )
    )

    payload = {
        "year": year,
        "scope_note": SCOPE_NOTE,
        "metadata": {
            k: scenarios["metadata"].get(k)
            for k in (
                "policyengine_version",
                "country_model_version",
                "certified_data_build_id",
            )
        },
        "states": ranked,
    }

    _ensure_parent_dir(output_path or OUTPUT_PATH)
    with open(output_path or OUTPUT_PATH, "w") as handle:
        json.dump(payload, handle, indent=2, default=float)

    # Trimmed payload for the site: drop nothing, it is already small.
    if website_output_path != "none":
        _ensure_parent_dir(website_output_path or WEBSITE_OUTPUT_PATH)
        with open(website_output_path or WEBSITE_OUTPUT_PATH, "w") as handle:
            json.dump(payload, handle, indent=2, default=float)

    if verbose:
        _report(payload)
    return payload


def _report(payload):
    print(f"\nSTATE EXPOSURE TO THE AI CAPITAL SHOCK (Rapid, {payload['year']})")
    print(f"scope: {payload['scope_note']}\n")
    header = (
        f"{'state':6s} {'baseline $B':>12s} {'Δ prop $B':>10s} "
        f"{'% of base':>10s} {'range across λ':>18s}"
    )
    print(header)
    print("-" * len(header))
    shown = 0
    for e in payload["states"]:
        if not e["comparable_percentage"]:
            continue
        shown += 1
        if shown > 15:
            break
        print(
            f"{e['state']:6s} {e['baseline_net_revenue_b']:>12.1f} "
            f"{e['deltas_b'].get('proportional', 0.0):>10.2f} "
            f"{e['exposure_pct_proportional']:>9.2f}% "
            f"{e['exposure_pct_min']:>8.2f}% – {e['exposure_pct_max']:.2f}%"
        )

    narrow = [e for e in payload["states"] if e["modelled_base_kind"] == "capital_only"]
    if narrow:
        print("\nCapital-only modelled income tax — percentage NOT comparable:")
        for e in narrow:
            print(
                f"  {e['state']}: {e['deltas_b'].get('proportional', 0.0):+.2f}B, "
                f"which is {e['exposure_pct_proportional']:.1f}% of a "
                f"${e['baseline_net_revenue_b']:.1f}B modelled base — but that "
                f"base is the capital-gains and millionaires taxes alone, not "
                f"the state's budget. The dollar delta is the meaningful figure."
            )

    zero = [e["state"] for e in payload["states"] if e["modelled_base_kind"] == "none"]
    print(
        f"\nNo modelled base at all ({len(zero)}): {', '.join(sorted(zero))}"
        "\n  -> unmeasured through this channel, NOT low exposure: these states"
        "\n     fund themselves through sales and other taxes outside the model."
    )


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenarios", default=SCENARIOS_PATH)
    parser.add_argument("--output", default=OUTPUT_PATH)
    parser.add_argument(
        "--website-output",
        default=WEBSITE_OUTPUT_PATH,
        help="Site payload path; 'none' skips it.",
    )
    parser.add_argument(
        "--cache",
        default=BASELINE_CACHE,
        help="Baseline cache; 'none' disables it.",
    )
    args = parser.parse_args(argv)
    build(
        scenarios_path=args.scenarios,
        output_path=args.output,
        website_output_path=args.website_output,
        cache_path="" if args.cache == "none" else args.cache,
    )


if __name__ == "__main__":
    main()
