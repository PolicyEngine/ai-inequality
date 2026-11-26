import React from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { billions } from "./billions";
import {
  AXIS_STYLE,
  COMPARISON_DASH,
  GRID_STYLE,
  LINE,
  TEXT,
  TOOLTIP_CONTENT_STYLE,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
  ZERO_LINE,
} from "./kitTheme";

// A figure's main line draws solid teal, its comparison dashed gray.
export const LINE_STYLES = {
  main: { stroke: LINE.main },
  comparison: { stroke: LINE.comparison, strokeDasharray: COMPARISON_DASH },
};

const STROKE_WIDTH = 2.5;
const SHIFT_TICKS = [0, 20, 40, 60, 80, 100];

// The vertical line the tooltip follows, in the axis text's ink.
const CROSSHAIR = { stroke: TEXT.muted, strokeWidth: 1 };

export function shiftLabel(shift) {
  return shift === 0 ? "Baseline" : `${shift}% shift`;
}

export function formatAmount(value) {
  return billions(value, { sign: true });
}

// Recharts' accessibility layer makes each chart a keyboard stop whose arrow
// keys move the tooltip from shift to shift. This tells screen readers so.
export const KEYBOARD_HINT = "Use the arrow keys to step through the shifts.";

// One chart of lines over the shift, in $B, with straight segments between
// the sweep's points, the y-axis on the given ticks and a heavier line at
// zero. `series` lists each line as { key, name, style, format }, where key
// names the field in each row of `data`, style is "main" or "comparison" and
// format, if given, prints the line's value in the tooltip from the hovered
// row; otherwise the tooltip prints the signed amount. `label` names the
// chart for screen readers, which reach it as a keyboard stop.
export default function LinePanel({
  data,
  series,
  ticks,
  label,
  height = 300,
}) {
  const formats = Object.fromEntries(
    series.map(({ key, format }) => [key, format]),
  );
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart
        data={data}
        margin={{ top: 8, right: 16, bottom: 4, left: 0 }}
        aria-label={label}
        desc={KEYBOARD_HINT}
      >
        <CartesianGrid {...GRID_STYLE} vertical={false} />
        <XAxis
          dataKey="shift_pct"
          type="number"
          domain={[0, 100]}
          ticks={SHIFT_TICKS}
          tickFormatter={(value) => `${value}%`}
          tick={AXIS_STYLE}
          axisLine={{ stroke: GRID_STYLE.stroke }}
          tickLine={false}
        />
        <YAxis
          ticks={ticks}
          domain={[ticks[0], ticks[ticks.length - 1]]}
          tickFormatter={formatAmount}
          tick={AXIS_STYLE}
          axisLine={false}
          tickLine={false}
          width={68}
        />
        <ReferenceLine y={0} {...ZERO_LINE} />
        <Tooltip
          cursor={CROSSHAIR}
          contentStyle={TOOLTIP_CONTENT_STYLE}
          labelStyle={TOOLTIP_LABEL_STYLE}
          itemStyle={TOOLTIP_ITEM_STYLE}
          labelFormatter={shiftLabel}
          formatter={(value, name, item) => {
            const format = formats[item.dataKey];
            return [format ? format(item.payload) : formatAmount(value), name];
          }}
        />
        {series.map(({ key, name, style }) => {
          const { stroke, strokeDasharray } = LINE_STYLES[style];
          return (
            <Line
              key={key}
              type="linear"
              dataKey={key}
              name={name}
              stroke={stroke}
              strokeDasharray={strokeDasharray}
              strokeWidth={STROKE_WIDTH}
              dot={false}
              activeDot={{ r: 4, fill: stroke, stroke }}
              isAnimationActive={false}
            />
          );
        })}
      </LineChart>
    </ResponsiveContainer>
  );
}
