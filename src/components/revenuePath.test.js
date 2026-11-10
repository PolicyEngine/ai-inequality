import { expect, test } from "vitest";

import { revenuePath } from "./ShiftSweep";

const LABEL = "Net government revenue change";
const PREFIX = "We estimate net government revenue ";

// A seeded generator (mulberry32), so a failing case can be rerun.
function seeded(seed) {
  let state = seed;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// What a reader sees for an amount: whole billions from $10B up, tenths
// below, with the sign the words carry. Written with toFixed, apart from the
// component's rounding, so the two can disagree.
function shown(value) {
  const tenths = Number(Math.abs(value).toFixed(1));
  const size = tenths >= 10 ? Number(Math.abs(value).toFixed(0)) : tenths;
  return size === 0 ? 0 : Math.sign(value) * size;
}

function printed(value) {
  const size = Math.abs(shown(value));
  return `$${size >= 10 ? size.toLocaleString("en-US") : size.toFixed(1)}B`;
}

// "an" for a number a reader says with a vowel sound first.
function article(shift) {
  const whole = Math.floor(shift);
  return [8, 11, 18].includes(whole) || (whole >= 80 && whole <= 89)
    ? "an"
    : "a";
}

// Amounts sit 0.003 off each hundredth, so none lands on a rounding half and
// the oracle's toFixed agrees with the component wherever both are right.
function amount(rand, scale) {
  const size = Math.floor(rand() * scale * 100) / 100 + 0.003;
  return rand() < 0.5 ? -size : size;
}

function randomSweep(rand) {
  const count = 1 + Math.floor(rand() * 11);
  let shifts;
  if (rand() < 0.6) {
    shifts = Array.from({ length: count }, (_, i) => i * 10);
  } else {
    // Shifts by halves, which may skip 0%.
    const pool = new Set();
    while (pool.size < count) pool.add(Math.round(rand() * 200) / 2);
    shifts = [...pool].sort((a, b) => a - b);
  }
  const values = [];
  shifts.forEach((shift, i) => {
    const pick = rand();
    let value;
    if (i === 0 && shift === 0 && rand() < 0.8) {
      value = 0;
    } else if (pick < 0.1) {
      value = rand() < 0.5 ? 0 : -0;
    } else if (pick < 0.25 && values.length) {
      // An exact tie with an earlier amount.
      value = values[Math.floor(rand() * values.length)];
    } else if (pick < 0.45 && values.length) {
      // A near tie, which may print the same as the earlier amount.
      const base = values[Math.floor(rand() * values.length)];
      const reach = Math.abs(base) >= 10 ? 40 : 4;
      value = base + (Math.floor(rand() * (2 * reach + 1)) - reach) / 100;
    } else {
      value = amount(rand, [0.05, 1, 10, 200, 3000][Math.floor(rand() * 5)]);
    }
    values.push(value);
  });
  return shifts.map((shift, i) => ({ shift, revenue: values[i] }));
}

const AMOUNT_CLAUSE =
  /^(?:(rises|falls) )?by (\$[\d,]+(?:\.\d)?B) at (an?) ([\d.]+)% shift$/;
const BASELINE_CLAUSE =
  /^(?:(stays at|returns to) its baseline )?at (an?) ([\d.]+)% shift$/;

// Checks each clause of a changes list against the rows it names, and
// returns the rows in order.
function checkClauses(list, rowAt) {
  const named = [];
  let verb = null;
  let changed = false;
  for (const clause of list.split(" and ")) {
    const byAmount = clause.match(AMOUNT_CLAUSE);
    const byBaseline = clause.match(BASELINE_CLAUSE);
    expect(byAmount || byBaseline, clause).toBeTruthy();
    if (byAmount) {
      const [, ownVerb, text, art, shiftText] = byAmount;
      const row = rowAt(Number(shiftText));
      verb = ownVerb ?? verb;
      expect(verb, clause).not.toBeNull();
      expect(art).toBe(article(row.shift));
      expect(text).toBe(printed(row.revenue));
      expect(Math.sign(shown(row.revenue))).toBe(verb === "rises" ? 1 : -1);
      changed = true;
      named.push(row);
    } else {
      const [, phrase, art, shiftText] = byBaseline;
      const row = rowAt(Number(shiftText));
      expect(art).toBe(article(row.shift));
      expect(shown(row.revenue)).toBe(0);
      if (phrase) expect(phrase).toBe(changed ? "returns to" : "stays at");
      else expect(verb).toBe("baseline");
      verb = "baseline";
      named.push(row);
    }
  }
  return named;
}

function checkPath(rows) {
  const text = revenuePath(rows, LABEL);
  const context = JSON.stringify(rows);
  expect(text, context).not.toMatch(/NaN|undefined|Infinity|\$-|-\$|\+/);
  expect(text.startsWith(PREFIX), context).toBe(true);
  const body = text.slice(PREFIX.length);
  const values = rows.map((row) => shown(row.revenue));
  const low = Math.min(...values);
  const end = rows[rows.length - 1];
  const endShown = shown(end.revenue);
  const rowAt = (shift) => {
    const row = rows.find((candidate) => candidate.shift === shift);
    expect(row, `${shift}% in ${context}`).toBeTruthy();
    return row;
  };
  // The last row at the lowest printed amount.
  const lowRow = rows[values.lastIndexOf(low)];
  const midway = rows.find((row) => row.shift === 50 && row !== end);

  let match;
  if (
    (match = body.match(
      /^stays at its baseline through (an?) ([\d.]+)% shift\.$/,
    ))
  ) {
    expect(
      values.every((value) => value === 0),
      context,
    ).toBe(true);
    expect(match[1]).toBe(article(end.shift));
    expect(Number(match[2])).toBe(end.shift);
  } else if (
    (match = body.match(/^never falls below its baseline and (.*)\.$/))
  ) {
    expect(low, context).toBeGreaterThanOrEqual(0);
    expect(
      values.some((value) => value > 0),
      context,
    ).toBe(true);
    const back = match[1].match(/^returns to it at (an?) ([\d.]+)% shift$/);
    if (back) {
      expect(endShown, context).toBe(0);
      expect(back[1]).toBe(article(end.shift));
      expect(Number(back[2])).toBe(end.shift);
    } else {
      expect(checkClauses(match[1], rowAt)).toEqual([end]);
      expect(endShown, context).toBeGreaterThan(0);
    }
  } else if (
    (match = body.match(
      /^(.*), its low point\. At (an?) ([\d.]+)% shift, (?:the fall narrows to (\$[\d,.]+B)|it (returns to its baseline)|it exceeds its baseline by (\$[\d,.]+B))\.$/,
    ))
  ) {
    const [, list, art, shiftText, narrowed, returned, exceeded] = match;
    expect(low, context).toBeLessThan(0);
    const expected = lowRow.shift > 50 && midway ? [midway, lowRow] : [lowRow];
    expect(checkClauses(list, rowAt), context).toEqual(expected);
    expect(lowRow, context).not.toBe(end);
    expect(endShown, context).toBeGreaterThan(low);
    expect(art).toBe(article(end.shift));
    expect(Number(shiftText)).toBe(end.shift);
    if (narrowed) {
      expect(endShown, context).toBeLessThan(0);
      expect(narrowed).toBe(printed(end.revenue));
    } else if (returned) {
      expect(endShown, context).toBe(0);
    } else {
      expect(endShown, context).toBeGreaterThan(0);
      expect(exceeded).toBe(printed(end.revenue));
    }
  } else {
    // The low point is the last row.
    match = body.match(/^(.*)\.$/);
    expect(match, context).toBeTruthy();
    expect(low, context).toBeLessThan(0);
    expect(endShown, context).toBe(low);
    expect(checkClauses(match[1], rowAt), context).toEqual(
      midway ? [midway, end] : [end],
    );
  }
  return text;
}

test("every revenue path states only what its printed amounts show", () => {
  const rand = seeded(20261110);
  const forms = new Set();
  for (let i = 0; i < 20000; i += 1) {
    const text = checkPath(randomSweep(rand));
    forms.add(
      text.includes("its low point")
        ? "low point"
        : text.includes("never falls")
          ? "never falls"
          : text.includes("through")
            ? "flat"
            : "falls to the end",
    );
  }
  // The generator reaches every form.
  expect([...forms].sort()).toEqual([
    "falls to the end",
    "flat",
    "low point",
    "never falls",
  ]);
});

test("the revenue path words the edge cases from what it prints", () => {
  const cases = [
    // Every amount prints as zero.
    [
      [
        { shift: 0, revenue: 0 },
        { shift: 10, revenue: 0.02 },
        { shift: 20, revenue: -0 },
      ],
      "We estimate net government revenue stays at its baseline through a 20% shift.",
    ],
    // A rise that comes back to the baseline.
    [
      [
        { shift: 0, revenue: 0 },
        { shift: 50, revenue: 5 },
        { shift: 100, revenue: 0.01 },
      ],
      "We estimate net government revenue never falls below its baseline and returns to it at a 100% shift.",
    ],
    // A flat bottom: the end prints the same as the 50% point.
    [
      [
        { shift: 0, revenue: 0 },
        { shift: 50, revenue: -5.04 },
        { shift: 100, revenue: -5.01 },
      ],
      "We estimate net government revenue falls by $5.0B at a 50% shift and by $5.0B at a 100% shift.",
    ],
    // A flat bottom past $10B, where whole billions tie.
    [
      [
        { shift: 0, revenue: 0 },
        { shift: 70, revenue: -130.4 },
        { shift: 100, revenue: -130.2 },
      ],
      "We estimate net government revenue falls by $130B at a 100% shift.",
    ],
    // A low point, then back to the baseline.
    [
      [
        { shift: 0, revenue: 0 },
        { shift: 30, revenue: -3 },
        { shift: 100, revenue: -0 },
      ],
      "We estimate net government revenue falls by $3.0B at a 30% shift, its low point. At a 100% shift, it returns to its baseline.",
    ],
    // $9.96B rounds to $10B.
    [
      [
        { shift: 0, revenue: 0 },
        { shift: 100, revenue: 9.96 },
      ],
      "We estimate net government revenue never falls below its baseline and rises by $10B at a 100% shift.",
    ],
    // A shift with decimals takes its article from the whole number.
    [
      [
        { shift: 0, revenue: 0 },
        { shift: 8.5, revenue: -2 },
      ],
      "We estimate net government revenue falls by $2.0B at an 8.5% shift.",
    ],
    // A sweep that starts past 0% and falls at its first row.
    [
      [
        { shift: 10, revenue: -3 },
        { shift: 20, revenue: -1 },
      ],
      "We estimate net government revenue falls by $3.0B at a 10% shift, its low point. At a 20% shift, the fall narrows to $1.0B.",
    ],
    // A 50% amount that prints as zero.
    [
      [
        { shift: 0, revenue: 0 },
        { shift: 50, revenue: 0.04 },
        { shift: 100, revenue: -7 },
      ],
      "We estimate net government revenue stays at its baseline at a 50% shift and falls by $7.0B at a 100% shift.",
    ],
  ];
  for (const [rows, sentence] of cases) {
    expect(checkPath(rows)).toBe(sentence);
  }
});
