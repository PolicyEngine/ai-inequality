/**
 * Shared chart styling constants and formatters used across analysis components.
 */

import { TOOLTIP_CONTENT_STYLE } from "../charts/kitTheme";

// The UI kit's tooltip box, which every chart passes as contentStyle.
export const TOOLTIP_STYLE = TOOLTIP_CONTENT_STYLE;

/** Format a decimal as a percentage string, e.g. 0.205 → "20.5%" */
export const pct = (v) => `${(v * 100).toFixed(1)}%`;

/** Format a number as a dollar amount in billions, e.g. 2220 → "$2,220B" */
export const dollars = (v) => `$${v.toLocaleString()}B`;

/** Format a number as a currency string with no decimals, e.g. 15080 → "$15,080" */
export const fmt = (v) =>
  v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
