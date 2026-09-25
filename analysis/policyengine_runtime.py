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

#: Bump when anything that changes computed values without changing a package
#: version is added here (for example a new legacy rename), so resume stores
#: written before the change are not reused after it.
RUNTIME_REVISION = 1


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
    ``LEGACY_INPUT_RENAMES``); the renames applied are recorded in the bundle
    metadata that every output carries.
    """

    from policyengine.tax_benefit_models.us import managed_microsimulation

    sim = managed_microsimulation(
        dataset=dataset,
        allow_unmanaged=allow_unmanaged,
        **kwargs,
    )
    applied = apply_legacy_input_renames(sim)
    bundle = getattr(sim, "policyengine_bundle", None)
    if isinstance(bundle, dict):
        bundle["legacy_input_renames"] = applied
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
