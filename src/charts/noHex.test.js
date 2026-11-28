import { readFileSync } from "node:fs";
import { join, relative } from "node:path";

import { parseModule, sourceFiles, walk } from "./sourceTree";

// Chart code draws every colour from kitTheme.js, so it holds no colour
// literal of its own: no hex and no CSS colour function such as rgb(),
// oklch() or color-mix() in any string, including one a template literal
// builds; no var() with a fallback, which could name a colour of its own; no
// CSS named colour such as "white" as a whole string; and no bare word in a
// colour prop, however its value is written. The scan reads strings, not
// code, so a function call such as color(dataKey) passes and comments don't
// count; kitTheme.js names each token's hex value in one.
//
// A <style> element's CSS is read as one text, its children joined as React
// joins them: JSX text loses the whitespace lines around its line breaks, so
// a colour split across children is still seen. Its declarations may hold
// none of the above, no CSS named or system colour and no CSS escape. A child
// other than JSX text, a string or a template with no ${} is code the scan
// can't read, and fails, as does a spread, children or dangerouslySetInnerHTML
// prop on the element. The scan finds <style> by its tag name: CSS that
// reaches a <style> element through a tag held in a variable, a member tag or
// createElement() goes unread (#64). No chart file draws a <style> element.

const ROOT = process.cwd();
const SRC = join(ROOT, "src");
const APP = join(ROOT, "app");

// CSS allows no space between a function's name and its parenthesis, so
// prose such as "The Budget Lab (2026)" names no colour.
const COLOUR_LITERAL =
  /#[0-9a-f]{3,8}\b|\b(?:color-mix|light-dark|rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(|var\(\s*--[^\s,()]*\s*,/gi;
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

// The CSS system colours (CSS Color 4), which paint from the user's theme,
// with the deprecated ones browsers still paint, such as ButtonHighlight.
const SYSTEM_COLOURS = new Set(
  `accentcolor accentcolortext activetext buttonborder buttonface buttontext
  canvas canvastext field fieldtext graytext highlight highlighttext linktext
  mark marktext selecteditem selecteditemtext visitedtext activeborder
  activecaption appworkspace background buttonhighlight buttonshadow
  captiontext inactiveborder inactivecaption inactivecaptiontext
  infobackground infotext menu menutext scrollbar threeddarkshadow threedface
  threedhighlight threedlightshadow threedshadow window windowframe
  windowtext`.split(/\s+/),
);
// Properties that take no colour, whose words are names: a font such as
// Arial Black, a property such as background in a transition, or a grid area.
// A property missing here only fails a correct stylesheet, never passes a
// colour.
const NAME_ONLY = new Set(
  `font font-family transition transition-property will-change animation
  animation-name grid-area grid-template-areas grid-row grid-row-start
  grid-row-end grid-column grid-column-start grid-column-end counter-reset
  counter-increment counter-set quotes list-style-type container
  container-name view-transition-name anchor-name position-anchor`.split(/\s+/),
);

// The text React renders for a JSX text child, one [text, line] per source
// line it keeps: tabs read as spaces, a line break drops the spaces around
// it, a line left empty drops out, and kept lines join with one space (as
// Babel's and SWC's JSX transforms clean a child).
function jsxTextLines(value, firstLine) {
  const lines = value.split(/\r\n|\n|\r/);
  let lastNonEmpty = 0;
  lines.forEach((line, i) => {
    if (/[^ \t]/.test(line)) lastNonEmpty = i;
  });
  const kept = [];
  lines.forEach((line, i) => {
    let text = line.replace(/\t/g, " ");
    if (i > 0) text = text.replace(/^ +/, "");
    if (i < lines.length - 1) text = text.replace(/ +$/, "");
    if (!text) return;
    kept.push([i === lastNonEmpty ? text : `${text} `, firstLine + i]);
  });
  return kept;
}

