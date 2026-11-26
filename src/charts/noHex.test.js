import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";

import { parse } from "espree";

// Chart code draws every colour from kitTheme.js, so it holds no colour
// literal of its own: no hex and no CSS colour function such as rgb(),
// oklch() or color-mix() in any string, including one a template literal
// builds; no var() with a fallback, which could name a colour of its own; no
// CSS named colour such as "white" as a whole string; and no bare word in a
// colour prop, however its value is written. The scan reads strings, not
// code, so a function call such as color(dataKey) passes and comments don't
// count; kitTheme.js names each token's hex value in one.

const ROOT = process.cwd();
const SRC = join(ROOT, "src");
const APP = join(ROOT, "app");

// CSS allows no space between a function's name and its parenthesis, so
// prose such as "The Budget Lab (2026)" names no colour.
const COLOUR_LITERAL =
  /#[0-9a-f]{3,8}\b|\b(?:color-mix|light-dark|rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(|var\(\s*--[\w-]+\s*,/gi;
// A prop that takes a colour: fill, stroke, color, background and any name
// ending in one of them, such as stopColor, textFill or backgroundColor.
const COLOUR_PROP = /(?:fill|stroke|colou?r|background)$/i;
// The CSS named colours (CSS Color 4, as the color-name package lists them).
const NAMED_COLOURS = new Set(
  `aliceblue antiquewhite aqua aquamarine azure beige bisque black
  blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse
  chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan
  darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta
  darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen
  darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink
  deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen
  fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey
  honeydew hotpink indianred indigo ivory khaki lavender lavenderblush
  lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow
  lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen
  lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime
  limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid
  mediumpurple mediumseagreen mediumslateblue mediumspringgreen
  mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
  navajowhite navy oldlace olive olivedrab orange orangered orchid
  palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff
  peru pink plum powderblue purple rebeccapurple red rosybrown royalblue
  saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue
  slateblue slategray slategrey snow springgreen steelblue tan teal thistle
  tomato turquoise violet wheat white whitesmoke yellow yellowgreen`.split(
    /\s+/,
  ),
);
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

// Every colour literal in a module, as "line: text", in line order.
export function colourLiterals(source) {
  const ast = parseModule(source);
  const found = [];
  // Each string in the code: string literals and the fixed parts of
  // template literals.
  const strings = (root) => {
    const out = [];
    walk(root, (node) => {
      if (node.type === "Literal" && typeof node.value === "string") {
        out.push([node, node.value]);
      }
      if (node.type === "TemplateElement") {
        out.push([node, node.value.cooked ?? ""]);
      }
    });
    return out;
  };
  const reported = new Set();
  // A bare word anywhere in a colour prop's value names a colour, whether the
  // value is a literal, a conditional or a fallback.
  const colourProp = (value, prop) => {
    if (typeof prop !== "string" || !COLOUR_PROP.test(prop)) return;
    for (const [node, text] of strings(value)) {
      const word = text.trim();
      if (/^[a-z]+$/i.test(word) && !KEYWORDS.has(word.toLowerCase())) {
        found.push([node.loc.start.line, `${prop}="${word}"`]);
        reported.add(node);
      }
    }
  };
  walk(ast, (node) => {
    // A string literal, JSX attribute values included.
    if (node.type === "Literal" && typeof node.value === "string") {
      for (const match of node.value.matchAll(COLOUR_LITERAL)) {
        found.push([node.loc.start.line, match[0]]);
      }
    }
    // A template literal, read whole: fill in its literal parts, and treat
    // any other part after "#" as a hex value made at run time.
    if (node.type === "TemplateLiteral") {
      let text = "";
      node.quasis.forEach((quasi, i) => {
        text += quasi.value.cooked ?? "";
        const part = node.expressions[i];
        if (!part) return;
        if (part.type === "Literal") {
          text += String(part.value);
        } else {
          if (text.endsWith("#")) {
            found.push([node.loc.start.line, "#${…}"]);
          }
          text += " ";
        }
      });
      for (const match of text.matchAll(COLOUR_LITERAL)) {
        found.push([node.loc.start.line, `\`${match[0]}\``]);
      }
    }
    if (node.type === "JSXAttribute") colourProp(node.value, node.name.name);
    if (node.type === "Property" && !node.computed) {
      colourProp(node.value, node.key.name ?? node.key.value);
    }
  });
  // A CSS named colour anywhere, as a whole string.
  for (const [node, text] of strings(ast)) {
    const word = text.trim().toLowerCase();
    if (!reported.has(node) && NAMED_COLOURS.has(word)) {
      found.push([node.loc.start.line, `"${text.trim()}"`]);
    }
  }
  // Sort is stable, so finds on one line keep the order the scan made them.
  return found
    .sort(([a], [b]) => a - b)
    .map(([line, text]) => `${line}: ${text}`);
}

