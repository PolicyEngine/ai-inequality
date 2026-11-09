import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { memoMarkdown } from "./data/memoContent";
import BudgetLabMemo from "./views/BudgetLabMemo";
import Home from "./views/Home";
import IncomeShift from "./views/IncomeShift";
import PolicyAnalysis from "./views/PolicyAnalysis";
import References from "./views/References";
import ResearchPage from "./views/Research";

// Microcosm's pre-August name and the dataset it replaced as the default.
// Published ids keep the old spelling in data and code; pages never show them.
const RETIRED = /populace|enhanced[\s_-]*cps|\becps\b|policyengine-us-data/i;

const ROOT = process.cwd();

// The one module that has to recognize the frozen release-id prefix.
const RELEASE_ID_PARSER = "src/utils/modelMetadata.js";

function pathsUnder(dir) {
  return readdirSync(join(ROOT, dir), { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => join(entry.parentPath, entry.name).slice(ROOT.length + 1));
}

const read = (path) => readFileSync(join(ROOT, path), "utf8");

const siteCode = [...pathsUnder("src"), ...pathsUnder("app")].filter(
  (path) => /\.(js|jsx|css)$/.test(path) && !/\.test\.jsx?$/.test(path),
);

const PAGES = [
  ["/", Home],
  ["/?country=uk", Home],
  ["/research", ResearchPage],
  ["/research?country=uk", ResearchPage],
  ["/policy-analysis", PolicyAnalysis],
  ["/policy-analysis?country=uk", PolicyAnalysis],
  ["/income-shift", IncomeShift],
  ["/income-shift?country=uk", IncomeShift],
  ["/references", References],
  ["/budget-lab", BudgetLabMemo],
];

describe("retired dataset names", () => {
  it.each(PAGES)("%s renders none", (entry, View) => {
    const { container } = render(
      <MemoryRouter initialEntries={[entry]}>
        <View />
      </MemoryRouter>,
    );
    expect(container.textContent.length).toBeGreaterThan(200);
    expect(container.innerHTML).not.toMatch(RETIRED);
  });

  it("stays out of the generated memo", () => {
    expect(memoMarkdown.length).toBeGreaterThan(1000);
    expect(memoMarkdown).not.toMatch(RETIRED);
  });

  it("stays out of site code and copy", () => {
    const offenders = siteCode.filter(
      (path) => path !== RELEASE_ID_PARSER && RETIRED.test(read(path)),
    );
    expect(offenders).toEqual([]);
  });

  it("stays out of everything public serves", () => {
    const paths = pathsUnder("public");
    expect(paths.filter((path) => RETIRED.test(path))).toEqual([]);
    expect(
      paths.filter(
        (path) =>
          /\.(html|json|csv|txt)$/.test(path) && RETIRED.test(read(path)),
      ),
    ).toEqual([]);
  });

  // Toggled states draw their text from the same payloads, so a frozen id can
  // only reach a page through a component reading the key that holds it.
  it("stays behind the data keys that hold frozen ids", () => {
    const keys = new Set();
    const collect = (value, key) => {
      if (typeof value === "string") {
        if (RETIRED.test(value)) keys.add(key);
      } else if (Array.isArray(value)) {
        value.forEach((item) => collect(item, key));
      } else if (value && typeof value === "object") {
        Object.entries(value).forEach(([k, v]) => collect(v, k));
      }
    };
    pathsUnder("src/data")
      .filter((path) => path.endsWith(".json"))
      .forEach((path) => collect(JSON.parse(read(path))));

    const reads = siteCode
      .filter((path) => !path.startsWith("src/data/"))
      .flatMap((path) => {
        const code = read(path);
        return [...keys]
          .filter((key) => new RegExp(`\\b${key}\\b`).test(code))
          .map((key) => `${path}: ${key}`);
      });
    // AIScenarios passes this one through microcosmBuildLabel.
    expect(reads).toEqual([
      "src/components/AIScenarios.jsx: certifiedDataBuildId",
    ]);
  });
});
