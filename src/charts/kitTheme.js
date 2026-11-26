// Chart styling for the study site, taken from @policyengine/ui-kit.
//
// Every colour here is a kit token, so charts carry no hex values of their
// own. Tailwind writes a theme variable into the built CSS only when something
// uses it, so kitTheme.test.js checks that the export defines every token
// below.
import {
  AXIS_STYLE,
  GRID_STYLE,
  LEGEND_STYLE,
  TOOLTIP_STYLE,
  chartLineColors,
  impactColors,
} from "@policyengine/ui-kit/charts";

export { AXIS_STYLE, GRID_STYLE, LEGEND_STYLE };

// Recharts' Tooltip takes these three as contentStyle, labelStyle and
// itemStyle.
export const TOOLTIP_CONTENT_STYLE = TOOLTIP_STYLE.contentStyle;
export const TOOLTIP_LABEL_STYLE = TOOLTIP_STYLE.labelStyle;
export const TOOLTIP_ITEM_STYLE = TOOLTIP_STYLE.itemStyle;

// Series colours in a fixed order. A chart with n series takes the first n,
// by position, and never cycles. This order keeps neighbours apart: the
// dataviz palette validator puts every adjacent pair at a ΔE (OKLab × 100) of
// at least 15.6 in normal vision and 15.5 under colour-vision deficiency, for
// the first 3, 4, 5 or all 6.
export const SERIES = [
  "var(--chart-1)", // #319795
  "var(--chart-3)", // #285e61
  "var(--chart-2)", // #0ea5e9
  "var(--chart-4)", // #026aa2
  "var(--color-gray-400)", // #94a3b8
  "var(--chart-5)", // #64748b
];

// Gains draw teal and losses gray, as the kit's impact charts draw them.
export const GAIN = impactColors.positive;
export const LOSS = impactColors.negative;

// For measures where a fall is good news, such as poverty. Read the inverted
// pair directly: getImpactColors(true) at kit 0.12.0 swaps it back.
export const FALL_IS_GOOD = {
  fall: impactColors.negativeInverted,
  rise: impactColors.positiveInverted,
};

// A figure's main line draws solid teal and its comparison line dashed gray.
export const LINE = {
  main: chartLineColors.reform,
  comparison: chartLineColors.baseline,
};
export const COMPARISON_DASH = "6 4";

// The zero line on charts of changes, drawn heavier than the kit's 1px
// gray-600 so gains and losses read against it.
export const ZERO_LINE = { stroke: "var(--foreground)", strokeWidth: 1.5 };

// The edge every stacked band and bar draws, in the page's background colour.
// Bands that touch need it: the kit has no four series colours that clear a
// ΔE of 15 against each other, and in a stack a band between two others can
// shrink to nothing and let them meet.
export const BAND_EDGE = { stroke: "var(--background)", strokeWidth: 1 };

// Text inside a chart: labels and values stay in ink, never a series colour.
export const TEXT = {
  primary: "var(--foreground)",
  muted: "var(--muted-foreground)",
};

// Every CSS variable a chart can reach through this module, including the
// ones inside the kit's axis, grid, legend and tooltip styles.
export function tokensUsed() {
  const found = new Set();
  const walk = (value) => {
    if (typeof value === "string") {
      for (const [, name] of value.matchAll(/var\((--[\w-]+)\)/g)) {
        found.add(name);
      }
    } else if (value && typeof value === "object") {
      Object.values(value).forEach(walk);
    }
  };
  walk([
    AXIS_STYLE,
    GRID_STYLE,
    LEGEND_STYLE,
    TOOLTIP_STYLE,
    SERIES,
    GAIN,
    LOSS,
    FALL_IS_GOOD,
    LINE,
    ZERO_LINE,
    BAND_EDGE,
    TEXT,
  ]);
  return [...found].sort();
}
