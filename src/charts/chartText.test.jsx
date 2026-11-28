import { cloneElement } from "react";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative, resolve as resolvePath } from "node:path";
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
// spread into an object that adds only text layout; and any title takes
// AXIS_LABEL_STYLE. The scan fails what it can't read: a spread it can't
// read, wherever it sits, since it could set any prop; a child, or a
// children, className, style, tickTextProps or colour-named prop, since each
// can paint the axis (a <Label> draws its title in Recharts' #808080); and a
// key outside the short list each tick, axis line and title object may set.
//
// The kit's names count only when the module imports them from
// src/charts/kitTheme and binds them nowhere else, and a module constant is
// read only when nothing else binds its name. Either counts only while every
// use of it sits where the scan can follow it: a JSX prop's value, a spread
// or property value in an object that sits there too, a module constant's
// value, a condition, or text. A kit name used anywhere else, such as in a
// call, a delete or an alias, fails its module, since code the scan can't
// read could change the kit's objects. So does any use of XAxis, YAxis or the
// recharts namespace outside a JSX tag, and any load of recharts other than
// an import, since the scan finds axes by their tags.
const AXIS_COMPONENTS = new Set(["XAxis", "YAxis"]);
const COLOUR_KEY = /(?:fill|stroke|colou?r|background)$/i;
const KIT_NAMES = new Set([
  "AXIS_PROPS",
  "AXIS_STYLE",
  "AXIS_LABEL_STYLE",
  "GRID_STYLE",
]);
const KIT_MODULE = join(process.cwd(), "src", "charts", "kitTheme");
// Where a sample with no file of its own reads from: beside kitTheme.js.
const SAMPLE_FILE = join(process.cwd(), "src", "charts", "sample.jsx");
// A prop on an axis that can paint it and that no kit setting covers.
const paints = (key) =>
  key === null ||
  ["children", "className", "style", "tickTextProps"].includes(key) ||
  COLOUR_KEY.test(key);
// The keys each object may set besides its kit spread: text layout for tick
// text and a title's style, a title's placement, and an axis line's width
// and dashes.
const TICK_KEYS = new Set([
  "fontSize",
  "fontWeight",
  "fontFamily",
  "fontStyle",
  "letterSpacing",
  "dx",
  "dy",
  "angle",
  "textAnchor",
  "verticalAnchor",
  "width",
]);
const TITLE_STYLE_KEYS = new Set([
  "fontSize",
  "fontWeight",
  "fontFamily",
  "fontStyle",
  "letterSpacing",
]);
const LABEL_KEYS = new Set([
  "value",
  "position",
  "offset",
  "angle",
  "dx",
  "dy",
  "style",
]);
const AXIS_LINE_KEYS = new Set(["stroke", "strokeWidth", "strokeDasharray"]);
const KIT = Symbol("AXIS_PROPS");

const isName = (node, name) =>
  node?.type === "Identifier" && node.name === name;
const isMember = (node, object, property) =>
  node?.type === "MemberExpression" &&
  !node.computed &&
  isName(node.object, object) &&
  isName(node.property, property);
const isFalse = (node) => node?.type === "Literal" && node.value === false;
const isNoTitle = (node) =>
  isFalse(node) ||
  (node?.type === "Literal" && node.value === null) ||
  isName(node, "undefined");
const keyName = (property) =>
  property.computed ? null : (property.key.name ?? property.key.value);
// A plain key: value pair, not a getter, method or computed key.
const plainProperty = (property, keys) =>
  property.type === "Property" &&
  property.kind === "init" &&
  !property.method &&
  keys.has(keyName(property));
// An import's name, string names such as { "XAxis" as Axis } included.
const importedName = (specifier) =>
  specifier.imported?.name ?? specifier.imported?.value;

