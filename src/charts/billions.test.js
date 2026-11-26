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
