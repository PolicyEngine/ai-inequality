// Tests for the policy-analysis page's health-coverage figures.
//
// Invariants:
//
// * src/data/revenueLines.json comes from the sweep the page reads, and its
//   counting lines equal federalRow(_, true) and stateDeltaRow(_, true)
//   added up over the states, at every shift;
// * each figure draws the file's values, the two revenue panels share one
//   y-axis whose ticks include 0, and every y=0 line is ZERO_LINE;
// * lines counting health coverage draw LINE.main solid, and lines not
//   counting it LINE.comparison dashed;
// * the page prints the gated copy, with numbers from the file, and the UK
//   page renders neither figure;
// * the states' line not counting health coverage reads "about even" in the
//   caption and the tooltip wherever it is smaller than the workers' state
//   payroll taxes the line leaves out, and as an amount elsewhere;
// * the new chart files hold no colour literal and name no CSS variable
//   kitTheme.js doesn't.

import { cloneElement } from "react";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { billions } from "../charts/billions";
import {
  COMPARISON_DASH,
  LINE,
  TEXT,
  ZERO_LINE,
  tokensUsed,
} from "../charts/kitTheme";
import revenueLines from "../data/revenueLines.json";
import sweepData from "../data/shiftSweepData.json";
import PolicyAnalysis from "../views/PolicyAnalysis";
import {
  federalRow,
  showsHealthCoverageFigures,
  stateDeltaRow,
} from "../utils/sweepRevenue";
import CaliforniaRevenue, {
  SERIES_KEYS,
  californiaTicks,
} from "./CaliforniaRevenue";
import RevenueByGovernment, {
  PANELS,
  sharedTicks,
} from "./RevenueByGovernment";
import {
  QUOTED_SHIFT,
  healthCoverageCopy,
  linesAt,
  statesAboutEven,
  statesNotCounting,
} from "./healthCoverageCopy";

// jsdom gives ResponsiveContainer no size, so Recharts draws nothing there. A
// fixed size lets these tests read what the charts draw.
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    ResponsiveContainer: ({ children, height }) =>
      cloneElement(children, { width: 600, height }),
  };
});

// A failed hover test would otherwise leave later tests on fake timers.
afterEach(() => {
  vi.useRealTimers();
});

const ROOT = process.cwd();
const metadata = sweepData.metadata;
const lines = revenueLines.lines;

// The copy as it passed the voice gate
// (runs/from-scratch-2026-11-26/build/copy_pr2.md), with the numbers the
// committed sweep gives.
const GATED = {
  heading: "What counting health coverage changes",
  intro:
    "The sweep counts Medicaid, CHIP and ACA premium tax credits, which grow as wages fall, and charges each government its share of the added spending.",
  revenueTitle:
    "At a 10% shift, health coverage costs the federal government $48 billion and the states $18 billion",
  revenueSubtitle:
    "Net revenue change in 2026, taxes less benefits and excluding corporate taxes, by share of labor income shifted to capital income",
  panels: ["Federal government", "States combined"],
  series: ["Counting health coverage", "Not counting health coverage"],
  federalCaption:
    "At a 10% shift: -$172B counting health coverage, -$124B not counting it",
  statesCaption:
    "At a 10% shift: -$16B counting health coverage, about even not counting it",
  revenueFootnote:
    "The federal line includes employers' state and local payroll taxes. Neither line counts the Additional Medicare Tax, which falls $3.5 billion at a 10% shift, or workers' state payroll taxes, such as California's State Disability Insurance, and local taxes on occupations, which fall $3.4 billion. Counting those, all governments' net revenue falls $195 billion.",
  californiaTitle:
    "At a 10% shift, California's income and use tax rises $5.1 billion, and added health and benefit spending takes $2.9 billion of it",
  californiaSubtitle:
    "Change in California's revenue in 2026, by share of labor income shifted to capital income",
  californiaSeries: [
    "Income and use tax, after refundable credits",
    "Less added health and benefit spending",
  ],
  californiaFootnote:
    "Neither line counts workers' State Disability Insurance contributions, which fall with wages.",
};

const SOURCE = "PolicyEngine 5.0.1, 2026 baseline.";

function renderPage(entry = "/policy-analysis") {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <PolicyAnalysis />
    </MemoryRouter>,
  );
}

