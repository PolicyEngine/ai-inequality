import { billions } from "./billions";

test("prints whole billions from $10 billion up and tenths below", () => {
  expect(billions(47.950231, { unit: "billion" })).toBe("$48 billion");
  expect(billions(3.522067, { unit: "billion" })).toBe("$3.5 billion");
  expect(billions(-195.188052, { unit: "billion" })).toBe("$195 billion");
  expect(billions(9.96, { unit: "billion" })).toBe("$10 billion");
  expect(billions(9.94, { unit: "billion" })).toBe("$9.9 billion");
});

test("signs amounts with a hyphen-minus before the dollar sign", () => {
  expect(billions(-172.101481, { sign: true })).toBe("-$172B");
  expect(billions(2.082155, { sign: true })).toBe("+$2.1B");
  expect(billions(-2000, { sign: true })).toBe("-$2,000B");
  expect(billions(500, { sign: true })).toBe("+$500B");
  expect(billions(-172.1, { sign: true })).not.toContain("−");
});

test("prints zero, and amounts that round to it, unsigned", () => {
  expect(billions(0, { sign: true })).toBe("$0B");
  expect(billions(-0.04, { sign: true })).toBe("$0B");
  expect(billions(0.04)).toBe("$0B");
});

test("rejects amounts that aren't finite numbers", () => {
  expect(() => billions(Number.NaN)).toThrow();
  expect(() => billions(undefined)).toThrow();
});

test("prints a fixed precision, another currency and no separator on request", () => {
  expect(billions(-172.101481, { sign: true, precision: 1 })).toBe("-$172.1B");
  expect(billions(-2011.26, { sign: true, precision: 1 })).toBe("-$2,011.3B");
  expect(
    billions(-2011.26, { sign: true, precision: 1, grouping: false }),
  ).toBe("-$2011.3B");
  expect(
    billions(2.082155, { sign: true, precision: 2, currencySymbol: "£" }),
  ).toBe("+£2.08B");
  expect(billions(9.96, { precision: 0 })).toBe("$10B");
});

test("rounds a fixed precision as toFixed does", () => {
  // 0.15 is stored just below 0.15, so toFixed(1) prints 0.1, as the sweep
  // always has; toLocaleString would print 0.2.
  expect(billions(0.15, { sign: true, precision: 1 })).toBe("+$0.1B");
  expect(
    billions(-1499.85, { sign: true, precision: 1, grouping: false }),
  ).toBe("-$1499.8B");
});

test("prints an amount that rounds to zero unsigned at any precision", () => {
  expect(billions(0, { sign: true, precision: 2 })).toBe("$0.00B");
  expect(billions(-0, { sign: true, precision: 0 })).toBe("$0B");
  expect(billions(-0.004, { sign: true, precision: 2 })).toBe("$0.00B");
  expect(billions(-0.3, { sign: true, precision: 0 })).toBe("$0B");
  expect(billions(-0.3, { sign: true, precision: 1 })).toBe("-$0.3B");
});
