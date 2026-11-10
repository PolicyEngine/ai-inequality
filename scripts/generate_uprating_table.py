#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Regenerate public/data/uprating_analysis.csv from a pinned PolicyEngine-US release.

The uprating explorer on /research lists the parameter files and variables that
PolicyEngine-US grows over time, with the series each one grows by. This script
reads both from the tax-benefit system the release builds, so the table shows
what the model applies rather than what a scan of its files suggests:

- A parameter file gets a row when the built system uprates at least one value
  it holds. policyengine-core uprates a leaf parameter whose metadata names a
  series once metadata has passed down the tree, so a file-level ``uprating``
  key reaches a breakdown's values only where the file asks for that.
- A variable gets a row when its ``uprating`` is set once the system is built.
  That includes the series policyengine-us assigns to inputs that name none,
  and the per-person versions it swaps in for national totals.

src/data/policyengineUsSnapshot.json pins the release (its version and the
commit that sets it). Run from the repository root:

    uv run scripts/generate_uprating_table.py          # rewrite the table
    uv run scripts/generate_uprating_table.py --check  # fail if it is stale

The script installs the pinned release from PyPI in a throwaway environment,
resolving every dependency as PyPI served it a minute after the release's last
upload, so a rerun at the same pin writes the same table. It then checks the
installed files against the pinned commit on GitHub, because each row links to
its file there. Set GITHUB_TOKEN to raise GitHub's rate limit.

It stops, naming the files involved, on anything it can't account for: a
parameter file that YAML can't parse or that the system didn't load, an uprated
value it can't place in a file, a row whose series its file doesn't declare, a
variable defined outside policyengine_us/variables, or an installed file that
differs from the pinned commit.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import hashlib
import importlib.metadata
import inspect
import io
import json
import os
import sys
import urllib.request
import warnings
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = REPO_ROOT / "src" / "data" / "policyengineUsSnapshot.json"
TABLE_PATH = REPO_ROOT / "public" / "data" / "uprating_analysis.csv"

COLUMNS = ("type", "uprating_category", "path", "file_path", "uprating", "description")
PACKAGE = "policyengine_us"
SOURCE_ROOTS = (f"{PACKAGE}/parameters", f"{PACKAGE}/variables")
YAML_SUFFIXES = (".yaml", ".yml")
# policyengine-core reads index.yaml as its directory's own metadata.
DIRECTORY_METADATA_STEM = "index"
# Several uprating series one file's values use, as in a schedule that rounds
# married-filing-separately amounts to half the interval of the others.
SPEC_SEPARATOR = "; "

PYTHON_VERSION = "3.13"
PINNED_ENVIRONMENT_FLAG = "UPRATING_TABLE_PINNED_ENVIRONMENT"

# Each category names the series that drives a value's growth. A row's category
# comes from the first series on its uprating chain that this list names, so a
# state supplement that follows the federal SSI amount, which follows the
# Social Security COLA, lands under the COLA.
NAMED_SERIES = {
    "gov.irs.uprating": "IRS chained CPI-U",
    "gov.bls.cpi.c_cpi_u": "Chained CPI-U",
    "gov.bls.cpi.cpi_u": "CPI-U",
    "gov.bls.cpi.cpi_w": "CPI-W",
    "gov.bls.cpi.cpi_u_medical_care": "CPI-U medical care",
    "gov.states.ca.cpi": "California CPI",
    "gov.ssa.uprating": "Social Security (CPI-W)",
    "gov.ssa.nawi": "National average wage index",
    "gov.usda.snap.uprating": "SNAP (CPI-U)",
    "gov.hhs.uprating": "Head Start spending (CPI-U)",
    "gov.hhs.fpg_uprating": "Federal poverty guidelines (CPI-U)",
    "gov.aca.benchmark_premium_uprating": "ACA benchmark premium",
    "calibration.gov.census.populations.total": "Population",
    "calibration.gov.cbo.social_security": "CBO Social Security benefits",
    "calibration.gov.cbo.unemployment_compensation": "CBO unemployment compensation",
}
CBO_INCOME_PREFIX = "calibration.gov.cbo.income_by_source."
CBO_INCOME_SOURCES = {
    "adjusted_gross_income": "adjusted gross income",
    "employment_income": "employment income",
    "net_capital_gain": "net capital gains",
    "qualified_dividend_income": "qualified dividends",
    "self_employment_income": "self-employment income",
    "taxable_interest_and_ordinary_dividends": "taxable interest and ordinary dividends",
    "taxable_pension_income": "taxable pensions",
    "taxable_social_security": "taxable Social Security",
}
CMS_PREFIX = "calibration.gov.hhs.cms."
# policyengine-us derives some series from others, such as a national total
# divided by population, and records the source series under this key.
DERIVED_FROM = "derived_from"

