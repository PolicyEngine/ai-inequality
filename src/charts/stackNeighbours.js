// Which series a stacked chart draws next to each other, and how far apart
// two kit colours sit. Tests use these to check that bands which touch on the
// page can be told apart; nothing on the page imports them.

// Pairs of series, by index into keys, that touch in some row. Recharts'
// stackOffset="sign" (offsetSign in recharts/lib/util/ChartUtils.js) stacks
// each row outward from zero in key order: a value of zero or more on the
// positive side, a negative one below. Two series touch where they sit next to
// each other on one side, so two that are not neighbours in keys touch
// wherever every series between them is near zero. A series shorter than
// minShare of the chart's full range counts as absent. Each pair appears once,
// lower index first, with the indexes of the rows where it touches.
export function touchingPairs(rows, keys, minShare = 0.005) {
  const value = (row, key) => row[key] ?? 0;
  const sides = rows.map((row) => [
    keys.reduce((sum, key) => sum + Math.max(0, value(row, key)), 0),
    keys.reduce((sum, key) => sum + Math.min(0, value(row, key)), 0),
  ]);
  const range =
    Math.max(0, ...sides.map(([up]) => up)) -
    Math.min(0, ...sides.map(([, down]) => down));
  const pairs = new Map();
  rows.forEach((row, rowIndex) => {
    const up = [];
    const down = [];
    keys.forEach((key, i) => {
      const v = value(row, key);
      if (Math.abs(v) < minShare * range) return;
      (v >= 0 ? up : down).push(i);
    });
    for (const side of [up, down]) {
      for (let k = 1; k < side.length; k += 1) {
        const id = `${side[k - 1]}-${side[k]}`;
        if (!pairs.has(id)) pairs.set(id, [side[k - 1], side[k], []]);
        pairs.get(id)[2].push(rowIndex);
      }
    }
  });
  return [...pairs.values()];
}

// The hex value a "var(--token)" takes in light mode, from the kit's
// tokens.css: its first plain ":root {" block and its "@theme {" block.
export function tokenHex(css, colour) {
  const name = colour.match(/^var\((--[\w-]+)\)$/)?.[1];
  if (!name) throw new Error(`${colour} is not a kit token`);
  const blocks = [...css.matchAll(/^(?::root|@theme) \{\n([\s\S]*?)^\}/gm)];
  for (const [, body] of blocks) {
    const hex = body.match(
      new RegExp(`^\\s*${name}:\\s*(#[0-9a-f]{6})\\s*;`, "im"),
    )?.[1];
    if (hex) return hex.toLowerCase();
  }
  throw new Error(`tokens.css sets no hex value for ${name}`);
}

// The distance between two colours in OKLab, times 100: the ΔE the dataviz
// palette validator reports, where 15 is the floor for neighbours.
export function colourDistance(hexA, hexB) {
  const [a, b] = [hexA, hexB].map(toOklab);
  return 100 * Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}

function toOklab(hex) {
  const [r, g, b] = [1, 3, 5].map((start) => {
    const c = parseInt(hex.slice(start, start + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}
