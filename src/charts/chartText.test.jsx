import { cloneElement } from "react";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import AIScenarios from "../components/AIScenarios";
import IncomeDistributionBreakdown from "../components/IncomeDistributionBreakdown";
import ShiftSweep from "../components/ShiftSweep";
import sweepData from "../data/shiftSweepData.json";
import { GRID_STYLE, TEXT } from "./kitTheme";
import { parseModule, sourceFiles, walk } from "./sourceTree";

// jsdom gives ResponsiveContainer no size, so Recharts draws no legend there.
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    ResponsiveContainer: ({ children, height }) =>
      cloneElement(children, {
        width: 800,
        height: typeof height === "number" ? height : 400,
      }),
  };
});

// Each legend entry's name, the colour it's written in and its swatch's
// accessible name.
function legendEntries() {
  return [...document.querySelectorAll(".recharts-legend-item")].map((item) => {
    const text = item.querySelector(".recharts-legend-item-text");
    return {
      name: text.textContent,
      colour: text.style.color,
      swatch: item.querySelector("svg").getAttribute("aria-label"),
    };
  });
}

function expectInkAndNames(entries) {
  expect(entries.length).toBeGreaterThan(0);
  for (const entry of entries) {
    expect(entry.colour).toBe(TEXT.muted);
    expect(entry.swatch).toBe(`${entry.name} legend icon`);
  }
}

describe("chart legends", () => {
  it("write the sweep's band names in ink, with plain swatch names", () => {
    render(
      <MemoryRouter>
        <ShiftSweep sweepData={sweepData} />
      </MemoryRouter>,
    );
    fireEvent.click(
      screen.getByRole("radio", { name: /net government revenue change/i }),
    );
    expectInkAndNames(legendEntries());
  });

  it("write the income components' names in ink, with plain swatch names", () => {
    render(<IncomeDistributionBreakdown />);
    expectInkAndNames(legendEntries());
  });

  it("write the AI scenarios' series names in ink, with plain swatch names", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expectInkAndNames(legendEntries());
  });
});

// Recharts writes each tooltip row in its series' colour unless the Tooltip
// sets itemStyle, so every Tooltip in the site's chart code takes the kit's.
describe("chart tooltips", () => {
  const ROOT = process.cwd();
  const DIRS = ["src/components", "src/charts", "src/views"];
  const files = DIRS.flatMap((dir) =>
    readdirSync(join(ROOT, dir))
      .filter((name) => /\.jsx$/.test(name) && !/\.test\./.test(name))
      .map((name) => join(dir, name)),
  );

  it("each set the kit's label and item styles", () => {
    const missing = files.flatMap((path) => {
      const code = readFileSync(join(ROOT, path), "utf8");
      const tooltips = [...code.matchAll(/<Tooltip\b[\s\S]*?\/>/g)].map(
        (match) => match[0],
      );
      return tooltips
        .filter(
          (tag) =>
            !tag.includes("{...TOOLTIP_PROPS}") &&
            !(tag.includes("itemStyle=") && tag.includes("labelStyle=")),
        )
        .map((tag) => `${path}: ${tag.slice(0, 60)}`);
    });
    expect(missing).toEqual([]);
  });
});

// Recharts draws axis lines, tick marks and tick text in #666 unless an axis
// sets them, so every axis takes the kit's settings, through AXIS_PROPS or
// one by one: tick text and axis titles in muted ink, axis lines in the
// grid's colour or none, and no tick marks.
const all = (selector) => [...document.querySelectorAll(selector)];
const KIT_PAINT = /^(none|var\(--[\w-]+\))$/;

// The colour an element paints: an inline style wins over the attribute, as
// it does in the browser. Recharts writes fill="#808080" on every axis title,
// and the kit's style covers it.
function paint(element, prop) {
  const style = element.getAttribute("style") ?? "";
  const match = style.match(new RegExp(`(?:^|;)\\s*${prop}:\\s*([^;]+)`));
  return match ? match[1].trim() : element.getAttribute(prop);
}

