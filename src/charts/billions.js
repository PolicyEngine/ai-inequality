// The one formatter for amounts in billions of dollars on the page's
// health-coverage figures: their titles, captions, footnotes, tooltips and
// axes. It prints whole billions from $10 billion up and tenths below, as the
// revenue prose in ShiftSweep does, and rounds before it picks, so 9.96 prints
// "$10". Negative amounts take a hyphen-minus before the dollar sign, the
// character the page prints for negative dollars elsewhere.
//
//   billions(47.95, { unit: "billion" })  -> "$48 billion"
//   billions(-172.1, { sign: true })      -> "-$172B"
//   billions(2.08, { sign: true })        -> "+$2.1B"
export function billions(value, { unit = "B", sign = false } = {}) {
  if (!Number.isFinite(value)) {
    throw new Error(`billions: ${value} is not a finite number`);
  }
  const size = Math.abs(value);
  const tenths = Math.round(size * 10) / 10;
  const shown = tenths >= 10 ? Math.round(size) : tenths;
  const digits = shown >= 10 || shown === 0 ? 0 : 1;
  const amount = shown.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  const suffix = unit === "billion" ? " billion" : "B";
  const prefix = !sign || shown === 0 ? "" : value < 0 ? "-" : "+";
  return `${prefix}$${amount}${suffix}`;
}