# policyengine-us also grows parameters in code. While the system builds, before
# policyengine-core's metadata uprating, it calls EXTENSIONS_ENTRY in
# EXTENSIONS_MODULE, and each function that entry calls is a step. Updates the
# entry makes itself, outside any step, count as a step under the entry's name.
EXTENSIONS_MODULE = "parameters/uprating_extensions.py"
EXTENSIONS_ENTRY = "set_all_uprating_parameters"
# Steps that carry an index series past its last projection on the series' own
# trend. Those series drive other values' growth; they aren't rows themselves.
INDEX_STEPS = frozenset({"extend_parameter_values", EXTENSIONS_ENTRY})
# Steps that compute statutory amounts each year by formula, with the index each
# formula applies. The run checks that every step still reads its index and
# that the release runs no step this list and INDEX_STEPS leave out.
FORMULA_STEPS = {
    "extend_dependent_standard_deduction_parameters": "gov.bls.cpi.c_cpi_u",
    "extend_educator_expense_cap": "gov.bls.cpi.c_cpi_u",
    "extend_hsa_contribution_limits": "gov.bls.cpi.c_cpi_u",
    "extend_la_cpi_u_indexed_amounts": "gov.bls.cpi.cpi_u",
    "extend_medicaid_home_equity_limits": "gov.bls.cpi.cpi_u",
    "extend_medicaid_spousal_impoverishment_standards": "gov.bls.cpi.cpi_u",
    "extend_nyc_income_tax_elimination_credit_thresholds": "gov.bls.cpi.cpi_u",
    "extend_or_ctc_parameters": "gov.bls.cpi.cpi_u",
    "extend_social_security_payroll_cap": "gov.ssa.nawi",
    "extend_social_security_wage_indexed_parameters": "gov.ssa.nawi",
    "extend_wa_millionaires_standard_deduction": "gov.bls.cpi.cpi_w",
}
# How the table shows a value a formula step grows. The viewer parses this to
# link the step's module, so change the two together.
FORMULA_SEPARATOR = " via "


class TableError(RuntimeError):
    """Something the table can't account for; the message names the files."""


def fail(summary: str, items) -> None:
    items = sorted(str(item) for item in items)
    if items:
        listing = "\n".join(f"  {item}" for item in items[:200])
        more = f"\n  ... and {len(items) - 200} more" if len(items) > 200 else ""
        raise TableError(f"{summary} ({len(items)}):\n{listing}{more}")


# ---------------------------------------------------------------------------
# Pure helpers (tested in analysis/tests/test_uprating_table.py without
# policyengine-us installed).
# ---------------------------------------------------------------------------


def uprating_index(spec) -> str | None:
    """The series an uprating spec names: the string itself, or its `parameter`."""
    if isinstance(spec, str):
        return spec
    if isinstance(spec, dict) and isinstance(spec.get("parameter"), str):
        return spec["parameter"]
    return None


def format_spec(spec) -> str:
    """A spec as the table shows it: a series name, or the YAML mapping as Python writes it."""
    return spec if isinstance(spec, str) else repr(spec)


def canonical_spec(spec) -> str:
    return json.dumps(spec, sort_keys=True, default=str)


def format_specs(specs) -> str:
    """Join one file's distinct specs, the most-used first."""
    counts = Counter(format_spec(spec) for spec in specs)
    ordered = sorted(counts, key=lambda text: (-counts[text], text))
    return SPEC_SEPARATOR.join(ordered)


def single_line(text) -> str:
    return " ".join(str(text or "").split())