function expectKitAxes() {
  const lines = all(".recharts-cartesian-axis-line");
  const ticks = all(".recharts-cartesian-axis-tick-value");
  const titles = all(".recharts-label");
  expect(lines.length).toBeGreaterThan(0);
  expect(ticks.length).toBeGreaterThan(0);
  expect(titles.length).toBeGreaterThan(0);
  for (const line of lines)
    expect(paint(line, "stroke")).toBe(GRID_STYLE.stroke);
  expect(all(".recharts-cartesian-axis-tick-line")).toHaveLength(0);
  for (const tick of ticks) expect(paint(tick, "fill")).toBe(TEXT.muted);
  for (const title of titles) expect(paint(title, "fill")).toBe(TEXT.muted);
  // Nothing else in an axis paints a colour of its own.
  const painted = [
    ...all(".recharts-cartesian-axis, .recharts-cartesian-axis *"),
    ...ticks,
  ].flatMap((element) =>
    ["stroke", "fill"]
      .map((prop) => paint(element, prop))
      .filter((value) => value !== null && !KIT_PAINT.test(value)),
  );
  expect(painted).toEqual([]);
}

// The props each XAxis and YAxis in a module ends up with, read from the
// code: AXIS_PROPS sets the axis line, tick marks and tick text, and an
// attribute after it wins, as it does in React. An axis passes when its axis
// line takes GRID_STYLE.stroke or is off, as the kit's own charts draw
// some; its tick marks are off; its tick text takes AXIS_STYLE, alone or
// spread into an object that sets no colour; and any title takes
// AXIS_LABEL_STYLE. A spread the scan can't read could set any of these, so
// it fails, as does a child inside a paired tag (a <Label> draws its title in
// Recharts' #808080), a style, tickTextProps or colour-named prop on the axis,
// and a style key inside its tick or axis line, since an inline style beats
// the kit's paint. The kit's names count only when the module imports them
// from kitTheme and binds them nowhere else.
const AXIS_COMPONENTS = new Set(["XAxis", "YAxis"]);
const COLOUR_KEY = /(?:fill|stroke|colou?r|background)$/i;
const KIT_NAMES = [
  "AXIS_PROPS",
  "AXIS_STYLE",
  "AXIS_LABEL_STYLE",
  "GRID_STYLE",
];
const paints = (key) =>
  key === null ||
  key === "style" ||
  key === "tickTextProps" ||
  COLOUR_KEY.test(key);
const KIT = Symbol("AXIS_PROPS");
const UNREAD = Symbol("unread spread");

const isName = (node, name) =>
  node?.type === "Identifier" && node.name === name;
const isMember = (node, object, property) =>
  node?.type === "MemberExpression" &&
  !node.computed &&
  isName(node.object, object) &&
  isName(node.property, property);
const isFalse = (node) => node?.type === "Literal" && node.value === false;
const keyName = (property) =>
  property.computed ? null : (property.key.name ?? property.key.value);