function renderFigure(Component) {
  return render(
    <Component revenueLines={revenueLines} metadata={metadata} year={2026} />,
  );
}

// The points a Recharts line path passes through, in pixels.
function pathPoints(path) {
  return [
    ...path.getAttribute("d").matchAll(/[ML](-?[\d.e+-]+),(-?[\d.e+-]+)/g),
  ].map(([, x, y]) => [Number(x), Number(y)]);
}

// What a chart draws: its plot area, the y-axis tick labels in order, each
// line's stroke, dash and points read back into $B, and the zero lines.
function drawn(container) {
  const rect = container.querySelector("clipPath rect");
  const plot = {
    x: Number(rect.getAttribute("x")),
    y: Number(rect.getAttribute("y")),
    width: Number(rect.getAttribute("width")),
    height: Number(rect.getAttribute("height")),
  };
  const yTicks = [
    ...container.querySelectorAll(
      ".recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value",
    ),
  ].map((node) => ({
    text: node.textContent,
    y: Number(node.getAttribute("y")),
  }));
  const zeroLines = [
    ...container.querySelectorAll(".recharts-reference-line-line"),
  ].map((node) => ({
    stroke: node.getAttribute("stroke"),
    strokeWidth: Number(node.getAttribute("stroke-width")),
    strokeDasharray: node.getAttribute("stroke-dasharray"),
    y: Number(node.getAttribute("y1")),
  }));
  const paths = [...container.querySelectorAll("path.recharts-line-curve")];
  return { plot, yTicks, zeroLines, paths };
}

// Reads each point of a path back into a shift and a value in $B, given the
// y-axis domain the chart draws.
function valuesOf(path, plot, [low, high]) {
  return pathPoints(path).map(([x, y]) => ({
    shift: ((x - plot.x) / plot.width) * 100,
    value: high - ((y - plot.y) / plot.height) * (high - low),
  }));
}

describe("the stored lines", () => {
  it("come from the sweep the page reads", () => {
    const bytes = readFileSync(join(ROOT, "src/data/shiftSweepData.json"));
    expect(revenueLines.provenance.sweep_sha256).toBe(
      createHash("sha256").update(bytes).digest("hex"),
    );
    expect(revenueLines.provenance.year).toBe(sweepData.year);
    expect(revenueLines.provenance.code_commit).toBe(metadata.code_commit);
    expect(lines.map((line) => line.shift_pct)).toEqual(
      sweepData.scenarios.map((scenario) => scenario.shift_pct),
    );
  });

  it("equal the site's federalRow and stateDeltaRow counting health coverage", () => {
    const gaps = sweepData.scenarios.flatMap((scenario, i) => {
      const line = lines[i];
      const deltas = Object.values(scenario.state_deltas ?? {});
      const states = deltas.reduce(
        (sum, delta) => sum + stateDeltaRow(delta, true).revenue,
        0,
      );
      const california = scenario.state_deltas?.CA;
      const pairs = [
        [
          "federal",
          line.federal_counting_health_change_b,
          federalRow(scenario, true).revenue,
        ],
        ["states", line.states_counting_health_change_b, states],
        [
          "California net",
          line.california_net_counting_health_change_b,
          california ? stateDeltaRow(california, true).revenue : 0,
        ],
        [
          "California tax",
          line.california_income_and_use_tax_change_b,
          california
            ? stateDeltaRow(california, true).rev_state_income_tax_net
            : 0,
        ],
      ];
      return pairs
        .filter(
          ([, stored, computed]) => !(Math.abs(stored - computed) <= 2e-5),
        )
        .map(
          ([name, stored, computed]) =>
            `${scenario.shift_pct}% ${name}: ${stored} vs ${computed}`,
        );
    });
    expect(gaps).toEqual([]);
  });

  it("show at the 0% shift only where the sweep has no state rows", () => {
    expect(Object.keys(sweepData.scenarios[0].state_deltas ?? {})).toEqual([]);
    expect(linesAt(revenueLines, 0).states_counting_health_change_b).toBe(0);
  });
});

