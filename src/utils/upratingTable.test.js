import { readFileSync } from "node:fs";

import fc from "fast-check";
import { describe, expect, it } from "vitest";

import { POLICYENGINE_US_SNAPSHOT } from "./policyengineUsSource";
import {
  FORMULA_LINES,
  FORMULA_MODULE,
  OTHER_CARD,
  UPRATING_CARDS,
  cardForCategory,
  counted,
  formatShare,
  formulaSourceUrl,
  formulaSteps,
  parseUpratingTable,
  summarizeUprating,
} from "./upratingTable";

const rows = parseUpratingTable(
  readFileSync("public/data/uprating_analysis.csv", "utf8"),
);
const listedFiles = new Set(
  readFileSync("tests/fixtures/policyengine-us-files.txt", "utf8")
    .split("\n")
    .filter((line) => line && !line.startsWith("#")),
);
// Read here apart from the module's import of it.
const formulaLines = JSON.parse(
  readFileSync("src/data/upratingFormulaLines.json", "utf8"),
);

// Counts the cards should show, tallied here without summarizeUprating.
function independentCounts(table) {
  const counts = new Map();
  for (const row of table) {
    const claimed = UPRATING_CARDS.filter((card) =>
      card.includes(row.uprating_category),
    );
    const id = claimed.length ? claimed[0].id : OTHER_CARD.id;
    counts.set(id, (counts.get(id) ?? 0) + 1);
  }
  return counts;
}

const CATEGORY_POOL = [
  "IRS chained CPI-U",
  "Chained CPI-U",
  "CPI-U",
  "CBO employment income",
  "CBO a new source",
  "Population",
  "California CPI",
  "Social Security (CPI-W)",
  "CMS health spending",
  "A category no card claims",
  "Another unclaimed category",
];

// Tables of up to 40 rows, with categories the cards claim, categories they
// don't, and arbitrary text.
const tables = fc
  .array(
    fc.record({
      type: fc.constantFrom("parameter", "variable"),
      uprating_category: fc.oneof(
        fc.constantFrom(...CATEGORY_POOL),
        fc.string({ maxLength: 12 }),
      ),
    }),
    { maxLength: 40 },
  )
  .map((entries) =>
    entries.map((entry, index) => ({ ...entry, path: `row_${index}` })),
  );

describe("the uprating table", () => {
  it("parses the committed CSV", () => {
    expect(rows.length).toBeGreaterThan(0);
    expect(Object.keys(rows[0])).toEqual([
      "type",
      "uprating_category",
      "path",
      "file_path",
      "uprating",
      "description",
    ]);
  });

  it("refuses a malformed table", () => {
    expect(() =>
      parseUpratingTable('type,path\nparameter,"unclosed\n'),
    ).toThrow(/Uprating table row/);
  });
});

describe("formula rows", () => {
  it("read the index and the function from the generator's format", () => {
    expect(
      formulaSteps({
        uprating: "gov.ssa.nawi via extend_social_security_payroll_cap",
      }),
    ).toEqual([
      { series: "gov.ssa.nawi", step: "extend_social_security_payroll_cap" },
    ]);
    expect(
      formulaSteps({ uprating: "gov.irs.uprating; gov.bls.cpi.cpi_u via f" }),
    ).toEqual([{ series: "gov.bls.cpi.cpi_u", step: "f" }]);
    expect(
      formulaSteps({
        uprating: "{'parameter': 'gov.irs.uprating', 'rounding': 50}",
      }),
    ).toEqual([]);
    expect(formulaSteps({ uprating: "" })).toEqual([]);
    expect(formulaSteps(undefined)).toEqual([]);
  });

  it("link to the lines that grow them, at the pinned commit", () => {
    expect(FORMULA_LINES).toEqual(formulaLines);
    expect(formulaLines.commit).toBe(POLICYENGINE_US_SNAPSHOT.commit);
    expect(formulaLines.module).toBe(FORMULA_MODULE);
    expect(listedFiles.has(FORMULA_MODULE)).toBe(true);

    const formulaRows = rows.filter((row) => formulaSteps(row).length);
    expect(formulaRows.length).toBeGreaterThan(0);
    // One anchor for each formula row, and none for a path the table lacks.
    expect(Object.keys(formulaLines.lines).sort()).toEqual(
      formulaRows.map((row) => row.path).sort(),
    );
    for (const row of formulaRows) {
      const lines = formulaLines.lines[row.path];
      expect(lines).toMatch(/^L\d+-L\d+$/);
      const [start, end] = lines.slice(1).split("-L").map(Number);
      expect(start).toBeGreaterThan(0);
      expect(end).toBeGreaterThanOrEqual(start);
      expect(formulaSourceUrl(row)).toBe(
        `https://github.com/PolicyEngine/policyengine-us/blob/${POLICYENGINE_US_SNAPSHOT.commit}/${FORMULA_MODULE}#${lines}`,
      );
    }
  });

  it("give no formula link to a row no formula grows", () => {
    expect(
      formulaSourceUrl({
        path: "gov.irs.income.bracket",
        uprating: "gov.irs.uprating",
      }),
    ).toBeNull();
    expect(formulaSourceUrl(undefined)).toBeNull();
  });

  it("appear only for parameters", () => {
    const misplaced = rows
      .filter((row) => formulaSteps(row).length && row.type !== "parameter")
      .map((row) => row.path);
    expect(misplaced).toEqual([]);
  });
});