export function axisProblems(source) {
  const ast = parseModule(source);
  const text = (node) => source.slice(...node.range);
  // The names the module's recharts import binds to XAxis and YAxis,
  // aliases included, and its namespace imports, such as Recharts.XAxis.
  const axisNames = new Map([...AXIS_COMPONENTS].map((name) => [name, name]));
  const namespaces = new Set();
  // Module-level constants, so tick={SMALL_TICK} reads SMALL_TICK's value.
  const constants = new Map();
  for (const statement of ast.body) {
    if (
      statement.type === "ImportDeclaration" &&
      statement.source.value === "recharts"
    ) {
      for (const specifier of statement.specifiers) {
        if (specifier.type === "ImportNamespaceSpecifier") {
          namespaces.add(specifier.local.name);
        }
        if (
          specifier.type === "ImportSpecifier" &&
          AXIS_COMPONENTS.has(specifier.imported.name)
        ) {
          axisNames.set(specifier.local.name, specifier.imported.name);
        }
      }
    }
    const declaration =
      statement.type === "ExportNamedDeclaration"
        ? statement.declaration
        : statement;
    if (
      declaration?.type === "VariableDeclaration" &&
      declaration.kind === "const"
    ) {
      for (const declarator of declaration.declarations) {
        if (declarator.id.type === "Identifier" && declarator.init) {
          constants.set(declarator.id.name, declarator.init);
        }
      }
    }
  }
  // Every name the module binds, to find a kit name bound twice.
  const bound = new Map();
  const bind = (pattern) => {
    if (!pattern) return;
    if (pattern.type === "Identifier") {
      bound.set(pattern.name, (bound.get(pattern.name) ?? 0) + 1);
    } else if (pattern.type === "ObjectPattern") {
      pattern.properties.forEach((property) =>
        bind(
          property.type === "RestElement" ? property.argument : property.value,
        ),
      );
    } else if (pattern.type === "ArrayPattern") {
      pattern.elements.forEach(bind);
    } else if (pattern.type === "RestElement") {
      bind(pattern.argument);
    } else if (pattern.type === "AssignmentPattern") {
      bind(pattern.left);
    }
  };
  walk(ast, (node) => {
    if (node.type === "VariableDeclarator") bind(node.id);
    if (/^(?:Function|ArrowFunction|Class)/.test(node.type)) {
      bind(node.id);
      node.params?.forEach(bind);
    }
    if (node.type === "CatchClause") bind(node.param);
    if (/^Import\w*Specifier$/.test(node.type)) bind(node.local);
  });
  const trusted = new Set();
  for (const statement of ast.body) {
    if (
      statement.type !== "ImportDeclaration" ||
      !/(?:^|\/)kitTheme(?:\.js)?$/.test(statement.source.value)
    ) {
      continue;
    }
    for (const specifier of statement.specifiers) {
      const local = specifier.local.name;
      if (
        specifier.type === "ImportSpecifier" &&
        specifier.imported.name === local &&
        KIT_NAMES.includes(local) &&
        bound.get(local) === 1
      ) {
        trusted.add(local);
      }
    }
  }
  const isKit = (node, name) => isName(node, name) && trusted.has(name);
  const isKitMember = (node, object, property) =>
    isMember(node, object, property) && trusted.has(object);
  // A module constant's value, unless a function binds its name again.
  const resolve = (node, seen = new Set()) => {
    if (
      node?.type !== "Identifier" ||
      !constants.has(node.name) ||
      bound.get(node.name) !== 1
    ) {
      return node;
    }
    if (seen.has(node.name)) return node;
    seen.add(node.name);
    return resolve(constants.get(node.name), seen);
  };
  const axisName = (name) => {
    if (name.type === "JSXIdentifier") return axisNames.get(name.name);
    if (
      name.type === "JSXMemberExpression" &&
      name.object.type === "JSXIdentifier" &&
      namespaces.has(name.object.name) &&
      AXIS_COMPONENTS.has(name.property.name)
    ) {
      return name.property.name;
    }
    return undefined;
  };

  // An object whose every spread is one of allowed and that sets no colour.
  const plainObject = (node, allowed) =>
    node?.type === "ObjectExpression" &&
    node.properties.every((property) =>
      property.type === "SpreadElement"
        ? allowed(resolve(property.argument))
        : !paints(keyName(property)),
    ) &&
    node.properties.some(
      (property) =>
        property.type === "SpreadElement" &&
        allowed(resolve(property.argument)),
    );
  const kitTick = (node) =>
    isKit(node, "AXIS_STYLE") ||
    isKitMember(node, "AXIS_PROPS", "tick") ||
    plainObject(node, kitTick);
  const kitTitleStyle = (node) =>
    isKit(node, "AXIS_LABEL_STYLE") || plainObject(node, kitTitleStyle);
  const CHECKS = {
    axisLine: [
      "an axis line in GRID_STYLE.stroke, or none",
      (node) =>
        isFalse(node) ||
        isKitMember(node, "AXIS_PROPS", "axisLine") ||
        (node?.type === "ObjectExpression" &&
          node.properties.every(
            (property) =>
              property.type === "Property" &&
              (keyName(property) === "stroke"
                ? isKitMember(resolve(property.value), "GRID_STYLE", "stroke")
                : !paints(keyName(property))),
          ) &&
          node.properties.some((property) => keyName(property) === "stroke")),
    ],
    tickLine: [
      "no tick marks",
      (node) => isFalse(node) || isKitMember(node, "AXIS_PROPS", "tickLine"),
    ],
    tick: ["tick text in AXIS_STYLE", kitTick],
    label: [
      "a title in AXIS_LABEL_STYLE",
      (node) =>
        isFalse(node) ||
        (node?.type === "ObjectExpression" &&
          node.properties.every((property) =>
            property.type === "SpreadElement"
              ? false
              : keyName(property) === "style"
                ? kitTitleStyle(resolve(property.value))
                : !COLOUR_KEY.test(keyName(property) ?? "fill"),
          ) &&
          node.properties.some((property) => keyName(property) === "style")),
    ],
  };

  const axes = [];
  walk(ast, (element) => {
    if (element.type !== "JSXElement") return;
    const node = element.openingElement;
    const name = axisName(node.name);
    if (!name) return;
    const line = node.loc.start.line;
    // Props that can paint the axis and that no kit setting covers.
    const painted = [];
    // Each checked prop's final value: KIT from AXIS_PROPS, UNREAD from a
    // spread the scan can't read, or the expression an attribute sets.
    const props = new Map();
    const spread = (argument) => {
      const value = resolve(argument);
      if (isKit(argument, "AXIS_PROPS")) {
        for (const key of ["axisLine", "tickLine", "tick"]) props.set(key, KIT);
      } else if (value?.type === "ObjectExpression") {
        for (const property of value.properties) {
          if (property.type === "SpreadElement") spread(property.argument);
          else if (keyName(property) in CHECKS) {
            props.set(keyName(property), resolve(property.value));
          } else if (keyName(property) === null) {
            for (const key of Object.keys(CHECKS)) props.set(key, UNREAD);
          } else if (paints(keyName(property))) {
            painted.push(keyName(property));
          }
        }
      } else {
        for (const key of Object.keys(CHECKS)) props.set(key, UNREAD);
      }
    };
    for (const attribute of node.attributes) {
      if (attribute.type === "JSXSpreadAttribute") {
        spread(attribute.argument);
        continue;
      }
      const key = attribute.name.name;
      if (!(key in CHECKS)) {
        if (paints(key)) painted.push(key);
        continue;
      }
      const { value } = attribute;
      props.set(
        key,
        value === null
          ? { type: "Literal", value: true, raw: "true" }
          : value.type === "JSXExpressionContainer"
            ? resolve(value.expression)
            : value,
      );
    }
    const problems = painted.map(
      (key) => `${line}: ${name} sets ${key}, which can paint the axis`,
    );
    for (const [key, [wanted, passes]] of Object.entries(CHECKS)) {
      const value = props.get(key);
      // An axis with no title draws none; every other prop has a default
      // that Recharts draws in #666.
      if (value === undefined && key === "label") continue;
      if (value === KIT) continue;
      if (value === undefined) {
        problems.push(`${line}: ${name} has no ${key}, so not ${wanted}`);
      } else if (value === UNREAD) {
        problems.push(
          `${line}: ${name} ${key} comes from a spread the scan can't read`,
        );
      } else if (!passes(value)) {
        problems.push(
          `${line}: ${name} ${key}=${value.range ? text(value) : value.raw}, not ${wanted}`,
        );
      }
    }
    // A child of a paired tag, such as a <Label>, draws what the scan can't read.
    const child = element.children.find(
      (item) =>
        !(item.type === "JSXText" && !item.value.trim()) &&
        item.expression?.type !== "JSXEmptyExpression",
    );
    if (child) {
      problems.push(`${line}: ${name} has a child the scan can't read`);
    }
    axes.push({ line, name, problems });
  });
  return axes;
}