def parameter_name(relative_path: str) -> str:
    """The parameter a file defines: its path under parameters/, dotted, without the suffix."""
    stem, _, _ = relative_path.rpartition(".")
    return stem.replace("/", ".")


def owning_file(name: str, file_roots: dict[str, str]) -> str | None:
    """The file whose parameter is the longest prefix of `name`.

    Names grow by ``.child`` for nodes and ``[index]`` for scale brackets, so a
    prefix ends where the name continues with either.
    """
    end = len(name)
    while end > 0:
        prefix = name[:end]
        if prefix in file_roots:
            return file_roots[prefix]
        end = max(name.rfind(".", 0, end), name.rfind("[", 0, end))
    return None


def declared_specs(data) -> list:
    """Every `uprating` value under a `metadata` mapping in a parameter file's YAML."""
    found = []

    def visit(node):
        if isinstance(node, dict):
            metadata = node.get("metadata")
            if isinstance(metadata, dict) and "uprating" in metadata:
                found.append(metadata["uprating"])
            for key, value in node.items():
                if key != "metadata":
                    visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(data)
    return found


def named_category(series: str) -> str | None:
    if series in NAMED_SERIES:
        return NAMED_SERIES[series]
    if series.startswith(CBO_INCOME_PREFIX):
        key = series[len(CBO_INCOME_PREFIX) :]
        return f"CBO {CBO_INCOME_SOURCES.get(key, key.replace('_', ' '))}"
    if series.startswith(CMS_PREFIX):
        return "CMS health spending"
    return None


def category_for(series: str, links) -> tuple[str, str]:
    """The category for a value that grows with `series`, and the series that names it.

    `links(name)` returns two series for `name`, either of which may be None:
    the one it was derived from (the national total a per-person series
    divides by population) and the one its own metadata uprates it by. A
    derived series takes its source's category. Otherwise the first series on
    the uprating chain that NAMED_SERIES or a family prefix names gives the
    category, and a chain that ends without one gets "Other: <root>".
    """
    seen = []
    current = series
    while True:
        if current in seen:
            raise TableError("Uprating chain loops: " + " -> ".join([*seen, current]))
        seen.append(current)
        derived_from, uprated_by = links(current)
        if derived_from:
            current = derived_from
            continue
        category = named_category(current)
        if category is not None:
            return category, current
        if not uprated_by or uprated_by == "self":
            return f"Other: {current}", current
        current = uprated_by


def sort_key(row: dict) -> tuple:
    return (
        0 if row["type"] == "parameter" else 1,
        row["uprating_category"],
        row["path"],
    )


def render_table(rows) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in sorted(rows, key=sort_key):
        writer.writerow({column: row[column] for column in COLUMNS})
    return buffer.getvalue()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def formula_spec(series: str, step: str) -> str:
    """How the table shows a value that a formula step grows from `series`."""
    return f"{series}{FORMULA_SEPARATOR}{step}"


def last_instant(values) -> str | None:
    """The latest instant in a leaf's (instant, value) pairs, or None if it has none."""
    return max((instant for instant, _ in values), default=None)


def effective_value(values, instant: str):
    """A leaf's value at `instant`, read as policyengine-core reads it.

    Core keeps a leaf's values latest first and returns the first one dated on
    or before the instant, so this walks the pairs in their stored order.
    """
    for start, value in values:
        if start <= instant:
            return value
    return None


def projection_differs(before, after, since: str) -> bool:
    """Whether two versions of a leaf disagree at any instant after `since`."""
    instants = {i for i, _ in before if i > since} | {i for i, _ in after if i > since}
    return any(
        effective_value(before, instant) != effective_value(after, instant)
        for instant in instants
    )


# ---------------------------------------------------------------------------
# The pinned environment.
# ---------------------------------------------------------------------------


def load_snapshot() -> dict:
    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    for key in ("repository", "version", "commit"):
        if not snapshot.get(key):
            raise TableError(f"{SNAPSHOT_PATH.relative_to(REPO_ROOT)} sets no {key}")
    return snapshot


def installed_version() -> str | None:
    try:
        return importlib.metadata.version("policyengine-us")
    except importlib.metadata.PackageNotFoundError:
        return None