describe("the revenue-by-government figure", () => {
  it("draws both panels on one y-axis whose ticks include 0", () => {
    const { container } = renderFigure(RevenueByGovernment);
    const ticks = sharedTicks(lines);
    expect(ticks).toContain(0);
    const values = lines.flatMap((line) =>
      PANELS.flatMap((panel) => [
        line[panel.counting],
        line[panel.notCounting],
      ]),
    );
    expect(ticks[0]).toBeLessThanOrEqual(Math.min(...values));
    expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(Math.max(...values));

    const labels = PANELS.map((panel) =>
      drawn(container.querySelector(`[data-panel="${panel.id}"]`)).yTicks.map(
        (tick) => tick.text,
      ),
    );
    expect(labels[0]).toEqual(
      ticks.map((tick) => billions(tick, { sign: true })),
    );
    expect(labels[1]).toEqual(labels[0]);
    expect(labels[0]).toContain("$0B");
  });

  it("draws the file's values, counting solid teal and not counting dashed gray", () => {
    const { container } = renderFigure(RevenueByGovernment);
    const ticks = sharedTicks(lines);
    const domain = [ticks[0], ticks[ticks.length - 1]];
    for (const panel of PANELS) {
      const chart = drawn(
        container.querySelector(`[data-panel="${panel.id}"]`),
      );
      expect(chart.paths).toHaveLength(2);
      const [counting, notCounting] = chart.paths;
      expect(counting.getAttribute("stroke")).toBe(LINE.main);
      expect(counting.getAttribute("stroke-dasharray")).toBeNull();
      expect(notCounting.getAttribute("stroke")).toBe(LINE.comparison);
      expect(notCounting.getAttribute("stroke-dasharray")).toBe(
        COMPARISON_DASH,
      );
      for (const [path, key] of [
        [counting, panel.counting],
        [notCounting, panel.notCounting],
      ]) {
        const points = valuesOf(path, chart.plot, domain);
        expect(points).toHaveLength(lines.length);
        points.forEach((point, i) => {
          expect(point.shift).toBeCloseTo(lines[i].shift_pct, 6);
          expect(point.value).toBeCloseTo(lines[i][key], 6);
        });
      }
    }
  });

  it("draws y=0 as ZERO_LINE in each panel", () => {
    const { container } = renderFigure(RevenueByGovernment);
    for (const panel of PANELS) {
      const chart = drawn(
        container.querySelector(`[data-panel="${panel.id}"]`),
      );
      const zero = chart.yTicks.find((tick) => tick.text === "$0B");
      expect(chart.zeroLines).toEqual([
        {
          stroke: ZERO_LINE.stroke,
          strokeWidth: ZERO_LINE.strokeWidth,
          strokeDasharray: null,
          y: zero.y,
        },
      ]);
    }
  });

  // Moves the pointer over a shift in one panel and reads its tooltip's
  // label and items. Recharts reads the pointer on the next animation frame,
  // so the caller runs on fake timers.
  async function hover(node, shift) {
    const { plot } = drawn(node);
    fireEvent.mouseMove(node.querySelector(".recharts-wrapper"), {
      clientX: plot.x + (plot.width * shift) / 100,
      clientY: plot.y + plot.height / 2,
    });
    await act(async () => {
      vi.advanceTimersByTime(100);
    });
    const tooltip = node.querySelector(".recharts-default-tooltip");
    return {
      label: tooltip.querySelector(".recharts-tooltip-label").textContent,
      items: [...tooltip.querySelectorAll(".recharts-tooltip-item")].map(
        (item) => [
          item.querySelector(".recharts-tooltip-item-name").textContent,
          item.querySelector(".recharts-tooltip-item-value").textContent,
        ],
      ),
    };
  }

  it("shows both lines' values at the hovered shift, on a kit crosshair", async () => {
    vi.useFakeTimers();
    const { container } = renderFigure(RevenueByGovernment);
    const at = linesAt(revenueLines, 10);
    // The states' line not counting health coverage reads as its caption
    // does: about even at 10%, inside the workers' state payroll taxes it
    // leaves out.
    const expected = {
      federal: billions(at.federal_not_counting_health_change_b, {
        sign: true,
      }),
      states: "about even",
    };
    for (const panel of PANELS) {
      const node = container.querySelector(`[data-panel="${panel.id}"]`);
      expect(await hover(node, 10)).toEqual({
        label: "10% shift",
        items: [
          [GATED.series[0], billions(at[panel.counting], { sign: true })],
          [GATED.series[1], expected[panel.id]],
        ],
      });
      const cursor = node.querySelector(".recharts-tooltip-cursor");
      expect(cursor.getAttribute("stroke")).toBe(TEXT.muted);
    }
    vi.useRealTimers();
  });

  it("prints the states' amount not counting health coverage where it passes the left-out taxes", async () => {
    vi.useFakeTimers();
    const { container } = renderFigure(RevenueByGovernment);
    const node = container.querySelector('[data-panel="states"]');
    const at = linesAt(revenueLines, 20);
    expect(statesAboutEven(at)).toBe(false);
    expect(await hover(node, 20)).toEqual({
      label: "20% shift",
      items: [
        [
          GATED.series[0],
          billions(at.states_counting_health_change_b, { sign: true }),
        ],
        [
          GATED.series[1],
          billions(at.states_not_counting_health_change_b, { sign: true }),
        ],
      ],
    });
    vi.useRealTimers();
  });

  it("titles, captions and footnote are the gated copy", () => {
    const { container } = renderFigure(RevenueByGovernment);
    const figure = container.querySelector("figure#revenue-by-government");
    const view = within(figure);
    expect(view.getByRole("heading", { level: 3 }).textContent).toBe(
      GATED.revenueTitle,
    );
    expect(figure).toHaveAccessibleName(GATED.revenueTitle);
    expect(figure.querySelector(".study-figure-subtitle").textContent).toBe(
      GATED.revenueSubtitle,
    );
    expect(
      view
        .getAllByRole("heading", { level: 4 })
        .map((node) => node.textContent),
    ).toEqual(GATED.panels);
    expect(
      [...figure.querySelectorAll(".study-figure-legend-item")].map(
        (node) => node.textContent,
      ),
    ).toEqual(GATED.series);
    expect(
      [...figure.querySelectorAll(".study-figure-caption")].map(
        (node) => node.textContent,
      ),
    ).toEqual([GATED.federalCaption, GATED.statesCaption]);
    expect(figure.querySelector(".study-figure-footnote").textContent).toBe(
      GATED.revenueFootnote,
    );
    expect(figure.querySelector(".study-figure-source").textContent).toBe(
      SOURCE,
    );
    // Each line's name in the chart, which its tooltip shows.
    for (const panel of PANELS) {
      expect(
        drawn(container.querySelector(`[data-panel="${panel.id}"]`)).paths.map(
          (path) => path.getAttribute("name"),
        ),
      ).toEqual(GATED.series);
    }
  });
});

