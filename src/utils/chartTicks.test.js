import { niceTicks, snap125 } from "./chartTicks";

test("snap125 snaps positive values to 1/2/5 steps", () => {
  expect(snap125(0.6)).toBe(1);
  expect(snap125(1.2)).toBe(2);
  expect(snap125(2.2)).toBe(5);
  expect(snap125(18)).toBe(20);
  expect(snap125(0)).toBe(1);
});

test("niceTicks builds inclusive snapped ticks across the domain", () => {
  expect(niceTicks(0, 100, 11)).toEqual([
    0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
  ]);
  expect(niceTicks(-761, 122, 6)).toEqual([-800, -600, -400, -200, 0, 200]);
});
