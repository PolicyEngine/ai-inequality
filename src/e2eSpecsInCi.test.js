import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

// CI's e2e step names each spec file it runs. Two pull requests that each add
// a spec to that line conflict there, and a resolution that keeps one side
// drops the other side's spec from CI without failing anything. So every
// spec must appear on that line, apart from these two: one only saves
// screenshots, and the other checks the 2025 homepage's copy, which the site
// no longer shows.
const NOT_IN_CI = ["homepage.spec.js", "visual-inspection.spec.js"];

const E2E_DIR = join(process.cwd(), "tests", "e2e");
const WORKFLOW = join(process.cwd(), ".github", "workflows", "deploy.yml");

test("CI's e2e step runs every e2e spec but the two it leaves out", () => {
  const step = readFileSync(WORKFLOW, "utf8")
    .split("\n")
    .find((line) => /^\s*run: bunx playwright test /.test(line));
  expect(step).toBeDefined();
  const specs = readdirSync(E2E_DIR).filter((name) =>
    name.endsWith(".spec.js"),
  );
  expect(specs.length).toBeGreaterThan(NOT_IN_CI.length);
  expect(
    specs.filter(
      (name) =>
        !NOT_IN_CI.includes(name) && !step.includes(`tests/e2e/${name}`),
    ),
  ).toEqual([]);
  for (const name of NOT_IN_CI) {
    expect(existsSync(join(E2E_DIR, name))).toBe(true);
    expect(step).not.toContain(name);
  }
});