describe("the California figure", () => {
  it("draws the file's values on its own axis, with ZERO_LINE at y=0", () => {
    const { container } = renderFigure(CaliforniaRevenue);
    const ticks = californiaTicks(lines);
    expect(ticks).toContain(0);
    const chart = drawn(container.querySelector('[data-panel="california"]'));
    expect(chart.yTicks.map((tick) => tick.text)).toEqual(
      ticks.map((tick) => billions(tick, { sign: true })),
    );
    const zero = chart.yTicks.find((tick) => tick.text === "$0B");
    expect(chart.zeroLines).toEqual([
      {
        stroke: ZERO_LINE.stroke,
        strokeWidth: ZERO_LINE.strokeWidth,
        strokeDasharray: null,
        y: zero.y,
      },
    ]);
    const [incomeTax, net] = chart.paths;
    expect(incomeTax.getAttribute("stroke")).toBe(LINE.main);
    expect(incomeTax.getAttribute("stroke-dasharray")).toBeNull();
    expect(net.getAttribute("stroke")).toBe(LINE.comparison);
    expect(net.getAttribute("stroke-dasharray")).toBe(COMPARISON_DASH);
    const domain = [ticks[0], ticks[ticks.length - 1]];
    for (const [path, key] of [
      [incomeTax, SERIES_KEYS.incomeTax],
      [net, SERIES_KEYS.net],
    ]) {
      valuesOf(path, chart.plot, domain).forEach((point, i) => {
        expect(point.shift).toBeCloseTo(lines[i].shift_pct, 6);
        expect(point.value).toBeCloseTo(lines[i][key], 6);
      });
    }
  });

  it("title, legend and footnote are the gated copy", () => {
    const { container } = renderFigure(CaliforniaRevenue);
    const figure = container.querySelector("figure#california");
    expect(within(figure).getByRole("heading", { level: 3 }).textContent).toBe(
      GATED.californiaTitle,
    );
    expect(figure.querySelector(".study-figure-subtitle").textContent).toBe(
      GATED.californiaSubtitle,
    );
    expect(
      [...figure.querySelectorAll(".study-figure-legend-item")].map(
        (node) => node.textContent,
      ),
    ).toEqual(GATED.californiaSeries);
    expect(figure.querySelector(".study-figure-footnote").textContent).toBe(
      GATED.californiaFootnote,
    );
    expect(figure.querySelector(".study-figure-source").textContent).toBe(
      SOURCE,
    );
  });
});