// Each colour in a stylesheet's declarations, as [offset, text]. Comments,
// quoted strings and unquoted url() are blanked in one pass that takes the
// leftmost first, as CSS reads them, so a quoted "/*" or one inside url(/a/*)
// opens no comment. CSS reads \r, \r\n and \f as a line break, and a string
// ends at a line break, as CSS ends a bad string; a url() ends at its first
// ")", never later than CSS ends it, and a function such as --furl() is no
// url(). Text before a "{" is a selector or an at-rule's
// prelude, which paints nothing; every other run between "{", "}" and ";" is
// a declaration, at any depth of nesting and in a block left open at the end.
function styleColours(css) {
  const blank = (match) => match.replace(/[^\n]/g, " ");
  // Line breaks as CSS reads them, keeping each offset in place.
  const text = css
    .replace(/\r\n/g, " \n")
    .replace(/[\r\f]/g, "\n")
    .replace(
      /\/\*[\s\S]*?(?:\*\/|$)|"(?:[^"\\\n]|\\[\s\S])*(?:"|(?=\n)|$)|'(?:[^'\\\n]|\\[\s\S])*(?:'|(?=\n)|$)|(?<![\w-])url\(\s*[^\s"'()][^)]*\)?/gi,
      blank,
    );
  const found = [];
  for (const escape of text.matchAll(/\\/g)) {
    found.push([escape.index, "\\ escape"]);
  }
  for (const run of text.matchAll(/[^{};]+(?=[{};]|$)/g)) {
    if (text[run.index + run[0].length] === "{") continue;
    const colon = run[0].indexOf(":");
    if (colon < 0) continue;
    const property = run[0].slice(0, colon).trim().toLowerCase();
    const value = run[0].slice(colon + 1);
    const valueStart = run.index + colon + 1;
    for (const match of value.matchAll(COLOUR_LITERAL)) {
      found.push([valueStart + match.index, match[0]]);
    }
    if (NAME_ONLY.has(property)) continue;
    // Whole identifiers, so var(--color-gray-400) names no gray.
    for (const word of value.matchAll(/(?:--|-?[a-z_])[\w-]*/gi)) {
      const name = word[0].toLowerCase();
      if (NAMED_COLOURS.has(name) || SYSTEM_COLOURS.has(name)) {
        found.push([valueStart + word.index, `${property}: ${word[0]}`]);
      }
    }
  }
  return found;
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
  // Strings a <style> element's CSS holds: the stylesheet scan reads them, so
  // a hex-like selector, comment or url() in one names no colour.
  const stylesheet = new Set();
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
    if (
      node.type === "Literal" &&
      typeof node.value === "string" &&
      !stylesheet.has(node)
    ) {
      for (const match of node.value.matchAll(COLOUR_LITERAL)) {
        found.push([node.loc.start.line, match[0]]);
      }
    }
    // A template literal, read whole: fill in its literal parts, and treat
    // any other part after "#" as a hex value made at run time.
    if (node.type === "TemplateLiteral" && !stylesheet.has(node)) {
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
    // The CSS a <style> element holds, its children joined. JSX text reaches
    // no string scan; espree decodes its entities, so &#123; reads as "{".
    if (
      node.type === "JSXElement" &&
      node.openingElement.name.type === "JSXIdentifier" &&
      node.openingElement.name.name === "style"
    ) {
      // Props that hand the element CSS the scan doesn't read.
      for (const attribute of node.openingElement.attributes) {
        const name = attribute.name?.name;
        if (attribute.type === "JSXSpreadAttribute") {
          found.push([
            attribute.loc.start.line,
            "<style> takes a spread the scan can't read",
          ]);
        } else if (name === "children" || name === "dangerouslySetInnerHTML") {
          found.push([
            attribute.loc.start.line,
            `<style> sets ${name}, which the scan can't read`,
          ]);
        }
      }
      let css = "";
      // Where each piece of text starts in css, on which line, and whether
      // its line breaks are source lines, as a template's are and a string's
      // escaped ones aren't.
      const starts = [];
      const add = (text, line, breaks = false) => {
        starts.push([css.length, line, breaks]);
        css += text;
      };
      for (const child of node.children) {
        const expression =
          child.type === "JSXExpressionContainer" ? child.expression : null;
        if (child.type === "JSXText") {
          for (const [text, line] of jsxTextLines(
            child.value,
            child.loc.start.line,
          )) {
            add(text, line);
          }
        } else if (expression?.type === "JSXEmptyExpression") {
          continue;
        } else if (
          expression?.type === "Literal" &&
          typeof expression.value === "string"
        ) {
          stylesheet.add(expression);
          add(expression.value, child.loc.start.line);
        } else if (
          expression?.type === "TemplateLiteral" &&
          expression.expressions.length === 0
        ) {
          stylesheet.add(expression);
          stylesheet.add(expression.quasis[0]);
          add(
            expression.quasis[0].value.cooked ?? "",
            child.loc.start.line,
            true,
          );
        } else {
          found.push([
            child.loc.start.line,
            "<style> child the scan can't read",
          ]);
        }
      }
      const lineAt = (offset) => {
        const [start, line, breaks] = starts.findLast(([at]) => at <= offset);
        if (!breaks) return line;
        return line + (css.slice(start, offset).match(/\n/g) ?? []).length;
      };
      for (const [offset, text] of styleColours(css)) {
        found.push([lineAt(offset), `<style> ${text}`]);
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
    if (
      !reported.has(node) &&
      !stylesheet.has(node) &&
      NAMED_COLOURS.has(word)
    ) {
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
    "const w = <style>.series &#123; stroke: #227773; &#125;</style>;",
    "const x = <style>{\".a { fill: red; font-family: 'Tan' }\"}</style>;",
    "const y = <style>{`.b:hover { stroke: ${c}; color: Navy }`}</style>;",
    "const z = <style>.c &#123; fill: var(--chart-1); &#125; /* red */</style>;",
    'const aa = <style>.a &#123; color: #{"227773"} &#125;</style>;',
    'const ab = <style>{".a { color: "}{"red }"}</style>;',
    "const ac = <style><>.a &#123; fill: teal &#125;</></style>;",
    'const ad = <style>{`.a { color: r${""}ed }`}</style>;',
    'const ae = <style>{".a { opacity: 1; &:hover { color: red } }"}</style>;',
    "const af = <style>{\".a { content: '/*'; color: red } /* */\"}</style>;",
    'const ag = <style>{".a { fill: Canvas; stroke: var(--color-gray-400)"}</style>;',
    "const ah = <style>/* was #fff */ #add &#123; fill: url(#red); &#125;</style>;",
    'const ai = <style>{".a { color: \\\\72 ed }"}</style>;',
    "const aj = (",
    "  <style>",
    "    .a &#123;",
    "      color: navy;",
    "    &#125;",
    "  </style>",
    ");",
    'const ak = <style children={".a { color: red }"} />;',
    "const al = <style dangerouslySetInnerHTML={{ __html: css }} />;",
    "const am = <style {...props}>.a &#123; opacity: 1 &#125;</style>;",
    "const an = (",
    "  <style>",
    "    .a &#123; color: re",
    '    {"d }"}',
    "  </style>",
    ");",
    'const ao = <style>{".a { background: url(/a/*) } .b { color: red }"}</style>;',
    'const ap = <style>{".a { content: \\"/*\\n} .b { color: red } /* */"}</style>;',
    'const aq = <style>{".a { font-family: Arial Black; transition: background 1s }"}</style>;',
    'const ar = <style>{".a { color: var(--α, currentcolor) }"}</style>;',
    'const as = <style>{".a { outline-color: ButtonHighlight }"}</style>;',
    'const at = <style>{"/* #fff */ #add { opacity: 1; mask: url(#f00) }"}</style>;',
    'const au = <style>{`.a { opacity: 1 }`}{".b { color: #f00 }"}</style>;',
    'const av = <style>{".a { content: \\"x\\r} .b { color: red }"}</style>;',
    'const aw = <style>{".a { content: red; background: --furl(red) }"}</style>;',
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
    "25: <style> #227773",
    "26: <style> fill: red",
    "27: <style> child the scan can't read",
    "29: <style> #227773",
    "30: <style> color: red",
    "31: <style> child the scan can't read",
    "32: <style> child the scan can't read",
    "33: <style> color: red",
    "34: <style> color: red",
    "35: <style> fill: Canvas",
    "37: <style> \\ escape",
    "41: <style> color: navy",
    "45: <style> sets children, which the scan can't read",
    "46: <style> sets dangerouslySetInnerHTML, which the scan can't read",
    "47: <style> takes a spread the scan can't read",
    "50: <style> color: red",
    "54: <style> color: red",
    "55: <style> color: red",
    "57: <style> var(--α,",
    "58: <style> outline-color: ButtonHighlight",
    "60: <style> #f00",
    "61: <style> color: red",
    "62: <style> content: red",
    "62: <style> background: red",
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