describe("the uprating cards", () => {
  const summary = summarizeUprating(rows);

  it("count every row once", () => {
    expect(summary.total).toBe(rows.length);
    expect(summary.parameters + summary.variables).toBe(rows.length);
    expect(summary.parameters).toBe(
      rows.filter((row) => row.type === "parameter").length,
    );
    const sum = summary.cards.reduce((total, card) => total + card.count, 0);
    expect(sum).toBe(rows.length);
    for (const card of summary.cards) {
      expect(card.parameters + card.variables).toBe(card.count);
      expect(card.share).toBeCloseTo(card.count / rows.length, 12);
    }
  });

  it("match a count made without the summary", () => {
    const expected = independentCounts(rows);
    expect(
      Object.fromEntries(summary.cards.map((card) => [card.id, card.count])),
    ).toEqual(Object.fromEntries(expected));
  });

  it("give each category to exactly one card", () => {
    const categories = new Set(rows.map((row) => row.uprating_category));
    const claims = [...categories]
      .map((category) => [
        category,
        UPRATING_CARDS.filter((card) => card.includes(category)).length,
      ])
      .filter(([, count]) => count > 1);
    expect(claims).toEqual([]);
    // Every category in the pinned table has a card of its own.
    expect(summary.cards.map((card) => card.id)).not.toContain(OTHER_CARD.id);
  });

  it("list the largest card first", () => {
    const counts = summary.cards.map((card) => card.count);
    expect(counts).toEqual([...counts].sort((a, b) => b - a));
  });

  it("show only examples the table holds, each in its own card", () => {
    const byPath = new Map(rows.map((row) => [row.path, row]));
    const problems = [];
    for (const card of UPRATING_CARDS) {
      for (const example of card.examples) {
        const row = byPath.get(example.path);
        if (!row) problems.push(`${card.id}: ${example.path} is not a row`);
        else if (cardForCategory(row.uprating_category).id !== card.id) {
          problems.push(
            `${card.id}: ${example.path} falls in ${row.uprating_category}`,
          );
        }
      }
    }
    expect(problems).toEqual([]);
    for (const card of summary.cards) {
      const source = UPRATING_CARDS.find((entry) => entry.id === card.id);
      expect(card.examples).toEqual(source.examples);
    }
  });

  it("hold their invariants on generated tables", () => {
    fc.assert(
      fc.property(tables, (table) => {
        const result = summarizeUprating(table);
        const cards = result.cards;
        expect(result.total).toBe(table.length);
        expect(cards.reduce((total, card) => total + card.count, 0)).toBe(
          table.length,
        );
        expect(cards.every((card) => card.count > 0)).toBe(true);
        expect(
          Object.fromEntries(cards.map((card) => [card.id, card.count])),
        ).toEqual(Object.fromEntries(independentCounts(table)));
        // OTHER_CARD comes last and lists exactly the unclaimed categories.
        const other = cards.find((card) => card.id === OTHER_CARD.id);
        if (other) expect(cards.at(-1)).toBe(other);
        const unclaimed = new Set(
          table
            .map((row) => row.uprating_category)
            .filter(
              (category) =>
                !UPRATING_CARDS.some((card) => card.includes(category)),
            ),
        );
        expect(new Set(other?.categories.map((c) => c.name) ?? [])).toEqual(
          unclaimed,
        );
        const ranked = cards.filter((card) => card.id !== OTHER_CARD.id);
        const counts = ranked.map((card) => card.count);
        expect(counts).toEqual([...counts].sort((a, b) => b - a));
        for (const card of cards) {
          const inCategories = card.categories.reduce(
            (total, category) => total + category.count,
            0,
          );
          expect(inCategories).toBe(card.count);
        }
        const shares = cards.reduce((total, card) => total + card.share, 0);
        expect(shares).toBeCloseTo(table.length ? 1 : 0, 12);
      }),
      { numRuns: 300 },
    );
  });
});

describe("formatShare", () => {
  it("rounds to whole percents and marks a share that rounds to zero", () => {
    expect(formatShare(0.5234)).toBe("52%");
    expect(formatShare(0.004)).toBe("<1%");
    expect(formatShare(0)).toBe("0%");
    expect(formatShare(1)).toBe("100%");
  });
});

describe("counted", () => {
  it("names one item in the singular and any other count in the plural", () => {
    expect(counted(1, "parameter")).toBe("1 parameter");
    expect(counted(0, "variable")).toBe("0 variables");
    expect(counted(932, "item")).toBe("932 items");
  });
});
