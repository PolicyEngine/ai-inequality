"""Tests for scripts/generate_uprating_table.py and the table it writes.

The generator needs policyengine-us to build a table, but its helpers don't,
so these tests run in CI without it. They check, over generated inputs:

- a leaf belongs to the file whose parameter is the longest prefix of its
  name that ends where the name continues with ``.`` or ``[``, and to no file
  when no prefix ends there;
- a file's specs join as each distinct spec once, the most-used first;
- the table round-trips through CSV in its canonical order;
- following an uprating chain ends on every finite graph, by naming a
  category or raising on a loop, and a named category names the series it
  stopped on;
- a leaf read as policyengine-core reads it agrees with itself, and two
  readings differ only where some instant's value differs.

They also check the committed table: canonical order, one row per file or
variable, a named category on every row, and formula rows that match the
generator's formula steps.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import importlib.util
import io
import re
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_uprating_table.py"

_spec = importlib.util.spec_from_file_location("generate_uprating_table", SCRIPT)
table = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(table)

SEGMENTS = st.sampled_from(["gov", "irs", "a", "ab", "b", "x1", "amount"])
NAMES = st.lists(SEGMENTS, min_size=1, max_size=5).map(".".join)


def _with_brackets(draw, name):
    """Append scale-bracket parts, as in ``a.b[0].amount``."""
    for _ in range(draw(st.integers(0, 2))):
        name += f"[{draw(st.integers(0, 3))}]"
        if draw(st.booleans()):
            name += "." + draw(SEGMENTS)
    return name


@st.composite
def leaf_names(draw):
    return _with_brackets(draw, draw(NAMES))


def _reference_owner(name, file_roots):
    """The longest root that is the whole name or ends before a '.' or '['."""
    matches = [
        root
        for root in file_roots
        if name == root or name.startswith((root + ".", root + "["))
    ]
    return file_roots[max(matches, key=len)] if matches else None


# ---------------------------------------------------------------------------
# owning_file
# ---------------------------------------------------------------------------


def test_owning_file_takes_the_longest_prefix_at_a_boundary():
    roots = {"gov.irs": "gov/irs.yaml", "gov.irs.cap": "gov/irs/cap.yaml"}
    assert table.owning_file("gov.irs.cap", roots) == "gov/irs/cap.yaml"
    assert table.owning_file("gov.irs.cap[2].amount", roots) == "gov/irs/cap.yaml"
    assert table.owning_file("gov.irs.rate", roots) == "gov/irs.yaml"
    # "gov.irs.capital" continues "gov.irs.cap" mid-segment, so only gov.irs owns it.
    assert table.owning_file("gov.irs.capital", roots) == "gov/irs.yaml"
    assert table.owning_file("gov.ssa", roots) is None


@settings(deadline=None)
@given(
    name=leaf_names(),
    roots=st.lists(NAMES, max_size=6, unique=True),
)
def test_owning_file_matches_the_boundary_prefix_rule(name, roots):
    file_roots = {root: root.replace(".", "/") + ".yaml" for root in roots}
    # Add some true prefixes of the name, so matches are common.
    parts = re.split(r"(?=[.\[])", name)
    for cut in range(1, len(parts) + 1, 2):
        prefix = "".join(parts[:cut])
        file_roots.setdefault(prefix, prefix.replace(".", "/") + ".yaml")
    assert table.owning_file(name, file_roots) == _reference_owner(name, file_roots)


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------


def test_uprating_index_reads_a_series_name_or_its_parameter_key():
    assert table.uprating_index("gov.irs.uprating") == "gov.irs.uprating"
    assert table.uprating_index({"parameter": "gov.irs.uprating", "rounding": 50}) == (
        "gov.irs.uprating"
    )
    assert table.uprating_index({"rounding": 50}) is None
    assert table.uprating_index(None) is None


def test_format_spec_writes_a_mapping_as_python_does():
    spec = {"parameter": "gov.irs.uprating", "rounding": {"interval": 50}}
    assert table.format_spec(spec) == repr(spec)
    assert table.format_spec("gov.ssa.uprating") == "gov.ssa.uprating"


def test_format_specs_puts_the_most_used_spec_first():
    specs = ["b", "a", "b", {"parameter": "c"}, "a", "b"]
    assert table.format_specs(specs) == "b; a; {'parameter': 'c'}"


SPECS = st.lists(
    st.one_of(
        st.text(alphabet="abc.", min_size=1, max_size=4),
        st.fixed_dictionaries({"parameter": st.sampled_from(["p", "q"])}),
    ),
    min_size=1,
    max_size=12,
)


@given(SPECS)
def test_format_specs_lists_each_distinct_spec_once_by_use(specs):
    parts = table.format_specs(specs).split(table.SPEC_SEPARATOR)
    formatted = [table.format_spec(spec) for spec in specs]
    assert sorted(parts) == sorted(set(formatted))
    counts = [formatted.count(part) for part in parts]
    assert counts == sorted(counts, reverse=True)


def test_declared_specs_finds_metadata_at_every_depth():
    data = {
        "metadata": {"uprating": "top"},
        "SINGLE": {"metadata": {"uprating": {"parameter": "single"}}, "values": {}},
        "brackets": [
            {"amount": {"metadata": {"uprating": "bracket"}}},
            {"threshold": {"values": {"2020-01-01": 1}}},
        ],
        "description": "metadata: uprating in prose is not a key",
    }
    assert table.declared_specs(data) == ["top", {"parameter": "single"}, "bracket"]
    assert table.declared_specs({"values": {"2020-01-01": 1}}) == []


def test_parameter_name_and_single_line():
    assert table.parameter_name("gov/irs/payroll/cap.yaml") == "gov.irs.payroll.cap"
    assert table.single_line("  Two\n lines\tof  text ") == "Two lines of text"
    assert table.single_line(None) == ""


@given(st.text())
def test_single_line_leaves_single_spaces_only(text):
    line = table.single_line(text)
    assert line == line.strip()
    assert "  " not in line
    assert not re.search(r"[^\S ]", line)
    assert table.single_line(line) == line


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


def test_named_category_covers_the_series_families():
    assert table.named_category("gov.irs.uprating") == "IRS chained CPI-U"
    prefix = table.CBO_INCOME_PREFIX
    assert table.named_category(prefix + "employment_income") == (
        "CBO employment income"
    )
    assert table.named_category(prefix + "new_source") == "CBO new source"
    assert table.named_category(table.CMS_PREFIX + "moop_per_capita") == (
        "CMS health spending"
    )
    assert table.named_category("gov.states.zz.index") is None


def _links(graph):
    def links(name):
        return graph.get(name, (None, None))

    return links


def test_category_for_follows_a_derived_series_to_its_source():
    graph = {
        "calibration.gov.irs.soi.wages_per_capita": (
            "calibration.gov.irs.soi.wages",
            None,
        ),
        "calibration.gov.irs.soi.wages": (
            None,
            table.CBO_INCOME_PREFIX + "employment_income",
        ),
    }
    assert table.category_for(
        "calibration.gov.irs.soi.wages_per_capita", _links(graph)
    ) == ("CBO employment income", table.CBO_INCOME_PREFIX + "employment_income")


def test_category_for_names_the_first_named_series_on_the_chain():
    graph = {"gov.states.ss.supplement": (None, "gov.ssa.ssi.amount")}
    graph["gov.ssa.ssi.amount"] = (None, "gov.ssa.uprating")
    assert table.category_for("gov.states.ss.supplement", _links(graph)) == (
        "Social Security (CPI-W)",
        "gov.ssa.uprating",
    )


def test_category_for_marks_an_unnamed_root_as_other():
    graph = {"gov.zz.index": (None, "self")}
    assert table.category_for("gov.zz.index", _links(graph)) == (
        "Other: gov.zz.index",
        "gov.zz.index",
    )


def test_category_for_stops_on_a_loop():
    graph = {"a": (None, "b"), "b": ("a", None)}
    with pytest.raises(table.TableError, match="loops"):
        table.category_for("a", _links(graph))


NODES = st.sampled_from(
    [
        "n0",
        "n1",
        "n2",
        "n3",
        "n4",
        "gov.irs.uprating",
        "gov.ssa.nawi",
        table.CBO_INCOME_PREFIX + "employment_income",
    ]
)
GRAPHS = st.dictionaries(
    NODES,
    st.tuples(
        st.one_of(st.none(), NODES),
        st.one_of(st.none(), st.just("self"), NODES),
    ),
)


@given(series=NODES, graph=GRAPHS)
def test_category_for_ends_on_every_finite_graph(series, graph):
    try:
        category, named = table.category_for(series, _links(graph))
    except table.TableError as error:
        assert "loops" in str(error)
        return
    if category.startswith("Other: "):
        assert category == f"Other: {named}"
        assert table.named_category(named) is None
    else:
        assert table.named_category(named) == category


def test_every_formula_step_names_a_categorized_index():
    for step, series in table.FORMULA_STEPS.items():
        assert table.named_category(series), step
    assert not table.INDEX_STEPS & table.FORMULA_STEPS.keys()
    assert table.formula_spec("gov.ssa.nawi", "extend_x") == "gov.ssa.nawi via extend_x"


# ---------------------------------------------------------------------------
# Reading leaf values
# ---------------------------------------------------------------------------


def test_effective_value_reads_the_latest_value_on_or_before_the_instant():
    values = (("2026-01-01", 3), ("2025-01-01", 2), ("2024-01-01", 1))
    assert table.effective_value(values, "2025-06-01") == 2
    assert table.effective_value(values, "2026-01-01") == 3
    assert table.effective_value(values, "2023-12-31") is None
    assert table.last_instant(values) == "2026-01-01"
    assert table.last_instant(()) is None


INSTANTS = st.dates(min_value=dt.date(2020, 1, 1), max_value=dt.date(2100, 1, 1)).map(
    lambda day: day.isoformat()
)
LEAVES = st.dictionaries(INSTANTS, st.integers(-5, 5), max_size=8).map(
    lambda values: tuple(sorted(values.items(), reverse=True))
)


@given(values=LEAVES, instant=INSTANTS)
def test_effective_value_agrees_with_the_latest_earlier_instant(values, instant):
    earlier = [(start, value) for start, value in values if start <= instant]
    expected = max(earlier)[1] if earlier else None
    assert table.effective_value(values, instant) == expected


@given(before=LEAVES, after=LEAVES, since=INSTANTS)
def test_projection_differs_only_where_a_value_differs(before, after, since):
    assert not table.projection_differs(before, before, since)
    differs = table.projection_differs(before, after, since)
    assert differs == table.projection_differs(after, before, since)
    instants = {i for i, _ in before + after if i > since}
    assert differs == any(
        table.effective_value(before, i) != table.effective_value(after, i)
        for i in instants
    )


def test_git_blob_sha_matches_git():
    # `printf 'hello\n' | git hash-object --stdin`
    assert table.git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"
    assert table.git_blob_sha(b"") == hashlib.sha1(b"blob 0\0").hexdigest()


# ---------------------------------------------------------------------------
# render_table
# ---------------------------------------------------------------------------

# Field text with the characters CSV must quote. The generator's fields never
# hold carriage returns or NULs: descriptions pass through single_line.
FIELD_TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\r\x00"),
    max_size=20,
) | st.sampled_from(['a, "quoted" b', "two\nlines", ""])

ROWS = st.lists(
    st.fixed_dictionaries(
        {
            "type": st.sampled_from(["parameter", "variable"]),
            "uprating_category": st.sampled_from(["CPI-U", "CBO a", "Population"]),
            "path": st.text(alphabet="abc._", min_size=1, max_size=8),
            "file_path": st.text(min_size=1, max_size=8),
            "uprating": FIELD_TEXT,
            "description": FIELD_TEXT,
        }
    ),
    max_size=10,
    unique_by=lambda row: (row["type"], row["path"]),
)


@given(ROWS)
def test_render_table_round_trips_in_canonical_order(rows):
    text = table.render_table(rows)
    reader = csv.DictReader(io.StringIO(text, newline=""))
    assert tuple(reader.fieldnames) == table.COLUMNS
    parsed = list(reader)
    assert parsed == sorted(rows, key=table.sort_key)
    assert table.render_table(parsed) == text


# ---------------------------------------------------------------------------
# The committed table
# ---------------------------------------------------------------------------

TABLE_TEXT = table.TABLE_PATH.read_text(encoding="utf-8")
TABLE_ROWS = list(csv.DictReader(io.StringIO(TABLE_TEXT, newline="")))
FORMULA = re.compile(r"^(\S+)" + re.escape(table.FORMULA_SEPARATOR) + r"(\w+)$")


def test_committed_table_is_in_canonical_form():
    assert TABLE_ROWS
    assert table.render_table(TABLE_ROWS) == TABLE_TEXT


def test_committed_table_has_one_row_per_file_or_variable():
    keys = [(row["type"], row["path"]) for row in TABLE_ROWS]
    assert len(keys) == len(set(keys))
    files = [row["file_path"] for row in TABLE_ROWS if row["type"] == "parameter"]
    assert len(files) == len(set(files))
    for row in TABLE_ROWS:
        if row["type"] == "parameter":
            assert row["path"] == table.parameter_name(row["file_path"])
            assert row["file_path"].endswith(table.YAML_SUFFIXES)
        else:
            assert row["type"] == "variable"
            assert row["file_path"].endswith(".py")


def test_committed_table_names_every_category():
    unnamed = sorted(
        {
            row["uprating_category"]
            for row in TABLE_ROWS
            if not row["uprating_category"]
            or row["uprating_category"].startswith("Other: ")
        }
    )
    assert unnamed == []


def test_committed_formula_rows_match_the_formula_steps():
    for row in TABLE_ROWS:
        for part in row["uprating"].split(table.SPEC_SEPARATOR):
            match = FORMULA.match(part)
            if match:
                series, step = match.groups()
                assert row["type"] == "parameter", row["path"]
                assert table.FORMULA_STEPS.get(step) == series, row["path"]
