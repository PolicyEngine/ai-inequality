/**
 * Shared chart styling constants and formatters used across analysis components.
 */

export const TOOLTIP_STYLE = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 6,
  padding: "8px 12px",
  fontSize: 13,
};

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
