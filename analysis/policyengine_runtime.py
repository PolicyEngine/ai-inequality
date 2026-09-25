"""Managed PolicyEngine runtime helpers for reproducible analysis runs."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json

#: Stored input columns that policyengine-us has since renamed, mapped to the
#: live input. policyengine-us 1.777.0 replaced ``would_claim_wic`` with
#: ``takes_up_wic_if_eligible`` (Person, MONTH, default True), and ``wic`` is
#: ``defined_for`` the new flag. The certified US default
#: populace-us-2024-spm-20260915 is build p plus one column, so it still stores
#: the old name; the 2.x engine ignores it and every WIC-eligible person takes
#: WIC up. Mapping the stored draw restores the seeded take-up. The rename is
#: skipped on an engine that still knows the old name, and on data that already
#: carries the new one, so it retires itself once the data is re-cut.
LEGACY_INPUT_RENAMES = {"would_claim_wic": "takes_up_wic_if_eligible"}

#: Programs kept out of household net income. policyengine-us 1.764.x lists
#: ``head_start`` and ``early_head_start`` in ``gov.household.household_benefits``
#: and values each enrollee at per-enrollee program cost; Early Head Start
#: take-up is not seeded, so it defaults to every eligible child. That put
#: $129B of Head Start and Early Head Start into the 2030 baseline's net income
#: and let it respond to the wage shocks. policyengine-us 2.x lists only
#: ``household_head_start_benefits``, which is zero unless
#: ``gov.simulation.include_head_start_benefits_in_net_income`` is set (default
#: false). Dropping these names from the list counts Head Start the 2.x way on
#: either engine, and is a no-op on 2.x. Neither engine counts Head Start in SPM
#: resources, so poverty rates do not change.
NET_INCOME_EXCLUDED_BENEFITS = ("head_start", "early_head_start")

#: Bump when anything that changes computed values without changing a package
#: version is added here (for example a new legacy rename), so resume stores
#: written before the change are not reused after it. Revision 2 excludes
#: ``NET_INCOME_EXCLUDED_BENEFITS`` from household benefits.
RUNTIME_REVISION = 2


def drop_excluded_benefits(parameters, removed: set[str]):
    """Drop ``NET_INCOME_EXCLUDED_BENEFITS`` from every dated benefits list.

    Filters each dated value of ``gov.household.household_benefits`` in place,
    keeping the order of the other names, and adds each name it removed to
    ``removed``. A tree without that parameter is returned unchanged.
    """

    household = getattr(getattr(parameters, "gov", None), "household", None)
    node = getattr(household, "household_benefits", None)
    for at_instant in getattr(node, "values_list", ()):
        kept = [
            name for name in at_instant.value if name not in NET_INCOME_EXCLUDED_BENEFITS
        ]
        removed.update(set(at_instant.value) - set(kept))
        at_instant.value = kept
    return parameters


def net_income_exclusion_reform(removed: set[str] | None = None):
    """Return a reform class that applies ``drop_excluded_benefits``.

    Each name the loaded engine actually listed and the reform removed is added
    to ``removed``, so a caller can record what was excluded.
    """

    from policyengine_core.reforms import Reform

    removed = set() if removed is None else removed

    class ExcludeFromHouseholdBenefits(Reform):
        def apply(self):
            self.modify_parameters(
                lambda parameters: drop_excluded_benefits(parameters, removed)
            )

    return ExcludeFromHouseholdBenefits


def apply_legacy_input_renames(sim) -> dict[str, str]:
    """Set each renamed live input from the stored legacy column, every period.

    Reads the per-year person tables the dataset loaded (they keep columns the
    engine ignored), checks they line up with the simulation's persons, and
    sets the live input for every month (or year) of every dataset year.
    Returns the renames applied.
    """

    variables = sim.tax_benefit_system.variables
    datasets = getattr(getattr(sim, "dataset", None), "datasets", None)
    if not isinstance(datasets, dict):
        return {}
    applied: dict[str, str] = {}
    for legacy, live in LEGACY_INPUT_RENAMES.items():
        if legacy in variables or live not in variables:
            continue
        periods_by_year = {}
        for year, single_year in sorted(datasets.items()):
            person = getattr(single_year, "person", None)
            columns = getattr(person, "columns", ())
            if legacy not in columns or live in columns:
                continue
            periods_by_year[year] = person
        if not periods_by_year:
            continue
        definition_period = str(variables[live].definition_period)
        for year, person in periods_by_year.items():
            stored_ids = person["person_id"].to_numpy()
            simulated_ids = sim.calculate("person_id", period=year).values
            if (
                len(stored_ids) != len(simulated_ids)
                or (stored_ids != simulated_ids).any()
            ):
                raise ValueError(
                    f"Cannot map {legacy!r} onto {live!r} for {year}: the "
                    "stored person table is not in the simulation's person order."
                )
            values = person[legacy].to_numpy().astype(bool)
            if definition_period == "month":
                for month in range(1, 13):
                    sim.set_input(live, f"{year}-{month:02d}", values)
            else:
                sim.set_input(live, str(year), values)
        applied[legacy] = live
    return applied


def runtime_fingerprint() -> dict:
    """Identify the runtime whose results a resume store may reuse.

    Each policyengine.py release certifies one default dataset, so the package
    versions plus ``RUNTIME_REVISION`` pin what a managed run computes. The
    digest is what resume stores compare.
    """

    packages = {}
    # spm-calculator owns the SPM threshold formulas under policyengine-us
    # 2.x, and policyengine-us accepts more than one version of it.
    for package in (
        "policyengine",
        "policyengine-us",
        "policyengine-core",
        "spm-calculator",
    ):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    fingerprint = {
        "packages": packages,
        "legacy_input_renames": dict(sorted(LEGACY_INPUT_RENAMES.items())),
        "net_income_excluded_benefits": sorted(NET_INCOME_EXCLUDED_BENEFITS),
        "runtime_revision": RUNTIME_REVISION,
    }
    fingerprint["digest"] = hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True).encode()
    ).hexdigest()[:16]
    return fingerprint


def managed_us_microsimulation(
    *,
    dataset: str | None = None,
    allow_unmanaged: bool = False,
    **kwargs,
):
    """Construct a US Microsimulation pinned to the current PolicyEngine bundle.

    Stored inputs the engine has renamed are mapped onto their live names (see
    ``LEGACY_INPUT_RENAMES``), and household benefits leave out
    ``NET_INCOME_EXCLUDED_BENEFITS``. The bundle metadata that every output
    carries records the renames applied and the benefit names removed.
    """

    from policyengine.tax_benefit_models.us import managed_microsimulation

    if "reform" in kwargs:
        raise ValueError(
            "managed_us_microsimulation applies its own net-income reform; "
            "compose any other reform with net_income_exclusion_reform()."
        )
    removed: set[str] = set()
    sim = managed_microsimulation(
        dataset=dataset,
        allow_unmanaged=allow_unmanaged,
        reform=net_income_exclusion_reform(removed),
        **kwargs,
    )
    applied = apply_legacy_input_renames(sim)
    bundle = getattr(sim, "policyengine_bundle", None)
    if isinstance(bundle, dict):
        bundle["legacy_input_renames"] = applied
        bundle["net_income_excluded_benefits"] = sorted(removed)
    return sim


def managed_uk_microsimulation(
    *,
    dataset: str | None = None,
    allow_unmanaged: bool = False,
    **kwargs,
):
    """Construct a UK Microsimulation pinned to the current PolicyEngine bundle.

    Falls back to loading `policyengine_uk.Microsimulation` directly when
    the managed runtime cannot be imported (e.g. the bundled
    policyengine-us version and HuggingFace data release manifest are out
    of sync locally). The direct path still uses the HF-hosted enhanced
    FRS dataset and HUGGING_FACE_TOKEN for authentication.
    """
    try:
        from policyengine.tax_benefit_models.uk import managed_microsimulation

        return managed_microsimulation(
            dataset=dataset,
            allow_unmanaged=allow_unmanaged,
            **kwargs,
        )
    except Exception:
        from policyengine_uk import Microsimulation

        return Microsimulation(
            dataset=dataset
            or "hf://policyengine/policyengine-uk-data/enhanced_frs_2023_24.h5"
        )


def policyengine_bundle(sim) -> dict:
    """Return a detached copy of policyengine.py release metadata when present."""

    bundle = getattr(sim, "policyengine_bundle", None)
    if not isinstance(bundle, dict):
        return {}
    return dict(bundle)
