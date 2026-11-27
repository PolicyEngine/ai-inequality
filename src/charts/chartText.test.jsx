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
// it fails.
const AXIS_COMPONENTS = new Set(["XAxis", "YAxis"]);
const COLOUR_KEY = /(?:fill|stroke|colou?r|background)$/i;
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
  const resolve = (node, seen = new Set()) => {
    if (node?.type !== "Identifier" || !constants.has(node.name)) return node;
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
        : !COLOUR_KEY.test(keyName(property) ?? "fill"),
    ) &&
    node.properties.some(
      (property) =>
        property.type === "SpreadElement" &&
        allowed(resolve(property.argument)),
    );
  const kitTick = (node) =>
    isName(node, "AXIS_STYLE") ||
    isMember(node, "AXIS_PROPS", "tick") ||
    plainObject(node, kitTick);
  const kitTitleStyle = (node) =>
    isName(node, "AXIS_LABEL_STYLE") || plainObject(node, kitTitleStyle);
  const CHECKS = {
    axisLine: [
      "an axis line in GRID_STYLE.stroke, or none",
      (node) =>
        isFalse(node) ||
        isMember(node, "AXIS_PROPS", "axisLine") ||
        (node?.type === "ObjectExpression" &&
          node.properties.every(
            (property) =>
              property.type === "Property" &&
              (keyName(property) === "stroke"
                ? isMember(resolve(property.value), "GRID_STYLE", "stroke")
                : !COLOUR_KEY.test(keyName(property) ?? "fill")),
          ) &&
          node.properties.some((property) => keyName(property) === "stroke")),
    ],
    tickLine: [
      "no tick marks",
      (node) => isFalse(node) || isMember(node, "AXIS_PROPS", "tickLine"),
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
  walk(ast, (node) => {
    if (node.type !== "JSXOpeningElement") return;
    const name = axisName(node.name);
    if (!name) return;
    // Each checked prop's final value: KIT from AXIS_PROPS, UNREAD from a
    // spread the scan can't read, or the expression an attribute sets.
    const props = new Map();
    const spread = (argument) => {
      const value = resolve(argument);
      if (isName(argument, "AXIS_PROPS")) {
        for (const key of ["axisLine", "tickLine", "tick"]) props.set(key, KIT);
      } else if (value?.type === "ObjectExpression") {
        for (const property of value.properties) {
          if (property.type === "SpreadElement") spread(property.argument);
          else if (keyName(property) in CHECKS) {
            props.set(keyName(property), resolve(property.value));
          } else if (keyName(property) === null) {
            for (const key of Object.keys(CHECKS)) props.set(key, UNREAD);
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
      if (!(key in CHECKS)) continue;
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
    const problems = [];
    for (const [key, [wanted, passes]] of Object.entries(CHECKS)) {
      const value = props.get(key);
      // An axis with no title draws none; every other prop has a default
      // that Recharts draws in #666.
      if (value === undefined && key === "label") continue;
      if (value === KIT) continue;
      if (value === undefined) {
        problems.push(
          `${node.loc.start.line}: ${name} has no ${key}, so not ${wanted}`,
        );
      } else if (value === UNREAD) {
        problems.push(
          `${node.loc.start.line}: ${name} ${key} comes from a spread the scan can't read`,
        );
      } else if (!passes(value)) {
        problems.push(
          `${node.loc.start.line}: ${name} ${key}=${value.range ? text(value) : value.raw}, not ${wanted}`,
        );
      }
    }
    axes.push({ line: node.loc.start.line, name, problems });
  });
  return axes;
}

describe("chart axes", () => {
  it("the axis scan reads each axis's final props", () => {
    const sample = [
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
    ].join("\n");
    expect(axisProblems(sample)).toEqual([
      { line: 5, name: "XAxis", problems: [] },
      {
        line: 6,
        name: "XAxis",
        problems: [
          "6: XAxis axisLine=true, not an axis line in GRID_STYLE.stroke, or none",
          "6: XAxis has no tick, so not tick text in AXIS_STYLE",
        ],
      },
      {
        line: 7,
        name: "YAxis",
        problems: [
          "7: YAxis axisLine=true, not an axis line in GRID_STYLE.stroke, or none",
        ],
      },
      {
        line: 8,
        name: "YAxis",
        problems: ["8: YAxis tickLine=true, not no tick marks"],
      },
      {
        line: 9,
        name: "XAxis",
        problems: [
          "9: XAxis tick={ fontSize: 11 }, not tick text in AXIS_STYLE",
        ],
      },
      {
        line: 10,
        name: "XAxis",
        problems: [
          "10: XAxis tick={ ...AXIS_STYLE, fill: TEXT.primary }, not tick text in AXIS_STYLE",
        ],
      },
      { line: 11, name: "XAxis", problems: [] },
      {
        line: 12,
        name: "YAxis",
        problems: [
          '12: YAxis label="Billions", not a title in AXIS_LABEL_STYLE',
        ],
      },
      {
        line: 13,
        name: "YAxis",
        problems: [
          "13: YAxis label={ value: 'B', style: { fontSize: 13 } }, not a title in AXIS_LABEL_STYLE",
        ],
      },
      { line: 14, name: "YAxis", problems: [] },
      {
        line: 15,
        name: "YAxis",
        problems: [
          "15: YAxis axisLine comes from a spread the scan can't read",
          "15: YAxis tickLine comes from a spread the scan can't read",
          "15: YAxis tick comes from a spread the scan can't read",
          "15: YAxis label comes from a spread the scan can't read",
        ],
      },
      {
        line: 16,
        name: "XAxis",
        problems: [
          "16: XAxis has no axisLine, so not an axis line in GRID_STYLE.stroke, or none",
        ],
      },
      { line: 17, name: "YAxis", problems: [] },
      {
        line: 18,
        name: "YAxis",
        problems: [
          "18: YAxis axisLine={ stroke: TEXT.primary }, not an axis line in GRID_STYLE.stroke, or none",
        ],
      },
      {
        line: 19,
        name: "YAxis",
        problems: ["19: YAxis tickLine=true, not no tick marks"],
      },
      {
        line: 20,
        name: "XAxis",
        problems: [
          "20: XAxis label={ value: 'B', style: AXIS_LABEL_STYLE, fill: TEXT.primary }, not a title in AXIS_LABEL_STYLE",
        ],
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
