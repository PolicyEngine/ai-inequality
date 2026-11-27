// The one formatter for amounts in billions on the page's charts: the
// health-coverage figures' titles, captions, footnotes, tooltips and axes, and
// the shift sweep's axes and tooltips.
//
// By default it prints whole billions from $10 billion up and tenths below, as
// the revenue prose in ShiftSweep does, and rounds before it picks, so 9.96
// prints "$10". With a precision it prints that many decimals at every size.
// A signed amount takes a hyphen-minus or a plus before the currency symbol;
// the page prints negative dollars with a hyphen-minus elsewhere too. An
// amount that prints as zero takes no sign. grouping: false drops the
// thousands separator, as the sweep's axes and tooltips print amounts.
//
//   billions(47.95, { unit: "billion" })                  -> "$48 billion"
//   billions(-172.1, { sign: true })                      -> "-$172B"
//   billions(2.08, { sign: true })                        -> "+$2.1B"
//   billions(-2011.26, { sign: true, precision: 1,
//                        grouping: false })               -> "-$2011.3B"
//   billions(-9.5, { sign: true, currencySymbol: "£" })   -> "-£9.5B"
export function billions(
  value,
  {
    unit = "B",
    sign = false,
    precision,
    currencySymbol = "$",
    grouping = true,
  } = {},
) {
  if (!Number.isFinite(value)) {
    throw new Error(`billions: ${value} is not a finite number`);
  }
  const size = Math.abs(value);
  let shown = size;
  let digits = precision;
  if (precision === undefined) {
    const tenths = Math.round(size * 10) / 10;
    shown = tenths >= 10 ? Math.round(size) : tenths;
    digits = shown >= 10 || shown === 0 ? 0 : 1;
  }
  // toFixed rounds the number's exact binary value, as the sweep always has;
  // toLocaleString rounds its shortest decimal form, so 0.15 would print 0.2
  // where toFixed prints 0.1. The default path's shown is rounded already, so
  // both print it the same up to 10^16 billion, far past any amount here.
  const fixed = shown.toFixed(digits);
  const amount = grouping
    ? fixed.replace(/^\d+/, (whole) =>
        whole.replace(/\B(?=(\d{3})+(?!\d))/g, ","),
      )
    : fixed;
  const suffix = unit === "billion" ? " billion" : "B";
  const printsZero = !/[1-9]/.test(amount);
  const prefix = !sign || printsZero ? "" : value < 0 ? "-" : "+";
  return `${prefix}${currencySymbol}${amount}${suffix}`;
}