def release_cutoff(version: str) -> str:
    """One minute after PyPI received the release's last file, in RFC 3339."""
    url = f"https://pypi.org/pypi/policyengine-us/{version}/json"
    with urllib.request.urlopen(url, timeout=60) as response:
        release = json.load(response)
    uploads = [
        dt.datetime.fromisoformat(item["upload_time_iso_8601"].replace("Z", "+00:00"))
        for item in release.get("urls", [])
    ]
    if not uploads:
        raise TableError(f"PyPI lists no files for policyengine-us {version}")
    cutoff = max(uploads).astimezone(dt.timezone.utc) + dt.timedelta(minutes=1)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def reexecute_in_pinned_environment(version: str, argv: list[str]) -> None:
    """Rerun this script with the pinned release installed, unless it already is."""
    if installed_version() == version:
        return
    if os.environ.get(PINNED_ENVIRONMENT_FLAG):
        raise TableError(
            f"Expected policyengine-us {version} in the pinned environment, "
            f"found {installed_version()}"
        )
    cutoff = release_cutoff(version)
    command = [
        "uv",
        "run",
        "--no-project",
        "--python",
        PYTHON_VERSION,
        "--exclude-newer",
        cutoff,
        "--with",
        f"policyengine-us=={version}",
        "python",
        "-I",
        str(Path(__file__).resolve()),
        *argv,
    ]
    print(
        f"Installing policyengine-us {version} with dependencies as of {cutoff}",
        file=sys.stderr,
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME")
    }
    environment[PINNED_ENVIRONMENT_FLAG] = cutoff
    sys.stdout.flush()
    sys.stderr.flush()
    os.execvpe("uv", command, environment)


# ---------------------------------------------------------------------------
# The installed release against the pinned commit.
# ---------------------------------------------------------------------------