export function axisProblems(source, file = SAMPLE_FILE) {
  const ast = parseModule(source);
  const text = (node) => source.slice(...node.range);
  // Problems that belong to the module, not one axis.
  const moduleProblems = [];
  const flag = (node, name, problem) => {
    const { line } = node.loc.start;
    moduleProblems.push({ line, name, problems: [`${line}: ${problem}`] });
  };
  const parents = new Map();
  const link = (node, parent) => {
    if (!node || typeof node.type !== "string") return;
    parents.set(node, parent);
    for (const [key, value] of Object.entries(node)) {
      if (key === "loc" || key === "range") continue;
      if (Array.isArray(value)) value.forEach((child) => link(child, node));
      else if (value && typeof value === "object") link(value, node);
    }
  };
  link(ast, null);

  // The names the module's recharts import binds to XAxis and YAxis,
  // aliases included, and its namespace and default imports, such as
  // Recharts.XAxis.
  const axisNames = new Map([...AXIS_COMPONENTS].map((name) => [name, name]));
  const axisLocals = new Set();
  const namespaces = new Set();
  // The kit's names, imported from kitTheme under their own names.
  const kitImports = new Set();
  const fromKit = (path) =>
    /^\.\.?\//.test(path) &&
    resolvePath(dirname(file), path).replace(/\.js$/, "") === KIT_MODULE;
  // Module-level constants, so tick={SMALL_TICK} reads SMALL_TICK's value.
  const constants = new Map();
  for (const statement of ast.body) {
    if (statement.type === "ImportDeclaration") {
      for (const specifier of statement.specifiers) {
        const local = specifier.local.name;
        if (statement.source.value === "recharts") {
          if (specifier.type !== "ImportSpecifier") namespaces.add(local);
          else if (AXIS_COMPONENTS.has(importedName(specifier))) {
            axisNames.set(local, importedName(specifier));
            axisLocals.add(local);
          }
        }
        if (
          fromKit(statement.source.value) &&
          specifier.type === "ImportSpecifier" &&
          importedName(specifier) === local &&
          KIT_NAMES.has(local)
        ) {
          kitImports.add(local);
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
  // Every name the module binds, to find one bound twice.
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

  // Each place an identifier reads a name, not where it declares one or
  // names a property.
  const isReference = (node) => {
    const parent = parents.get(node);
    switch (parent?.type) {
      case "VariableDeclarator":
        return parent.id !== node;
      case "MemberExpression":
        return parent.object === node || parent.computed;
      case "Property":
      case "PropertyDefinition":
      case "MethodDefinition":
        return (
          parent.value === node || (parent.computed && parent.key === node)
        );
      case "ImportSpecifier":
      case "ImportDefaultSpecifier":
      case "ImportNamespaceSpecifier":
      case "LabeledStatement":
      case "BreakStatement":
      case "ContinueStatement":
        return false;
      case "ExportSpecifier":
        return parent.local === node;
      case "FunctionDeclaration":
      case "FunctionExpression":
      case "ArrowFunctionExpression":
        return parent.id !== node && !parent.params.includes(node);
      case "ClassDeclaration":
      case "ClassExpression":
        return parent.id !== node;
      case "CatchClause":
        return parent.param !== node;
      default:
        return Boolean(parent);
    }
  };
  const references = [];
  walk(ast, (node) => {
    if (node.type === "Identifier" && isReference(node)) references.push(node);
  });

  // The kit's names and module constants the scan can follow: bound once,
  // and every use where its value stays readable.
  const tracked = new Set(
    [...kitImports, ...constants.keys()].filter(
      (name) => bound.get(name) === 1,
    ),
  );
  const followed = (expression) => {
    const parent = parents.get(expression);
    const grandparent = parents.get(parent);
    switch (parent?.type) {
      case "JSXExpressionContainer":
        return grandparent?.type === "JSXAttribute";
      case "JSXSpreadAttribute":
        return true;
      case "SpreadElement":
      case "Property":
        return (
          (parent.type === "SpreadElement" || parent.value === expression) &&
          grandparent?.type === "ObjectExpression" &&
          followed(grandparent)
        );
      case "ConditionalExpression":
        return parent.test === expression || followed(parent);
      case "LogicalExpression":
        return followed(parent);
      case "TemplateLiteral":
      case "BinaryExpression":
        return true;
      case "VariableDeclarator":
        return (
          parent.init === expression &&
          parent.id.type === "Identifier" &&
          constants.has(parent.id.name) &&
          tracked.has(parent.id.name)
        );
      default:
        return false;
    }
  };
  const escapes = new Map();
  for (let changed = true; changed; ) {
    changed = false;
    for (const node of references) {
      if (!tracked.has(node.name)) continue;
      let top = node;
      while (
        parents.get(top)?.type === "MemberExpression" &&
        parents.get(top).object === top
      ) {
        top = parents.get(top);
      }
      if (!followed(top)) {
        tracked.delete(node.name);
        escapes.set(node.name, node);
        changed = true;
      }
    }
  }
  for (const [name, node] of escapes) {
    if (kitImports.has(name)) {
      flag(node, name, `${name} goes where the scan can't follow it`);
    }
  }
  // Axes the scan would miss: an axis component or the recharts namespace
  // used outside a JSX tag, and recharts loaded other than by an import.
  for (const node of references) {
    const parent = parents.get(node);
    const memberOfNamespace =
      namespaces.has(node.name) &&
      parent?.type === "MemberExpression" &&
      parent.object === node &&
      !parent.computed &&
      !AXIS_COMPONENTS.has(parent.property.name);
    if (
      axisLocals.has(node.name) ||
      (namespaces.has(node.name) && !memberOfNamespace)
    ) {
      flag(
        node,
        node.name,
        `${node.name} is used where the scan can't follow it`,
      );
    }
  }
  walk(ast, (node) => {
    if (
      (node.type === "CallExpression" &&
        isName(node.callee, "require") &&
        node.arguments[0]?.value === "recharts") ||
      (node.type === "ImportExpression" && node.source?.value === "recharts") ||
      (/^Export(?:Named|All)Declaration$/.test(node.type) &&
        node.source?.value === "recharts")
    ) {
      flag(node, "recharts", "loads recharts where the scan can't follow it");
    }
  });

  const trusted = new Set([...kitImports].filter((name) => tracked.has(name)));
  const isKit = (node, name) => isName(node, name) && trusted.has(name);
  const isKitMember = (node, object, property) =>
    isMember(node, object, property) && trusted.has(object);
  // A module constant's value, when the scan can follow it.
  const resolve = (node, seen = new Set()) => {
    if (
      node?.type !== "Identifier" ||
      !constants.has(node.name) ||
      !tracked.has(node.name)
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

  // An object that spreads one of allowed and otherwise sets only keys.
  const plainObject = (node, allowed, keys) =>
    node?.type === "ObjectExpression" &&
    node.properties.every((property) =>
      property.type === "SpreadElement"
        ? allowed(resolve(property.argument))
        : plainProperty(property, keys),
    ) &&
    node.properties.some(
      (property) =>
        property.type === "SpreadElement" &&
        allowed(resolve(property.argument)),
    );
  const kitTick = (node) =>
    isKit(node, "AXIS_STYLE") ||
    isKitMember(node, "AXIS_PROPS", "tick") ||
    plainObject(node, kitTick, TICK_KEYS);
  const kitTitleStyle = (node) =>
    isKit(node, "AXIS_LABEL_STYLE") ||
    plainObject(node, kitTitleStyle, TITLE_STYLE_KEYS);
  const CHECKS = {
    axisLine: [
      "an axis line in GRID_STYLE.stroke, or none",
      (node) =>
        isFalse(node) ||
        isKitMember(node, "AXIS_PROPS", "axisLine") ||
        (node?.type === "ObjectExpression" &&
          node.properties.every(
            (property) =>
              plainProperty(property, AXIS_LINE_KEYS) &&
              (keyName(property) !== "stroke" ||
                isKitMember(resolve(property.value), "GRID_STYLE", "stroke")),
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
        isNoTitle(node) ||
        (node?.type === "ObjectExpression" &&
          node.properties.every(
            (property) =>
              plainProperty(property, LABEL_KEYS) &&
              (keyName(property) === "style"
                ? kitTitleStyle(resolve(property.value))
                : keyName(property) !== "value" ||
                  !/^JSX/.test(property.value.type)),
          ) &&
          node.properties.some((property) => keyName(property) === "style")),
    ],
  };
  const checked = (key) => Object.hasOwn(CHECKS, key);

  const axes = [];
  walk(ast, (element) => {
    if (element.type !== "JSXElement") return;
    const node = element.openingElement;
    const name = axisName(node.name);
    if (!name) return;
    const line = node.loc.start.line;
    // Props that can paint the axis and that no kit setting covers.
    const painted = [];
    // Each checked prop's final value: KIT from AXIS_PROPS, or the
    // expression an attribute sets.
    const props = new Map();
    // A spread the scan can't read could set any prop, before or after.
    let unread = false;
    const spread = (argument) => {
      const value = resolve(argument);
      if (isKit(value, "AXIS_PROPS")) {
        for (const key of ["axisLine", "tickLine", "tick"]) props.set(key, KIT);
      } else if (value?.type === "ObjectExpression") {
        for (const property of value.properties) {
          const key = property.type === "Property" ? keyName(property) : null;
          if (property.type === "SpreadElement") spread(property.argument);
          else if (key === null || property.kind !== "init") unread = true;
          else if (checked(key)) props.set(key, resolve(property.value));
          else if (paints(key)) painted.push(key);
        }
      } else {
        unread = true;
      }
    };
    for (const attribute of node.attributes) {
      if (attribute.type === "JSXSpreadAttribute") {
        spread(attribute.argument);
        continue;
      }
      if (attribute.name.type === "JSXNamespacedName") {
        painted.push(text(attribute.name));
        continue;
      }
      const key = attribute.name.name;
      if (!checked(key)) {
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
    if (unread) {
      problems.push(`${line}: ${name} takes a spread the scan can't read`);
    } else {
      for (const [key, [wanted, passes]] of Object.entries(CHECKS)) {
        const value = props.get(key);
        // An axis with no title draws none; every other prop has a default
        // that Recharts draws in #666.
        if (value === undefined && key === "label") continue;
        if (value === KIT) continue;
        if (value === undefined) {
          problems.push(`${line}: ${name} has no ${key}, so not ${wanted}`);
        } else if (!passes(value)) {
          problems.push(
            `${line}: ${name} ${key}=${value.range ? text(value) : value.raw}, not ${wanted}`,
          );
        }
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
  // Sort is stable, so an axis keeps its place before its module's problems.
  return [...axes, ...moduleProblems].sort((a, b) => a.line - b.line);
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
      "const w = <XAxis {...rest} {...AXIS_PROPS} label={false} />;",
      'const x = <XAxis {...AXIS_PROPS} children={<Label value="B" />} />;',
      "const y = <YAxis {...AXIS_PROPS} label={{ value: 'B', style: AXIS_LABEL_STYLE, content: () => null }} />;",
      "const z = <YAxis {...AXIS_PROPS} label={null} />;",
      'const aa = <XAxis {...AXIS_PROPS} className="axis" />;',
      "const ab = <XAxis {...AXIS_PROPS} tick={{ ...AXIS_STYLE, className: 't' }} />;",
      "const ac = <XAxis {...AXIS_PROPS} label={{ value: <tspan>B</tspan>, style: AXIS_LABEL_STYLE }} />;",
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
        problems: ["16: YAxis takes a spread the scan can't read"],
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
      {
        line: 28,
        name: "XAxis",
        problems: ["28: XAxis takes a spread the scan can't read"],
      },
      {
        line: 29,
        name: "XAxis",
        problems: ["29: XAxis sets children, which can paint the axis"],
      },
      {
        line: 30,
        name: "YAxis",
        problems: [
          "30: YAxis label={ value: 'B', style: AXIS_LABEL_STYLE, content: () => null }, not a title in AXIS_LABEL_STYLE",
        ],
      },
      { line: 31, name: "YAxis", problems: [] },
      {
        line: 32,
        name: "XAxis",
        problems: ["32: XAxis sets className, which can paint the axis"],
      },
      {
        line: 33,
        name: "XAxis",
        problems: [
          "33: XAxis tick={ ...AXIS_STYLE, className: 't' }, not tick text in AXIS_STYLE",
        ],
      },
      {
        line: 34,
        name: "XAxis",
        problems: [
          "34: XAxis label={ value: <tspan>B</tspan>, style: AXIS_LABEL_STYLE }, not a title in AXIS_LABEL_STYLE",
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
        problems: ["3: XAxis takes a spread the scan can't read"],
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

  it("the axis scan follows the kit's names and the axes wherever they go", () => {
    const followed = [
      'import { AXIS_PROPS, AXIS_STYLE, AXIS_LABEL_STYLE } from "./kitTheme";',
      'import { "XAxis" as Axis, YAxis } from "recharts";',
      'import * as Recharts from "recharts";',
      "const tick = { ...AXIS_STYLE };",
      "delete tick.fill;",
      "const a = <Axis {...AXIS_PROPS} tick={tick} />;",
      "delete AXIS_STYLE.fill;",
      "const b = YAxis;",
      "const c = createElement(Recharts.XAxis);",
      "use({ style: AXIS_LABEL_STYLE });",
      'export { XAxis } from "recharts";',
      "const d = <Axis tickLine />;",
    ].join("\n");
    expect(axisProblems(followed)).toEqual([
      {
        line: 6,
        name: "XAxis",
        problems: ["6: XAxis tick=tick, not tick text in AXIS_STYLE"],
      },
      {
        line: 7,
        name: "AXIS_STYLE",
        problems: ["7: AXIS_STYLE goes where the scan can't follow it"],
      },
      {
        line: 8,
        name: "YAxis",
        problems: ["8: YAxis is used where the scan can't follow it"],
      },
      {
        line: 9,
        name: "Recharts",
        problems: ["9: Recharts is used where the scan can't follow it"],
      },
      {
        line: 10,
        name: "AXIS_LABEL_STYLE",
        problems: ["10: AXIS_LABEL_STYLE goes where the scan can't follow it"],
      },
      {
        line: 11,
        name: "recharts",
        problems: ["11: loads recharts where the scan can't follow it"],
      },
      {
        line: 12,
        name: "XAxis",
        problems: [
          "12: XAxis has no axisLine, so not an axis line in GRID_STYLE.stroke, or none",
          "12: XAxis tickLine=true, not no tick marks",
          "12: XAxis has no tick, so not tick text in AXIS_STYLE",
        ],
      },
    ]);
    // Only src/charts/kitTheme counts, read from the importing file's folder.
    const axis = "const a = <XAxis {...AXIS_PROPS} />;";
    expect(
      axisProblems(`import { AXIS_PROPS } from "./other/kitTheme";\n${axis}`),
    ).toEqual([
      {
        line: 2,
        name: "XAxis",
        problems: ["2: XAxis takes a spread the scan can't read"],
      },
    ]);
    expect(
      axisProblems(
        `import { AXIS_PROPS } from "../charts/kitTheme";\n${axis}`,
        join(process.cwd(), "src", "components", "Chart.jsx"),
      ),
    ).toEqual([{ line: 2, name: "XAxis", problems: [] }]);
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
      axisProblems(readFileSync(path, "utf8"), path).map((axis) => ({
        ...axis,
        file: relative(ROOT, path),
      })),
    );
    // Every file that draws an axis today, so a scan that finds none fails;
    // a chart added elsewhere is read too.
    expect([...new Set(found.map(({ file }) => file))]).toEqual(
      expect.arrayContaining([
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
