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
- a leaf read as policyengine-core reads it agrees with itself; two readings
  differ after an instant exactly when the values in force on some later day
  differ; and a leaf's value changes after an instant exactly when the value
  in force on some later day differs from the one in force then;
- following uprating chains from a set of series gives a set that holds every
  series in the system it starts from and every link of each series it holds;
- each dataset override lands once, as agreeing with, differing from, or
  missing from the row that ends up holding its column's values.

With stand-ins for policyengine-core's parameters, they check that the
recorder credits each value to the step that set it, and that the run stops on
each gap the generator promises to report: an unknown or missing step, a
formula step that stops reading its index, a leaf that two mechanisms grow, a
leaf that outruns what it held by no known mechanism, an extended index series
that no value grows by and no list names, an installed file that differs from
the pinned commit, and a stale table under --check.

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
import json
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


@settings(deadline=None)
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


@settings(deadline=None)
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
    assert table.named_category("calibration.gov.hhs.medicare.per_capita_cost") == (
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


@settings(deadline=None)
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


def test_index_series_lists_name_each_series_once_with_a_category():
    assert not table.DIRECT_INDEX_SERIES.keys() & table.UNREAD_INDEX_SERIES
    for series, readers in table.DIRECT_INDEX_SERIES.items():
        assert table.named_category(series), series
        assert readers and all(reader.endswith(".py") for reader in readers)


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


@settings(deadline=None)
@given(values=LEAVES, instant=INSTANTS)
def test_effective_value_agrees_with_the_latest_earlier_instant(values, instant):
    earlier = [(start, value) for start, value in values if start <= instant]
    expected = max(earlier)[1] if earlier else None
    assert table.effective_value(values, instant) == expected


def test_day_after_steps_one_day_and_starts_the_calendar_for_none():
    assert table.day_after("2025-12-31") == "2026-01-01"
    assert table.day_after("2024-02-28") == "2024-02-29"
    assert table.day_after("") == "0001-01-01"


def test_projection_differs_compares_the_values_in_force_after_the_instant():
    # Both versions set 2020 only, so they differ in every later year.
    before, after = (("2020-01-01", 1),), (("2020-01-01", 2),)
    assert table.projection_differs(before, after, "2025-01-01")
    # A difference that ends before the instant doesn't count.
    before = (("2030-01-01", 5), ("2020-01-01", 1))
    after = (("2030-01-01", 5), ("2020-01-01", 2))
    assert not table.projection_differs(before, after, "2030-01-01")
    # On 31 December 2029, the day after this instant, the two still differ.
    assert table.projection_differs(before, after, "2029-12-30")


def test_changes_after_compares_later_values_with_the_one_in_force():
    values = (("2030-01-01", 2), ("2027-01-01", 1), ("2026-01-01", 1))
    assert table.changes_after(values, "2026-01-01")
    assert not table.changes_after(values, "2030-01-01")
    # A later instant that repeats the value in force isn't a change.
    assert not table.changes_after((("2027-01-01", 0), ("2026-01-01", 0)), "2026-01-01")
    # From no value at all, any value is a change.
    assert table.changes_after((("2026-01-01", 0),), "")
    assert not table.changes_after((), "")


# Leaves that change value only on 1 January of 2020-2030, so the value in force
# holds within each year, and instants on several days of 2019-2031. Sampling
# days through 2032 checks the helpers against their meaning, not their method.
YEAR_STARTS = st.integers(2020, 2030).map(lambda year: f"{year}-01-01")
YEAR_LEAVES = st.dictionaries(YEAR_STARTS, st.integers(-2, 2), max_size=6).map(
    lambda values: tuple(sorted(values.items(), reverse=True))
)
SAMPLE_DAYS = [
    f"{year}-{day}"
    for year in range(2019, 2033)
    for day in ("01-01", "01-02", "07-01", "12-31")
]
SINCE = st.sampled_from([day for day in SAMPLE_DAYS if day < "2032-01-01"])


@settings(deadline=None)
@given(before=YEAR_LEAVES, after=YEAR_LEAVES, since=SINCE)
def test_projection_differs_exactly_when_a_later_day_differs(before, after, since):
    expected = any(
        table.effective_value(before, day) != table.effective_value(after, day)
        for day in SAMPLE_DAYS
        if day > since
    )
    assert table.projection_differs(before, after, since) == expected
    assert table.projection_differs(after, before, since) == expected
    assert not table.projection_differs(before, before, since)


@settings(deadline=None)
@given(values=YEAR_LEAVES, since=SINCE)
def test_changes_after_exactly_when_a_later_day_holds_another_value(values, since):
    in_force = table.effective_value(values, since)
    expected = any(
        table.effective_value(values, day) != in_force
        for day in SAMPLE_DAYS
        if day > since
    )
    assert table.changes_after(values, since) == expected


def test_git_blob_sha_matches_git():
    # `printf 'hello\n' | git hash-object --stdin`
    assert table.git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"
    assert table.git_blob_sha(b"") == hashlib.sha1(b"blob 0\0").hexdigest()


# ---------------------------------------------------------------------------
# Index series: which ones values grow by, and which ones formulas read
# ---------------------------------------------------------------------------


def test_series_in_use_follows_each_chain_to_its_end():
    graph = {
        "row.series": (None, "gov.irs.uprating"),
        "gov.irs.uprating": ("gov.bls.cpi.c_cpi_u", "self"),
        "gov.bls.cpi.c_cpi_u": (None, None),
        "unused": (None, "gov.bls.cpi.cpi_u"),
    }
    exists = graph.__contains__
    assert table.series_in_use({"row.series", None}, _links(graph), exists) == {
        "row.series",
        "gov.irs.uprating",
        "gov.bls.cpi.c_cpi_u",
    }
    # A series the system lacks ends its chain.
    assert table.series_in_use(
        {"row.series"}, _links(graph), lambda s: s != "gov.irs.uprating"
    ) == {"row.series"}


@settings(deadline=None)
@given(
    starts=st.sets(NODES, max_size=4), graph=GRAPHS, absent=st.sets(NODES, max_size=2)
)
def test_series_in_use_holds_its_starts_and_every_link(starts, graph, absent):
    def exists(name):
        return name not in absent

    used = table.series_in_use(starts, _links(graph), exists)
    assert {series for series in starts if exists(series)} <= used
    for series in used:
        assert exists(series) and series != "self"
        for link in graph.get(series, (None, None)):
            if link and link != "self" and exists(link):
                assert link in used


def test_files_naming_finds_a_series_by_its_last_two_parts():
    series = "calibration.gov.hhs.medicare.per_capita_cost"
    sources = {
        "full.py": "parameters(period).calibration.gov.hhs.medicare.per_capita_cost",
        "bound.py": "p = parameters(period).calibration.gov.hhs\np.medicare.per_capita_cost",
        "other_program.py": "parameters(period).gov.hhs.medicaid.per_capita_cost",
        "longer_name.py": "from x.medicare.per_capita_cost_helpers import f",
        "parent_only.py": "p = parameters(period).calibration.gov.hhs.medicare\np.per_capita_cost",
    }
    assert table.files_naming(series, sources) == {"full.py", "bound.py"}


@pytest.fixture
def index_lists(monkeypatch):
    monkeypatch.setattr(table, "DIRECT_INDEX_SERIES", {"s.direct": ("gov/reader.py",)})
    monkeypatch.setattr(table, "UNREAD_INDEX_SERIES", frozenset({"s.unread"}))


STEP = "extend_parameter_values"
EXTENDED = {"s.used": STEP, "s.direct": STEP, "s.unread": STEP}
SOURCES = {"gov/reader.py": "cost = parameters(period).s.direct", "gov/other.py": ""}


def test_index_rows_gives_rows_to_the_series_formulas_read(index_lists):
    assert table.index_rows(EXTENDED, {"s.used"}, SOURCES) == {"s.direct": STEP}
    # A series a formula reads keeps its row when values also grow by it.
    assert table.index_rows(EXTENDED, {"s.used", "s.direct"}, SOURCES) == {
        "s.direct": STEP
    }


@pytest.mark.parametrize(
    ("extended", "in_use", "sources", "message"),
    [
        ({**EXTENDED, "s.new": STEP}, {"s.used"}, SOURCES, "leave out"),
        (
            {"s.used": STEP, "s.direct": STEP},
            {"s.used"},
            SOURCES,
            "no index step extends",
        ),
        (EXTENDED, {"s.used", "s.unread"}, SOURCES, "a value grows by"),
        (
            EXTENDED,
            {"s.used"},
            {**SOURCES, "gov/new.py": "p.s.unread"},
            "Variables that name UNREAD_INDEX_SERIES",
        ),
        (EXTENDED, {"s.used"}, {"gov/reader.py": ""}, "no longer name their series"),
    ],
)
def test_index_rows_stops_on_each_gap_in_the_lists(
    index_lists, extended, in_use, sources, message
):
    with pytest.raises(table.TableError, match=message):
        table.index_rows(extended, in_use, sources)


def test_call_spans_cover_each_statement_and_the_comment_above_it():
    source = (
        "def entry(p):\n"  # 1
        "    x = 1\n"  # 2
        "\n"  # 3
        "    # Why the cap grows\n"  # 4
        "    # with wages.\n"  # 5
        "    grow(\n"  # 6
        "        p,\n"  # 7
        "    )\n"  # 8
        "    for name in NAMES:\n"  # 9
        "        grow(name)\n"  # 10
        "    return p\n"  # 11
        "\n"  # 12
        "def other():\n"  # 13
        "    grow(1)\n"  # 14
    )
    spans = table.call_spans(source, "entry")
    assert spans[6] == spans[7] == spans[8] == (4, 8)
    assert spans[2] == (2, 2)
    assert spans[10] == (10, 10)
    assert spans[11] == (11, 11)
    # A loop's own line and another function's statements get no span.
    assert 9 not in spans and 14 not in spans
    with pytest.raises(table.TableError, match="no function missing"):
        table.call_spans(source, "missing")


def test_formula_links_name_the_one_call_that_grows_each_row():
    spans = {6: (4, 8), 7: (4, 8), 10: (10, 10)}
    calls = {"a.x": {6}, "a.y": {7}, "b": {10}}
    assert table.formula_links({"a": ["a.x", "a.y"], "b": ["b"]}, calls, spans) == {
        "a": "L4-L8",
        "b": "L10-L10",
    }


@pytest.mark.parametrize(
    "calls", [{"a.x": {6}, "a.y": {10}}, {"a.x": set()}, {"a.x": {99}}]
)
def test_formula_links_stop_on_a_row_without_exactly_one_call(calls):
    spans = {6: (4, 8), 10: (10, 10)}
    with pytest.raises(table.TableError, match="one call"):
        table.formula_links({"a": ["a.x", "a.y"]}, calls, spans)


def test_render_formula_lines_sorts_the_rows_under_the_commit():
    text = table.render_formula_lines("abc", {"b": "L2-L3", "a": "L1-L1"})
    assert text.endswith("}\n")
    document = json.loads(text)
    assert document == {
        "commit": "abc",
        "module": "policyengine_us/parameters/uprating_extensions.py",
        "lines": {"a": "L1-L1", "b": "L2-L3"},
    }
    assert list(document["lines"]) == ["a", "b"]


# ---------------------------------------------------------------------------
# The extension recorder and extension_growth, with stand-in parameters
# ---------------------------------------------------------------------------


class _Value:
    def __init__(self, instant_str, value):
        self.instant_str, self.value = instant_str, value


class FakeParameter:
    """A leaf shaped like policyengine-core's Parameter, as the recorder sees it."""

    def __init__(self, name, values, metadata=None):
        self.name = name
        self.values_list = [
            _Value(i, v) for i, v in sorted(values.items(), reverse=True)
        ]
        self.metadata = dict(metadata or {})

    def update(self, period=None, value=None, start=None):
        instant = start or period
        self.values_list = [v for v in self.values_list if v.instant_str != instant]
        self.values_list.append(_Value(instant, value))
        self.values_list.sort(key=lambda v: v.instant_str, reverse=True)

    def _get_at_instant(self, instant):
        for value in self.values_list:
            if value.instant_str <= instant:
                return value.value
        return None

    def __call__(self, instant):
        return self._get_at_instant(instant)


class FakeTree(dict):
    def get_descendants(self):
        return iter(list(self.values()))


CAP = "gov.irs.payroll.social_security.cap"
FORMULA = {"extend_social_security_payroll_cap": "gov.ssa.nawi"}


def _tree():
    return FakeTree(
        {
            "gov.bls.cpi.cpi_u": FakeParameter(
                "gov.bls.cpi.cpi_u", {"2024-01-01": 300.0}
            ),
            "gov.ssa.nawi": FakeParameter("gov.ssa.nawi", {"2024-01-01": 60_000.0}),
            CAP: FakeParameter(
                CAP, {"2024-01-01": 168_600.0}, {"uprating": "gov.ssa.nawi"}
            ),
            "gov.x.flat": FakeParameter("gov.x.flat", {"2024-01-01": 1.0}),
        }
    )


def _set(leaf, instant, value):
    leaf.update(period=instant, value=value)


# Stand-ins for policyengine-us's steps, named as the real ones are.
def extend_parameter_values(leaf):
    leaf.update(period="2025-01-01", value=leaf("2024-01-01") * 1.03)


def extend_social_security_payroll_cap(tree):
    nawi = tree["gov.ssa.nawi"]
    # Through a helper, so the recorder must credit the step that called it.
    _set(
        tree[CAP],
        "2025-01-01",
        tree[CAP]("2024-01-01") * nawi("2025-01-01") / nawi("2024-01-01"),
    )


def set_all_uprating_parameters(tree):
    extend_parameter_values(tree["gov.bls.cpi.cpi_u"])
    extend_parameter_values(tree["gov.ssa.nawi"])
    extend_social_security_payroll_cap(tree)
    return tree


def mystery_step(tree):
    _set(tree["gov.x.flat"], "2030-01-01", 2.0)


# Other entries repeat the steps rather than call set_all_uprating_parameters,
# which the recorder would then credit as a step of their own.
def entry_with_a_mystery_step(tree):
    extend_parameter_values(tree["gov.bls.cpi.cpi_u"])
    extend_parameter_values(tree["gov.ssa.nawi"])
    extend_social_security_payroll_cap(tree)
    mystery_step(tree)
    return tree


def entry_that_extends_the_cap_twice(tree):
    extend_parameter_values(tree["gov.bls.cpi.cpi_u"])
    extend_parameter_values(tree["gov.ssa.nawi"])
    extend_social_security_payroll_cap(tree)
    extend_parameter_values(tree[CAP])
    return tree


def _add(tree, name, values, metadata=None):
    tree[name] = FakeParameter(name, values, metadata)


def _uprate(tree):
    """Core's uprating, reduced: a leaf naming a series holds its value into 2026.

    The cap's formula already sets its projection, as in policyengine-us.
    """
    for leaf in tree.get_descendants():
        if leaf.metadata.get("uprating") and leaf.name != CAP:
            _set(leaf, "2026-01-01", leaf("2026-01-01"))
    return tree


def _build(entry=set_all_uprating_parameters, before_uprating=None, after=None):
    """Run the stand-in build: the entry, then uprating, as policyengine-us does."""
    tree = _tree()
    recorder = table.ExtensionRecorder(entry, FakeParameter)
    recorder.wrap()(tree)
    if before_uprating:
        before_uprating(tree)
    recorder.wrap_uprating(_uprate)(tree)
    if after:
        after(tree)
    return recorder, tree


def _growth(monkeypatch, recorder, tree, formula_steps=FORMULA):
    monkeypatch.setattr(table, "FORMULA_STEPS", formula_steps)
    report = {}
    formula, index = table.extension_growth(recorder, dict(tree), report)
    return formula, index, report


def test_recorder_credits_each_value_to_the_step_the_entry_called(monkeypatch):
    original = (FakeParameter.update, FakeParameter._get_at_instant)
    recorder, tree = _build()
    assert (FakeParameter.update, FakeParameter._get_at_instant) == original
    assert recorder.runs == recorder.uprating_runs == 1
    assert recorder.updated[CAP] == {"extend_social_security_payroll_cap"}
    assert recorder.updated["gov.ssa.nawi"] == {"extend_parameter_values"}
    assert "gov.ssa.nawi" in recorder.reads["extend_social_security_payroll_cap"]
    assert recorder.loaded[CAP] == (("2024-01-01", 168_600.0),)
    assert recorder.extended[CAP][0] == ("2025-01-01", 168_600.0 * 1.03)
    # The recorder notes the line of the entry's call that set each value.
    source = Path(__file__).read_text(encoding="utf-8")
    (line,) = recorder.calls[CAP]
    assert (
        source.splitlines()[line - 1].strip()
        == "extend_social_security_payroll_cap(tree)"
    )
    spans = table.call_spans(source, "set_all_uprating_parameters")
    assert table.formula_links({CAP: [CAP]}, recorder.calls, spans) == {
        CAP: f"L{line}-L{line}"
    }

    formula, index, report = _growth(monkeypatch, recorder, tree)
    assert formula == {CAP: "extend_social_security_payroll_cap"}
    assert index == {
        "gov.bls.cpi.cpi_u": "extend_parameter_values",
        "gov.ssa.nawi": "extend_parameter_values",
    }
    assert report["metadata_overridden_by_code"] == [CAP]
    assert report["added_after_uprating"] == []


def test_recorder_baseline_is_what_a_leaf_held_before_the_build_grew_it():
    def add_zero_child(tree):
        _add(tree, "gov.x.child", {"2040-01-01": 0})

    recorder, _ = _build(before_uprating=add_zero_child)
    assert recorder.baseline(CAP, True) == (("2024-01-01", 168_600.0),)
    assert recorder.baseline("gov.x.made_by_a_step", True) == ()
    assert recorder.baseline("gov.x.child", False) == (("2040-01-01", 0),)
    assert recorder.baseline("gov.x.added_later", False) is None


@pytest.mark.parametrize(
    ("entry", "formula_steps", "message"),
    [
        (entry_with_a_mystery_step, FORMULA, "leave out"),
        (
            set_all_uprating_parameters,
            {**FORMULA, "extend_gone": "gov.ssa.nawi"},
            "no longer runs",
        ),
        (
            set_all_uprating_parameters,
            {"extend_social_security_payroll_cap": "gov.bls.cpi.cpi_u"},
            "no longer read the index",
        ),
        (entry_that_extends_the_cap_twice, FORMULA, "several extension steps"),
    ],
)
def test_extension_growth_stops_on_a_step_it_cant_account_for(
    monkeypatch, entry, formula_steps, message
):
    recorder, tree = _build(entry)
    with pytest.raises(table.TableError, match=message):
        _growth(monkeypatch, recorder, tree, formula_steps)


def test_extension_growth_stops_when_metadata_also_grows_a_formula_leaf(monkeypatch):
    def regrow(tree):
        _set(tree[CAP], "2027-01-01", 1.0)

    recorder, tree = _build(after=regrow)
    with pytest.raises(table.TableError, match="metadata uprating both grow"):
        _growth(monkeypatch, recorder, tree)


@pytest.mark.parametrize(
    ("before_uprating", "after"),
    [
        # A leaf the files set gains a later value, with no uprating to explain it.
        (None, lambda tree: _set(tree["gov.x.flat"], "2040-01-01", 5.0)),
        # So does a leaf the build adds after the entry and before uprating.
        (
            lambda tree: _add(tree, "gov.x.child", {"2030-01-01": 1}),
            lambda tree: _set(tree["gov.x.child"], "2031-01-01", 2),
        ),
    ],
)
def test_extension_growth_stops_on_a_leaf_that_outruns_what_it_held(
    monkeypatch, before_uprating, after
):
    recorder, tree = _build(before_uprating=before_uprating, after=after)
    with pytest.raises(table.TableError, match="outrun"):
        _growth(monkeypatch, recorder, tree)


def test_extension_growth_stops_on_an_uprating_added_after_uprating(monkeypatch):
    def add(tree):
        _add(tree, "gov.x.late", {"2024-01-01": 1}, {"uprating": "gov.bls.cpi.cpi_u"})
        _add(tree, "gov.x.copy", {"2024-01-01": 1})

    recorder, tree = _build(after=add)
    with pytest.raises(table.TableError, match="after uprating that name"):
        _growth(monkeypatch, recorder, tree)
    del tree["gov.x.late"]
    report = _growth(monkeypatch, recorder, tree)[2]
    assert report["added_after_uprating"] == ["gov.x.copy"]


# ---------------------------------------------------------------------------
# The installed release against the pinned commit, and --check
# ---------------------------------------------------------------------------


def _install(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root / table.PACKAGE


INSTALLED = {
    "policyengine_us/parameters/gov/a.yaml": "values: {}\n",
    "policyengine_us/variables/b.py": "x = 1\n",
    "policyengine_us/variables/__pycache__/b.cpython-313.pyc": "compiled",
}


def _blobs(files):
    return {
        path: table.git_blob_sha(text.encode())
        for path, text in files.items()
        if "__pycache__" not in path
    }


def test_check_release_matches_commit_counts_the_matching_files(tmp_path, monkeypatch):
    package_dir = _install(tmp_path, INSTALLED)
    monkeypatch.setattr(
        table, "commit_blobs", lambda repository, commit: _blobs(INSTALLED)
    )
    snapshot = {"repository": "o/r", "version": "1.0", "commit": "abc"}
    assert table.check_release_matches_commit(snapshot, package_dir) == 2


@pytest.mark.parametrize(
    ("commit_files", "message"),
    [
        ({**INSTALLED, "policyengine_us/variables/c.py": "y = 2\n"}, "doesn't install"),
        ({"policyengine_us/variables/b.py": "x = 1\n"}, "lacks"),
        ({**INSTALLED, "policyengine_us/variables/b.py": "x = 2\n"}, "differ"),
    ],
)
def test_check_release_matches_commit_stops_on_any_difference(
    tmp_path, monkeypatch, commit_files, message
):
    package_dir = _install(tmp_path, INSTALLED)
    monkeypatch.setattr(
        table, "commit_blobs", lambda repository, commit: _blobs(commit_files)
    )
    snapshot = {"repository": "o/r", "version": "1.0", "commit": "abc"}
    with pytest.raises(table.TableError, match=message):
        table.check_release_matches_commit(snapshot, package_dir)


@pytest.fixture
def pinned_run(tmp_path, monkeypatch):
    """main() with the build replaced by fixed outputs, written under tmp_path.

    Returns the table's path and the formula lines' path.
    """
    table_path = tmp_path / "public" / "data" / "table.csv"
    lines_path = tmp_path / "src" / "data" / "lines.json"
    for path in (table_path, lines_path):
        path.parent.mkdir(parents=True)
    monkeypatch.setattr(table, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(table, "TABLE_PATH", table_path)
    monkeypatch.setattr(table, "FORMULA_LINES_PATH", lines_path)
    monkeypatch.setattr(
        table,
        "load_snapshot",
        lambda: {"repository": "o/r", "version": "1.0", "commit": "abc"},
    )
    monkeypatch.setattr(
        table, "reexecute_in_pinned_environment", lambda version, argv: None
    )
    monkeypatch.setattr(
        table,
        "build_table",
        lambda snapshot: (
            {table.TABLE_PATH: "type\nnew\n", table.FORMULA_LINES_PATH: "{}\n"},
            {"rows": []},
        ),
    )
    monkeypatch.setattr(table, "print_report", lambda snapshot, report: None)
    return table_path, lines_path


def test_check_passes_when_both_outputs_match_the_release(pinned_run, capsys):
    table_path, lines_path = pinned_run
    table_path.write_text("type\nnew\n", encoding="utf-8")
    lines_path.write_text("{}\n", encoding="utf-8")
    assert table.main(["--check"]) == 0
    out = capsys.readouterr().out
    assert "public/data/table.csv matches policyengine-us 1.0" in out
    assert "src/data/lines.json matches policyengine-us 1.0" in out


@pytest.mark.parametrize("stale", ["table", "lines"])
def test_check_fails_on_either_stale_output_and_leaves_both(pinned_run, capsys, stale):
    table_path, lines_path = pinned_run
    table_path.write_text("type\nold\n" if stale == "table" else "type\nnew\n")
    lines_path.write_text('{"old": 1}\n' if stale == "lines" else "{}\n")
    before = (table_path.read_text(), lines_path.read_text())
    assert table.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "is stale" in out
    assert ("-old" in out) if stale == "table" else ('-{"old": 1}' in out)
    assert (table_path.read_text(), lines_path.read_text()) == before


def test_a_run_without_check_writes_both_outputs(pinned_run):
    table_path, lines_path = pinned_run
    table_path.write_text("type\nold\n", encoding="utf-8")
    assert table.main([]) == 0
    assert table_path.read_text(encoding="utf-8") == "type\nnew\n"
    assert lines_path.read_text(encoding="utf-8") == "{}\n"


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


@settings(deadline=None)
@given(ROWS)
def test_render_table_round_trips_in_canonical_order(rows):
    text = table.render_table(rows)
    reader = csv.DictReader(io.StringIO(text, newline=""))
    assert tuple(reader.fieldnames) == table.COLUMNS
    parsed = list(reader)
    assert parsed == sorted(rows, key=table.sort_key)
    assert table.render_table(parsed) == text


# ---------------------------------------------------------------------------
# compare_dataset_growth
# ---------------------------------------------------------------------------


def _per_capita(series):
    return series + "_per_capita" if series.startswith("total.") else series


def test_compare_dataset_growth_follows_moves_and_per_capita_series():
    overrides = {
        "wages": "total.wages",
        "rent": "cpi",
        "weight": "population",
        "bonus": "total.agi",
    }
    moves = {"wages": "wages_before_response"}
    rows = {"wages_before_response": "total.wages_per_capita", "weight": "cpi"}
    agree, differ, unlisted = table.compare_dataset_growth(
        overrides, moves, rows, _per_capita
    )
    assert agree == [("wages", "wages_before_response", "total.wages_per_capita")]
    assert differ == [("weight", "weight", "population", "cpi")]
    assert unlisted == [("bonus", "total.agi_per_capita"), ("rent", "cpi")]


COLUMNS = st.sampled_from(["a", "b", "c", "d", "e"])
SERIES = st.sampled_from(["total.x", "total.y", "cpi", "population"])


@settings(deadline=None)
@given(
    overrides=st.dictionaries(COLUMNS, SERIES),
    moves=st.dictionaries(COLUMNS, COLUMNS),
    rows=st.dictionaries(COLUMNS, SERIES.map(_per_capita)),
)
def test_compare_dataset_growth_sorts_each_override_once(overrides, moves, rows):
    agree, differ, unlisted = table.compare_dataset_growth(
        overrides, moves, rows, _per_capita
    )
    columns = [entry[0] for entry in agree + differ + unlisted]
    assert sorted(columns) == sorted(overrides)
    for column, holder, series in agree:
        assert rows[holder] == series == _per_capita(overrides[column])
    for column, holder, series, listed in differ:
        assert listed == rows[holder] != series == _per_capita(overrides[column])
    for column, series in unlisted:
        assert moves.get(column, column) not in rows


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
                if step in table.INDEX_STEPS:
                    # An extended series a formula reads, grown from itself.
                    assert series in table.DIRECT_INDEX_SERIES, row["path"]
                    assert series == row["path"] or series.startswith(row["path"] + ".")
                else:
                    assert table.FORMULA_STEPS.get(step) == series, row["path"]


def test_committed_table_lists_the_index_series_formulas_read_and_no_unread_one():
    paths = {row["path"] for row in TABLE_ROWS if row["type"] == "parameter"}
    assert set(table.DIRECT_INDEX_SERIES) <= paths
    assert not paths & table.UNREAD_INDEX_SERIES


def test_committed_formula_lines_cover_each_formula_row_at_the_pinned_commit():
    text = table.FORMULA_LINES_PATH.read_text(encoding="utf-8")
    document = json.loads(text)
    formula_paths = {
        row["path"]
        for row in TABLE_ROWS
        if any(
            FORMULA.match(part) for part in row["uprating"].split(table.SPEC_SEPARATOR)
        )
    }
    assert set(document["lines"]) == formula_paths
    assert document["commit"] == table.load_snapshot()["commit"]
    for anchor in document["lines"].values():
        start, end = map(int, re.fullmatch(r"L(\d+)-L(\d+)", anchor).groups())
        assert 0 < start <= end
    assert table.render_formula_lines(document["commit"], document["lines"]) == text