def github_json(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-inequality-uprating-table",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com/{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def commit_blobs(repository: str, commit: str) -> dict[str, str]:
    """Blob SHA of every file under SOURCE_ROOTS at `commit`, by repository path."""
    tree = github_json(f"repos/{repository}/git/commits/{commit}")["tree"]["sha"]
    blobs = {}
    for root in SOURCE_ROOTS:
        sha = tree
        for part in root.split("/"):
            entries = github_json(f"repos/{repository}/git/trees/{sha}")["tree"]
            match = [e for e in entries if e["type"] == "tree" and e["path"] == part]
            if not match:
                raise TableError(f"{repository}@{commit} has no {root}")
            sha = match[0]["sha"]
        listing = github_json(f"repos/{repository}/git/trees/{sha}?recursive=1")
        if listing.get("truncated"):
            raise TableError(f"GitHub truncated the listing of {root} at {commit}")
        for entry in listing["tree"]:
            if entry["type"] == "blob":
                blobs[f"{root}/{entry['path']}"] = entry["sha"]
    return blobs


def installed_blobs(package_dir: Path) -> dict[str, str]:
    blobs = {}
    for root in SOURCE_ROOTS:
        directory = package_dir.parent / root
        for path in directory.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            blobs[path.relative_to(package_dir.parent).as_posix()] = git_blob_sha(
                path.read_bytes()
            )
    return blobs


def check_release_matches_commit(snapshot: dict, package_dir: Path) -> int:
    expected = commit_blobs(snapshot["repository"], snapshot["commit"])
    actual = installed_blobs(package_dir)
    fail(
        f"Files at {snapshot['commit']} that policyengine-us {snapshot['version']} doesn't install",
        expected.keys() - actual.keys(),
    )
    fail(
        f"Files policyengine-us {snapshot['version']} installs that {snapshot['commit']} lacks",
        actual.keys() - expected.keys(),
    )
    fail(
        f"Files that differ between policyengine-us {snapshot['version']} and {snapshot['commit']}",
        [path for path in expected if actual[path] != expected[path]],
    )
    return len(expected)


# ---------------------------------------------------------------------------
# Reading the built system.
# ---------------------------------------------------------------------------


def find_node(root, name: str):
    node = root
    for part in name.split("."):
        children = getattr(node, "children", None)
        if not children or part not in children:
            return None
        node = children[part]
    return node


def leaf_values(root, parameter_class) -> dict[str, tuple]:
    """Every leaf's (instant, value) pairs, in the order core stores them."""
    return {
        leaf.name: tuple((value.instant_str, value.value) for value in leaf.values_list)
        for leaf in root.get_descendants()
        if isinstance(leaf, parameter_class)
    }


class ExtensionRecorder:
    """What each step of the code extensions changes and reads.

    `wrap()` returns a stand-in for the entry function. While the entry runs,
    the stand-in credits every value a leaf sets, and every value it reads, to
    the function the entry called on the way there.
    """

    def __init__(self, entry, parameter_class):
        self.entry = entry
        self.parameter_class = parameter_class
        self.updated = defaultdict(set)  # leaf name -> steps that set its values
        self.reads = defaultdict(set)  # step -> leaves whose values it read
        self.loaded: dict[str, tuple] = {}
        self.extended: dict[str, tuple] = {}
        self.runs = 0

    def _step(self) -> str | None:
        # Frame 0 is this method and frame 1 the patched method that called it.
        frame, callee = sys._getframe(2), None
        while frame is not None:
            if frame.f_code is self.entry.__code__:
                return EXTENSIONS_ENTRY if callee is None else callee.f_code.co_name
            callee, frame = frame, frame.f_back
        return None

    def wrap(self):
        recorder, parameter_class = self, self.parameter_class
        original_update = parameter_class.update
        original_read = parameter_class._get_at_instant

        def update(parameter, *args, **kwargs):
            step = recorder._step()
            if step is not None:
                recorder.updated[parameter.name].add(step)
            return original_update(parameter, *args, **kwargs)

        def read(parameter, instant):
            step = recorder._step()
            if step is not None:
                recorder.reads[step].add(parameter.name)
            return original_read(parameter, instant)

        def entry(parameters):
            recorder.runs += 1
            recorder.loaded = leaf_values(parameters, parameter_class)
            parameter_class.update = update
            parameter_class._get_at_instant = read
            try:
                return recorder.entry(parameters)
            finally:
                parameter_class.update = original_update
                parameter_class._get_at_instant = original_read
                recorder.extended = leaf_values(parameters, parameter_class)

        return entry


def extension_growth(recorder, final: dict, report: dict) -> tuple[dict, set]:
    """Which leaves the formula and index steps grow, checked for completeness.

    Returns the leaves a formula step grows, each with its step, and the index
    series the index steps extend. Stops on a step neither list knows, a
    formula step that no longer reads its index, a leaf that several steps or a
    formula and its metadata both grow, and any leaf whose values outrun what
    its file holds by no mechanism the table knows.
    """
    changed = {
        name: steps
        for name, steps in recorder.updated.items()
        if recorder.extended.get(name) != recorder.loaded.get(name)
    }
    ran = {step for steps in recorder.updated.values() for step in steps}
    fail(
        f"Steps of {EXTENSIONS_ENTRY} that FORMULA_STEPS and INDEX_STEPS leave out",
        ran - INDEX_STEPS - FORMULA_STEPS.keys(),
    )
    fail(
        f"FORMULA_STEPS entries {EXTENSIONS_ENTRY} no longer runs",
        FORMULA_STEPS.keys() - ran,
    )
    fail(
        "Formula steps that no longer read the index FORMULA_STEPS gives them",
        [
            f"{step}: {series}"
            for step, series in FORMULA_STEPS.items()
            if series not in recorder.reads[step]
        ],
    )
    fail(
        "Leaves several extension steps change",
        [
            f"{name}: {sorted(steps)}"
            for name, steps in changed.items()
            if len(steps) > 1
        ],
    )
    fail(
        "Leaves the extension steps change that the built system lacks",
        changed.keys() - final.keys(),
    )

    formula = {
        name: next(iter(steps))
        for name, steps in changed.items()
        if next(iter(steps)) in FORMULA_STEPS
    }
    index = {
        name for name, steps in changed.items() if next(iter(steps)) in INDEX_STEPS
    }

    both, overridden = [], []
    for name in sorted(formula.keys() | index):
        leaf = final[name]
        since = last_instant(recorder.loaded[name]) or ""
        if projection_differs(recorder.extended[name], leaf_pairs(leaf), since):
            both.append(f"{name}: {formula.get(name, 'index')}")
        elif leaf.metadata.get("uprating") is not None:
            overridden.append(name)
    fail("Leaves a code step and metadata uprating both grow", both)
    report["metadata_overridden_by_code"] = overridden

    unaccounted = []
    for name, before in recorder.loaded.items():
        leaf = final.get(name)
        if leaf is None:
            unaccounted.append(f"{name}: missing from the built system")
            continue
        loaded_last, final_last = last_instant(before), last_instant(leaf_pairs(leaf))
        if loaded_last is None or final_last is None or final_last <= loaded_last:
            continue
        if name not in changed and leaf.metadata.get("uprating") is None:
            unaccounted.append(f"{name}: {loaded_last} -> {final_last}")
    fail(
        "Leaves whose values outrun their files by no mechanism the table knows",
        unaccounted,
    )
    report["formula_leaves"] = len(formula)
    report["index_series"] = len(index)
    return formula, index


def leaf_pairs(leaf) -> tuple:
    return tuple((value.instant_str, value.value) for value in leaf.values_list)


def read_parameter_files(
    parameters_dir: Path,
) -> tuple[dict[str, str], dict[str, list]]:
    """Each parameter file's parameter name and declared uprating specs.

    Reads every YAML file with policyengine-core's own loader, so a file it
    can't parse stops the run here as it would stop the model.
    """
    from policyengine_core.parameters import config as core_yaml

    file_roots, declared, unreadable = {}, {}, []
    for path in sorted(parameters_dir.rglob("*")):
        if path.suffix not in YAML_SUFFIXES or not path.is_file():
            continue
        relative = path.relative_to(parameters_dir).as_posix()
        try:
            with path.open(encoding="utf-8") as handle:
                data = core_yaml.yaml.load(handle, Loader=core_yaml.Loader)
        except Exception as error:  # noqa: BLE001 - report every unreadable file
            unreadable.append(
                f"{relative}: {type(error).__name__}: {single_line(error)[:200]}"
            )
            continue
        specs = declared_specs(data)
        if specs:
            declared[relative] = specs
        if path.stem != DIRECTORY_METADATA_STEM:
            file_roots[parameter_name(relative)] = relative
    fail("Parameter files YAML can't read", unreadable)
    return file_roots, declared


def parameter_rows(
    system,
    parameters_dir: Path,
    links,
    formula: dict[str, str],
    index: set[str],
    report: dict,
) -> list[dict]:
    """One row per parameter file holding a value that metadata or a formula grows.

    A leaf a formula step grows shows that step in place of any metadata it
    carries, which the step's values to the end of the projection override.
    Index series the index steps extend drive other values and get no row.
    """
    from policyengine_core.parameters import Parameter

    file_roots, declared = read_parameter_files(parameters_dir)
    fail(
        "Parameter files the built system holds no parameter for",
        [
            f
            for name, f in file_roots.items()
            if find_node(system.parameters, name) is None
        ],
    )

    # Each file's grown leaves as (name, spec, series, grown by a formula).
    grown_by_file, unplaced = defaultdict(list), []
    for leaf in system.parameters.get_descendants():
        if not isinstance(leaf, Parameter) or leaf.name in index:
            continue
        if leaf.name in formula:
            step = formula[leaf.name]
            series = FORMULA_STEPS[step]
            grown = (leaf.name, formula_spec(series, step), series, True)
        elif leaf.metadata.get("uprating") is not None:
            spec = leaf.metadata["uprating"]
            grown = (leaf.name, spec, uprating_index(spec), False)
        else:
            continue
        relative = owning_file(leaf.name, file_roots)
        if relative is None:
            unplaced.append(leaf.name)
        else:
            grown_by_file[relative].append(grown)
    fail("Uprated parameters that belong to no parameter file", unplaced)

    undeclared, rows = [], []
    for relative, grown in grown_by_file.items():
        grown.sort(key=lambda item: item[0])
        declared_here = {canonical_spec(spec) for spec in declared.get(relative, [])}
        missing = {
            format_spec(spec)
            for _, spec, _, by_formula in grown
            if not by_formula and canonical_spec(spec) not in declared_here
        }
        if missing:
            undeclared.append(f"{relative}: {sorted(missing)}")
            continue
        series = sorted({index for _, _, index, _ in grown}, key=str)
        if None in series:
            undeclared.append(f"{relative}: a spec names no series")
            continue
        categories = {category_for(index, links)[0] for index in series}
        if len(categories) != 1:
            undeclared.append(
                f"{relative}: values follow series in several categories: {series}"
            )
            continue
        root = find_node(system.parameters, parameter_name(relative))
        rows.append(
            {
                "type": "parameter",
                "uprating_category": categories.pop(),
                "path": parameter_name(relative),
                "file_path": relative,
                "uprating": format_specs(spec for _, spec, _, _ in grown),
                "description": single_line(getattr(root, "description", "")),
            }
        )
        report["uprated_leaves"] += sum(not by_formula for *_, by_formula in grown)
        report["formula_files"] += any(by_formula for *_, by_formula in grown)
    fail(
        "Parameter files whose uprated values don't match what the file declares",
        undeclared,
    )

    report["declared_without_effect"] = sorted(set(declared) - set(grown_by_file))
    return rows


def declared_variable_uprating(cls) -> str | None:
    """The uprating a variable's class (or a policyengine-us base) sets, if any."""
    from policyengine_core.variables import Variable as CoreVariable

    for klass in cls.__mro__:
        if klass is CoreVariable or klass is object:
            break
        if "uprating" in vars(klass) and isinstance(vars(klass)["uprating"], str):
            return vars(klass)["uprating"]
    return None


def variable_rows(system, variables_dir: Path, links, report: dict) -> list[dict]:
    rows, outside, unnamed = [], [], []
    for name in sorted(system.variables):
        variable = system.variables[name]
        if not variable.uprating:
            continue
        source = Path(inspect.getsourcefile(type(variable)) or "").resolve()
        if variables_dir not in source.parents:
            outside.append(f"{name}: {source}")
            continue
        declared = declared_variable_uprating(type(variable))
        if declared is None:
            report["variables_defaulted"] += 1
        elif declared != variable.uprating:
            report["variables_redirected"] += 1
        if declared is not None and declared not in source.read_text(encoding="utf-8"):
            unnamed.append(
                f"{name}: {source.relative_to(variables_dir)} doesn't name {declared}"
            )
        category, _ = category_for(variable.uprating, links)
        rows.append(
            {
                "type": "variable",
                "uprating_category": category,
                "path": name,
                "file_path": source.relative_to(variables_dir).as_posix(),
                "uprating": variable.uprating,
                "description": single_line(variable.label),
            }
        )
    fail("Uprated variables defined outside policyengine_us/variables", outside)
    fail(
        "Uprated variables whose file doesn't name the series their class sets", unnamed
    )
    return rows


def build_table(snapshot: dict) -> tuple[str, dict]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # Importing the package builds a system of its own, before the recorder
        # can wrap the extensions, so the table reads a second build.
        import policyengine_us
        import policyengine_us.system as country_system
        from policyengine_core.parameters import Parameter
        from policyengine_us.parameters import uprating_extensions

        package_dir = Path(policyengine_us.__file__).resolve().parent
        report = {
            "checked_files": check_release_matches_commit(snapshot, package_dir),
            "uprated_leaves": 0,
            "formula_files": 0,
            "variables_defaulted": 0,
            "variables_redirected": 0,
        }
        entry = getattr(uprating_extensions, EXTENSIONS_ENTRY)
        if (
            Path(inspect.getsourcefile(entry)).resolve()
            != package_dir / EXTENSIONS_MODULE
        ):
            raise TableError(
                f"{EXTENSIONS_ENTRY} no longer lives in {EXTENSIONS_MODULE}"
            )
        if country_system.set_irs_uprating_parameter is not entry:
            raise TableError(
                f"policyengine_us.system no longer extends parameters with {EXTENSIONS_ENTRY}"
            )
        recorder = ExtensionRecorder(entry, Parameter)
        country_system.set_irs_uprating_parameter = recorder.wrap()
        try:
            system = country_system.CountryTaxBenefitSystem()
        finally:
            country_system.set_irs_uprating_parameter = entry
    if recorder.runs != 1:
        raise TableError(
            f"The build ran {EXTENSIONS_ENTRY} {recorder.runs} times, not once"
        )
    report["misplaced_uprating_keys"] = sorted(
        {
            single_line(w.message)
            for w in caught
            if type(w.message).__name__ == "ParameterKeyWarning"
            and "'uprating'" in str(w.message)
        }
    )

    def links(name: str) -> tuple[str | None, str | None]:
        node = find_node(system.parameters, name)
        if node is None:
            raise TableError(f"Uprating names {name}, which the built system lacks")
        metadata = getattr(node, "metadata", {}) or {}
        return metadata.get(DERIVED_FROM), uprating_index(metadata.get("uprating"))

    final = {
        leaf.name: leaf
        for leaf in system.parameters.get_descendants()
        if isinstance(leaf, Parameter)
    }
    formula, index = extension_growth(recorder, final, report)
    rows = parameter_rows(
        system, package_dir / "parameters", links, formula, index, report
    )
    rows += variable_rows(system, package_dir / "variables", links, report)
    report["rows"] = rows
    report["core_version"] = importlib.metadata.version("policyengine-core")
    return render_table(rows), report


def print_report(snapshot: dict, report: dict) -> None:
    rows = report["rows"]
    by_type = Counter(row["type"] for row in rows)
    print(
        f"policyengine-us {snapshot['version']} ({snapshot['commit'][:7]}), "
        f"policyengine-core {report['core_version']}: "
        f"{report['checked_files']} files match the commit"
    )
    print(
        f"{by_type['parameter']} parameter files ({report['uprated_leaves']} values grow "
        f"by metadata; {report['formula_files']} files hold {report['formula_leaves']} "
        f"values formulas grow) and {by_type['variable']} variables"
    )
    print(
        f"  {report['index_series']} index series grow on their own trend and get no row"
    )
    if report["metadata_overridden_by_code"]:
        print("Values whose metadata uprating a code step overrides:")
        for name in report["metadata_overridden_by_code"]:
            print(f"  {name}")
    print(
        f"  variables: {report['variables_defaulted']} take policyengine-us's default, "
        f"{report['variables_redirected']} grow by another series than the one their "
        "class names"
    )
    for (kind, category), count in sorted(
        Counter((row["type"], row["uprating_category"]) for row in rows).items(),
        key=lambda item: (item[0][0], -item[1], item[0][1]),
    ):
        print(f"  {kind:9} {count:4d}  {category}")
    others = sorted(
        {
            row["uprating_category"]
            for row in rows
            if row["uprating_category"].startswith("Other: ")
        }
    )
    if others:
        print("Series with no category name (add them to NAMED_SERIES):")
        for category in others:
            print(f"  {category}")
    if report["declared_without_effect"]:
        print("Files that declare uprating the built system never applies:")
        for relative in report["declared_without_effect"]:
            print(f"  {relative}")
    if report["misplaced_uprating_keys"]:
        print("policyengine-core ignored these uprating keys:")
        for message in report["misplaced_uprating_keys"]:
            print(f"  {message}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the committed table differs from what the pinned release gives",
    )
    args = parser.parse_args(argv)
    snapshot = load_snapshot()
    reexecute_in_pinned_environment(snapshot["version"], argv)

    table, report = build_table(snapshot)
    print_report(snapshot, report)
    relative = TABLE_PATH.relative_to(REPO_ROOT)
    current = TABLE_PATH.read_text(encoding="utf-8") if TABLE_PATH.exists() else ""
    if args.check:
        if current != table:
            diff = list(
                difflib.unified_diff(
                    current.splitlines(),
                    table.splitlines(),
                    str(relative),
                    "generated",
                    lineterm="",
                )
            )
            print("\n".join(diff[:80]))
            print(f"{relative} is stale; run uv run scripts/generate_uprating_table.py")
            return 1
        print(f"{relative} matches policyengine-us {snapshot['version']}")
        return 0
    TABLE_PATH.write_text(table, encoding="utf-8")
    print(f"Wrote {relative}: {len(report['rows'])} rows")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except TableError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
