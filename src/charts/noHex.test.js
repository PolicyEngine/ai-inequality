import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";

import { parse } from "espree";

// Chart code draws every colour from kitTheme.js, so it holds no colour
// literal of its own: no hex, rgb(), rgba(), hsl() or hsla(), and no named
// colour such as "white" in a stroke, fill or color prop. Comments don't
// count; kitTheme.js names each token's hex value in one.

const ROOT = process.cwd();
const SRC = join(ROOT, "src");

const COLOUR_LITERAL = /#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?)\s*\(/gi;
const COLOUR_PROPS = new Set([
  "stroke",
  "fill",
  "color",
  "background",
  "backgroundColor",
  "borderColor",
  "stopColor",
  "floodColor",
  "lightingColor",
]);
// Values a colour prop may take that name no colour.
const KEYWORDS = new Set([
  "none",
  "transparent",
  "currentcolor",
  "inherit",
  "initial",
  "unset",
]);

function sourceFiles(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(js|jsx)$/.test(entry.name) && !/\.test\.(js|jsx)$/.test(path)
      ? [path]
      : [];
  });
}

function parseModule(source) {
  return parse(source, {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: { jsx: true },
    comment: true,
    loc: true,
    range: true,
  });
}

function walk(node, visit) {
  if (!node || typeof node.type !== "string") return;
  visit(node);
  for (const [key, value] of Object.entries(node)) {
    if (key === "loc" || key === "range") continue;
    if (Array.isArray(value)) value.forEach((child) => walk(child, visit));
    else if (value && typeof value === "object") walk(value, visit);
  }
}

const lineOf = (source, index) => source.slice(0, index).split("\n").length;

// Every colour literal in a module's code, as "line: text".
export function colourLiterals(source) {
  const ast = parseModule(source);
  // Blank out comments, keeping offsets, so line numbers stay right.
  let code = source;
  for (const { range } of ast.comments) {
    const [start, end] = range;
    code =
      code.slice(0, start) +
      code.slice(start, end).replace(/[^\n]/g, " ") +
      code.slice(end);
  }
  const found = [...code.matchAll(COLOUR_LITERAL)].map(
    (match) => `${lineOf(source, match.index)}: ${match[0]}`,
  );
  const namedColour = (node, prop) => {
    if (!COLOUR_PROPS.has(prop)) return;
    const value =
      node?.type === "JSXExpressionContainer" ? node.expression : node;
    if (value?.type !== "Literal" || typeof value.value !== "string") return;
    const word = value.value.trim();
    if (/^[a-z]+$/i.test(word) && !KEYWORDS.has(word.toLowerCase())) {
      found.push(`${value.loc.start.line}: ${prop}="${word}"`);
    }
  };
  walk(ast, (node) => {
    if (node.type === "JSXAttribute") namedColour(node.value, node.name.name);
    if (node.type === "Property" && !node.computed) {
      namedColour(node.value, node.key.name ?? node.key.value);
    }
  });
  return found;
}

const importsRecharts = (source) =>
  /from\s+["']recharts["']/.test(source) ||
  /require\(\s*["']recharts["']\s*\)/.test(source);

const CHART_FILES = sourceFiles(SRC).filter(
  (path) =>
    importsRecharts(readFileSync(path, "utf8")) ||
    path === join(SRC, "utils", "chartStyles.js") ||
    path.startsWith(join(SRC, "charts")),
);

test("the scan finds each kind of colour literal and skips comments", () => {
  const sample = [
    "// #ffffff in a comment",
    "/* rgb(0, 0, 0) in a comment */",
    'const a = "#227773";',
    "const b = { color: 'rgba(0, 0, 0, 0.5)' };",
    'const c = "hsl(180 50% 40%)";',
    'const d = <Line stroke="white" fill="none" />;',
    "const e = { fill: 'orange', stroke: 'var(--chart-1)' };",
    'const f = "https://example.org/#about";',
  ].join("\n");
  expect(colourLiterals(sample)).toEqual([
    "3: #227773",
    "4: rgba(",
    "5: hsl(",
    '6: stroke="white"',
    '7: fill="orange"',
  ]);
});

test("the scan covers every file that draws a chart", () => {
  const names = CHART_FILES.map((path) => relative(ROOT, path));
  expect(names).toContain("src/components/ShiftSweep.jsx");
  expect(names).toContain("src/components/AIScenarios.jsx");
  expect(names).toContain("src/components/IncomeDistributionBreakdown.jsx");
  expect(names).toContain("src/utils/chartStyles.js");
  expect(names).toContain("src/charts/kitTheme.js");
});

test.each(CHART_FILES.map((path) => [relative(ROOT, path), path]))(
  "%s holds no colour literal",
  (_name, path) => {
    expect(colourLiterals(readFileSync(path, "utf8"))).toEqual([]);
  },
);