describe("chart axes", () => {
  it("the axis scan reads each axis's final props", () => {
    const sample = [
      'import { AXIS_LABEL_STYLE, AXIS_PROPS, AXIS_STYLE, GRID_STYLE } from "./kitTheme";',
      'import { XAxis as X, YAxis } from "recharts";',
      'import * as Recharts from "recharts";',
      "const SMALL = { ...AXIS_STYLE, fontSize: 11 };",
      "const INKED = { ...AXIS_STYLE, fill: TEXT.primary };",
      "const a = <XAxis {...AXIS_PROPS} tick={SMALL} />;",
      "const b = <XAxis axisLine={true} tickLine={false} />;",
      "const c = <YAxis {...AXIS_PROPS} axisLine />;",
      "const d = <YAxis {...AXIS_PROPS} tickLine={true} />;",
      "const e = <X {...AXIS_PROPS} tick={{ fontSize: 11 }} />;",
      "const f = <X {...AXIS_PROPS} tick={INKED} />;",
      "const g = <X axisLine={true} {...AXIS_PROPS} />;",
      'const h = <YAxis {...AXIS_PROPS} label="Billions" />;',
      "const i = <YAxis {...AXIS_PROPS} label={{ value: 'B', style: { fontSize: 13 } }} />;",
      "const j = <YAxis {...AXIS_PROPS} label={{ value: 'B', style: AXIS_LABEL_STYLE }} />;",
      "const k = <YAxis {...AXIS_PROPS} {...rest} />;",
      "const l = <XAxis tick={AXIS_STYLE} tickLine={false}>{c}</XAxis>;",
      "const m = <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} />;",
      "const n = <Recharts.YAxis {...AXIS_PROPS} axisLine={{ stroke: TEXT.primary }} />;",
      "const o = <YAxis {...AXIS_PROPS} {...{ tickLine: true }} />;",
      "const p = <XAxis {...AXIS_PROPS} label={{ value: 'B', style: AXIS_LABEL_STYLE, fill: TEXT.primary }} />;",
      'const q = <XAxis {...AXIS_PROPS}><Label value="B" /></XAxis>;',
      "const r = <YAxis {...AXIS_PROPS} style={{ fill: TEXT.primary }} />;",
      "const s = <YAxis {...AXIS_PROPS} tickTextProps={{ fill: c }} stroke={c} />;",
      "const t = <XAxis {...AXIS_PROPS} tick={{ ...AXIS_STYLE, style: { fill: c } }} />;",
      "const u = <XAxis {...AXIS_PROPS} {...{ style: {} }} />;",
      "const v = <XAxis {...AXIS_PROPS} axisLine={{ stroke: GRID_STYLE.stroke, style: {} }}>{/* note */}</XAxis>;",
    ].join("\n");
    expect(axisProblems(sample)).toEqual([
      { line: 6, name: "XAxis", problems: [] },
      {
        line: 7,
        name: "XAxis",
        problems: [
          "7: XAxis axisLine=true, not an axis line in GRID_STYLE.stroke, or none",
          "7: XAxis has no tick, so not tick text in AXIS_STYLE",
        ],
      },
      {
        line: 8,
        name: "YAxis",
        problems: [
          "8: YAxis axisLine=true, not an axis line in GRID_STYLE.stroke, or none",
        ],
      },
      {
        line: 9,
        name: "YAxis",
        problems: ["9: YAxis tickLine=true, not no tick marks"],
      },
      {
        line: 10,
        name: "XAxis",
        problems: [
          "10: XAxis tick={ fontSize: 11 }, not tick text in AXIS_STYLE",
        ],
      },
      {
        line: 11,
        name: "XAxis",
        problems: [
          "11: XAxis tick={ ...AXIS_STYLE, fill: TEXT.primary }, not tick text in AXIS_STYLE",
        ],
      },
      { line: 12, name: "XAxis", problems: [] },
      {
        line: 13,
        name: "YAxis",
        problems: [
          '13: YAxis label="Billions", not a title in AXIS_LABEL_STYLE',
        ],
      },
      {
        line: 14,
        name: "YAxis",
        problems: [
          "14: YAxis label={ value: 'B', style: { fontSize: 13 } }, not a title in AXIS_LABEL_STYLE",
        ],
      },
      { line: 15, name: "YAxis", problems: [] },
      {
        line: 16,
        name: "YAxis",
        problems: [
          "16: YAxis axisLine comes from a spread the scan can't read",
          "16: YAxis tickLine comes from a spread the scan can't read",
          "16: YAxis tick comes from a spread the scan can't read",
          "16: YAxis label comes from a spread the scan can't read",
        ],
      },
      {
        line: 17,
        name: "XAxis",
        problems: [
          "17: XAxis has no axisLine, so not an axis line in GRID_STYLE.stroke, or none",
          "17: XAxis has a child the scan can't read",
        ],
      },
      { line: 18, name: "YAxis", problems: [] },
      {
        line: 19,
        name: "YAxis",
        problems: [
          "19: YAxis axisLine={ stroke: TEXT.primary }, not an axis line in GRID_STYLE.stroke, or none",
        ],
      },
      {
        line: 20,
        name: "YAxis",
        problems: ["20: YAxis tickLine=true, not no tick marks"],
      },
      {
        line: 21,
        name: "XAxis",
        problems: [
          "21: XAxis label={ value: 'B', style: AXIS_LABEL_STYLE, fill: TEXT.primary }, not a title in AXIS_LABEL_STYLE",
        ],
      },
      {
        line: 22,
        name: "XAxis",
        problems: ["22: XAxis has a child the scan can't read"],
      },
      {
        line: 23,
        name: "YAxis",
        problems: ["23: YAxis sets style, which can paint the axis"],
      },
      {
        line: 24,
        name: "YAxis",
        problems: [
          "24: YAxis sets tickTextProps, which can paint the axis",
          "24: YAxis sets stroke, which can paint the axis",
        ],
      },
      {
        line: 25,
        name: "XAxis",
        problems: [
          "25: XAxis tick={ ...AXIS_STYLE, style: { fill: c } }, not tick text in AXIS_STYLE",
        ],
      },
      {
        line: 26,
        name: "XAxis",
        problems: ["26: XAxis sets style, which can paint the axis"],
      },
      {
        line: 27,
        name: "XAxis",
        problems: [
          "27: XAxis axisLine={ stroke: GRID_STYLE.stroke, style: {} }, not an axis line in GRID_STYLE.stroke, or none",
        ],
      },
    ]);
  });

  it("the axis scan trusts the kit's names only from kitTheme", () => {
    // A local AXIS_PROPS and AXIS_STYLE read as the objects they are.
    const local = [
      "const AXIS_STYLE = { fill: c };",
      "const AXIS_PROPS = { tick: AXIS_STYLE, tickLine: false, axisLine: false };",
      "const a = <XAxis {...AXIS_PROPS} />;",
    ].join("\n");
    expect(axisProblems(local)).toEqual([
      {
        line: 3,
        name: "XAxis",
        problems: ["3: XAxis tick={ fill: c }, not tick text in AXIS_STYLE"],
      },
    ]);
    // An import from elsewhere, or a parameter that shadows the import,
    // isn't the kit's, and a constant a function binds again isn't read.
    const shadowed = [
      'import { AXIS_PROPS } from "./theme";',
      'import { AXIS_STYLE, GRID_STYLE } from "./kitTheme";',
      "const b = <XAxis {...AXIS_PROPS} />;",
      "function Chart({ AXIS_STYLE }) {",
      "  return <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={{ stroke: GRID_STYLE.stroke }} />;",
      "}",
      "const SMALL = { ...AXIS_STYLE };",
      "function Other() {",
      "  const SMALL = { fill: c };",
      "  return <YAxis tick={SMALL} tickLine={false} axisLine={false} />;",
      "}",
    ].join("\n");
    expect(axisProblems(shadowed)).toEqual([
      {
        line: 3,
        name: "XAxis",
        problems: [
          "3: XAxis axisLine comes from a spread the scan can't read",
          "3: XAxis tickLine comes from a spread the scan can't read",
          "3: XAxis tick comes from a spread the scan can't read",
          "3: XAxis label comes from a spread the scan can't read",
        ],
      },
      {
        line: 5,
        name: "YAxis",
        problems: ["5: YAxis tick=AXIS_STYLE, not tick text in AXIS_STYLE"],
      },
      {
        line: 10,
        name: "YAxis",
        problems: ["10: YAxis tick=SMALL, not tick text in AXIS_STYLE"],
      },
    ]);
  });

  it("draw the sweep's axes in the kit's colours", () => {
    render(
      <MemoryRouter>
        <ShiftSweep sweepData={sweepData} />
      </MemoryRouter>,
    );
    fireEvent.click(
      screen.getByRole("radio", { name: /net government revenue change/i }),
    );
    expectKitAxes();
  });

  it("draw the income components' axes in the kit's colours", () => {
    render(<IncomeDistributionBreakdown />);
    expectKitAxes();
  });

  it("draw the AI scenarios' axes in the kit's colours", () => {
    render(
      <MemoryRouter>
        <AIScenarios />
      </MemoryRouter>,
    );
    expectKitAxes();
  });

  // The renders above reach some of each file's charts; this reaches every
  // axis in the site's chart code.
  it("each take the kit's axis props", () => {
    const ROOT = process.cwd();
    const files = ["src", "app"].flatMap((dir) => sourceFiles(join(ROOT, dir)));
    const found = files.flatMap((path) =>
      axisProblems(readFileSync(path, "utf8")).map((axis) => ({
        ...axis,
        file: relative(ROOT, path),
      })),
    );
    // Every file that draws an axis today, so a scan that finds none fails.
    expect(new Set(found.map(({ file }) => file))).toEqual(
      new Set([
        "src/charts/LinePanel.jsx",
        "src/components/AIScenarios.jsx",
        "src/components/IncomeDistributionBreakdown.jsx",
        "src/components/ShiftSweep.jsx",
      ]),
    );
    expect(found.length).toBeGreaterThanOrEqual(20);
    expect(
      found.flatMap(({ file, problems }) =>
        problems.map((problem) => `${file}:${problem}`),
      ),
    ).toEqual([]);
  });
});