describe("the copy", () => {
  it("prints the gated strings from the file's numbers", () => {
    const copy = healthCoverageCopy(revenueLines);
    expect(copy.section).toEqual({
      heading: GATED.heading,
      intro: GATED.intro,
    });
    expect(copy.revenueByGovernment).toEqual({
      title: GATED.revenueTitle,
      subtitle: GATED.revenueSubtitle,
      panels: { federal: GATED.panels[0], states: GATED.panels[1] },
      series: { counting: GATED.series[0], notCounting: GATED.series[1] },
      captions: { federal: GATED.federalCaption, states: GATED.statesCaption },
      footnote: GATED.revenueFootnote,
    });
    expect(copy.california).toEqual({
      title: GATED.californiaTitle,
      subtitle: GATED.californiaSubtitle,
      series: {
        incomeTax: GATED.californiaSeries[0],
        net: GATED.californiaSeries[1],
      },
      footnote: GATED.californiaFootnote,
    });
  });

  it("uses the verbs the file's signs call for", () => {
    const at = linesAt(revenueLines, QUOTED_SHIFT);
    // "costs the federal government ... and the states ..."
    expect(at.federal_health_change_b).toBeGreaterThan(0);
    expect(at.state_health_change_b).toBeGreaterThan(0);
    // "... which falls ...", "... which fall ...", "... net revenue falls ..."
    expect(at.additional_medicare_tax_change_b).toBeLessThan(0);
    expect(
      at.employee_state_payroll_tax_change_b +
        at.local_occupational_tax_change_b,
    ).toBeLessThan(0);
    expect(at.total_rev_change_b).toBeLessThan(0);
    // "... income and use tax rises ..., and ... spending takes ... of it"
    const tax = at.california_income_and_use_tax_change_b;
    const net = at.california_net_counting_health_change_b;
    expect(tax).toBeGreaterThan(0);
    expect(tax - net).toBeGreaterThan(0);
    expect(tax - net).toBeLessThan(tax);
  });

  it("calls the states about even only within the taxes their line leaves out", () => {
    const at = linesAt(revenueLines, QUOTED_SHIFT);
    expect(statesAboutEven(at)).toBe(true);
    const settled = { ...at, states_not_counting_health_change_b: 4.2 };
    expect(statesAboutEven(settled)).toBe(false);
    const copy = healthCoverageCopy({
      ...revenueLines,
      lines: lines.map((line) =>
        line.shift_pct === QUOTED_SHIFT ? settled : line,
      ),
    });
    expect(copy.revenueByGovernment.captions.states).toBe(
      "At a 10% shift: -$16B counting health coverage, +$4.2B not counting it",
    );
  });

  it("calls the states about even at each shift by the same rule", () => {
    // Today only the 10% shift falls inside workers' state payroll taxes.
    expect(lines.filter(statesAboutEven).map((line) => line.shift_pct)).toEqual(
      [10],
    );
    for (const line of lines) {
      expect(statesNotCounting(line)).toBe(
        statesAboutEven(line)
          ? "about even"
          : billions(line.states_not_counting_health_change_b, { sign: true }),
      );
    }
  });
});