const importsRecharts = (source) =>
  /from\s+["']recharts["']/.test(source) ||
  /require\(\s*["']recharts["']\s*\)/.test(source);

const CHART_FILES = [...sourceFiles(SRC), ...sourceFiles(APP)].filter(
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
    'const g = <Bar fill={x ? "red" : "green"} />;',
    'const h = { fill: x || "Canvas" };',
    'const i = <Line stroke={`#${"227773"}`} />;',
    "const j = `#${hex}`;",
    'const k = { textFill: "red", labelColor: "blue" };',
    'const l = ["teal", "Navy"];',
    'const m = { label: "Teal gains, gray loses.", fill: TEXT.primary };',
    'const n = <Line stroke="oklch(60% 0.2 30)" />;',
    'const o = <Line stroke="var(--chart-1, red)" />;',
    'const p = { color: "color(display-p3 1 0 0)", fill: `lab(${l} 0 0)` };',
    'const q = { stroke: "var(--chart-1)", text: getColor(x), label: y };',
    'const r = <Line stroke="color-mix(in srgb, red, blue)" />;',
    'const s = <Line stroke="light-dark(red, blue)" />;',
    "const t = <Line stroke={color(dataKey)} fill={rgb(x)} />;",
    'const u = { note: "The Budget Lab (2026)", fill: SERIES[0] };',
    "const v = `#fff`;",
  ].join("\n");
  expect(colourLiterals(sample)).toEqual([
    "3: #227773",
    "4: rgba(",
    "5: hsl(",
    '6: stroke="white"',
    '7: fill="orange"',
    '9: fill="red"',
    '9: fill="green"',
    '10: fill="Canvas"',
    "11: `#227773`",
    "12: #${…}",
    '13: textFill="red"',
    '13: labelColor="blue"',
    '14: "teal"',
    '14: "Navy"',
    "16: oklch(",
    "17: var(--chart-1,",
    "18: color(",
    "18: `lab(`",
    "20: color-mix(",
    "21: light-dark(",
    "24: `#fff`",
  ]);
});

test("the scan covers every file that draws a chart", () => {
  const names = CHART_FILES.map((path) => relative(ROOT, path));
  expect(names).toContain("src/components/ShiftSweep.jsx");
  expect(names).toContain("src/components/AIScenarios.jsx");
  expect(names).toContain("src/components/IncomeDistributionBreakdown.jsx");
  expect(names).toContain("src/utils/chartStyles.js");
  expect(names).toContain("src/charts/kitTheme.js");
  // The app/ directory draws no chart today; the scan reads it all the same,
  // so a chart added there is checked.
  expect(sourceFiles(APP).length).toBeGreaterThan(0);
});

test.each(CHART_FILES.map((path) => [relative(ROOT, path), path]))(
  "%s holds no colour literal",
  (_name, path) => {
    expect(colourLiterals(readFileSync(path, "utf8"))).toEqual([]);
  },
);