describe("the policy-analysis page", () => {
  it("shows both figures for the US, between the hero and the income distribution", () => {
    const { container } = renderPage();
    const heading = screen.getByRole("heading", {
      level: 2,
      name: GATED.heading,
    });
    expect(screen.getByText(GATED.intro)).toBeInTheDocument();
    const section = heading.closest("section");
    const revenue = container.querySelector("#revenue-by-government");
    const california = container.querySelector("#california");
    expect(section).toContainElement(revenue);
    expect(section).toContainElement(california);
    expect(revenue.compareDocumentPosition(california)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    const hero = container.querySelector(".policy-analysis-hero");
    const distribution = container.querySelector(".income-background");
    expect(hero.compareDocumentPosition(section)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    expect(section.compareDocumentPosition(distribution)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    for (const text of [
      GATED.revenueTitle,
      GATED.federalCaption,
      GATED.statesCaption,
      GATED.revenueFootnote,
      GATED.californiaTitle,
      GATED.californiaFootnote,
    ]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
  });

  it("renders neither figure for the UK", () => {
    const { container } = renderPage("/policy-analysis?country=uk");
    expect(container.querySelector("#revenue-by-government")).toBeNull();
    expect(container.querySelector("#california")).toBeNull();
    expect(container.querySelector(".study-figure")).toBeNull();
    expect(screen.queryByText(GATED.heading)).toBeNull();
    expect(screen.queryByText(GATED.revenueTitle)).toBeNull();
  });

  it("shows the figures only for a US sweep with health coverage and state rows", () => {
    expect(showsHealthCoverageFigures("us", sweepData)).toBe(true);
    expect(showsHealthCoverageFigures("uk", sweepData)).toBe(false);
    const withoutHealth = {
      ...sweepData,
      scenarios: sweepData.scenarios.map((scenario) => {
        const copy = { ...scenario };
        delete copy.federal_health_change_b;
        return copy;
      }),
    };
    expect(showsHealthCoverageFigures("us", withoutHealth)).toBe(false);
    const withoutStates = {
      ...sweepData,
      scenarios: sweepData.scenarios.map((scenario) => ({
        ...scenario,
        state_deltas: {},
      })),
    };
    expect(showsHealthCoverageFigures("us", withoutStates)).toBe(false);
  });
});

describe("the new chart files", () => {
  const JS_FILES = [
    "src/charts/billions.js",
    "src/charts/Figure.jsx",
    "src/charts/LinePanel.jsx",
    "src/components/CaliforniaRevenue.jsx",
    "src/components/RevenueByGovernment.jsx",
    "src/components/healthCoverageCopy.js",
  ];
  const CSS_FILES = ["src/charts/Figure.css"];
  // CSS colour keywords, as whole words in code and style values.
  const NAMED = String.raw`\b(?:white|black|red|green|blue|orange|yellow|purple|pink|brown|gray|grey|teal|navy|silver|maroon|olive|lime|aqua|fuchsia|cyan|magenta|transparent|currentcolor)\b`;
  const LITERALS = [
    /#[0-9a-f]{3,8}\b/i,
    /\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\(/i,
  ];

  const withoutComments = (text) =>
    text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

  it("hold no colour literal", () => {
    const found = [...JS_FILES, ...CSS_FILES].flatMap((path) => {
      const code = withoutComments(readFileSync(join(ROOT, path), "utf8"));
      return LITERALS.filter((pattern) => pattern.test(code)).map(
        (pattern) => `${path}: ${pattern}`,
      );
    });
    expect(found).toEqual([]);
  });

  it("name colours only through kitTheme.js", () => {
    // JavaScript takes every colour from kitTheme's exports, so it names no
    // CSS variable and no colour keyword in a string.
    const jsFound = JS_FILES.flatMap((path) => {
      const code = withoutComments(readFileSync(join(ROOT, path), "utf8"));
      const strings = [...code.matchAll(/(["'`])((?:\\.|(?!\1).)*)\1/g)].map(
        ([, , text]) => text,
      );
      return strings
        .filter(
          (text) =>
            /var\(--/.test(text) ||
            new RegExp(`^\\s*${NAMED}\\s*$`, "i").test(text),
        )
        .map((text) => `${path}: "${text}"`);
    });
    expect(jsFound).toEqual([]);

    // The stylesheet's colours are kit tokens kitTheme.js names, which
    // kitTheme.test.js checks the export defines.
    const known = new Set(tokensUsed());
    const cssFound = CSS_FILES.flatMap((path) => {
      const css = withoutComments(readFileSync(join(ROOT, path), "utf8"));
      const declarations = [...css.matchAll(/([\w-]+)\s*:\s*([^;{}]+);/g)];
      return declarations.flatMap(([, property, value]) => [
        ...[...value.matchAll(/var\((--[\w-]+)\)/g)]
          .filter(([, token]) => !known.has(token))
          .map(([, token]) => `${path}: ${property} uses ${token}`),
        ...(new RegExp(NAMED, "i").test(value)
          ? [`${path}: ${property}: ${value.trim()}`]
          : []),
      ]);
    });
    expect(cssFound).toEqual([]);
  });
});
