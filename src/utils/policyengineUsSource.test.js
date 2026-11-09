import { readFileSync } from "node:fs";

import Papa from "papaparse";
import { describe, expect, it } from "vitest";

import {
  POLICYENGINE_US_SNAPSHOT,
  formatReleaseMonth,
  policyengineUsSourcePath,
  policyengineUsSourceUrl,
} from "./policyengineUsSource";

const TABLE = "public/data/uprating_analysis.csv";
// Written by scripts/snapshot-policyengine-us-files.mjs from GitHub's tree API.
const FILE_LIST = "tests/fixtures/policyengine-us-files.txt";

const parsed = Papa.parse(readFileSync(TABLE, "utf8"), {
  header: true,
  skipEmptyLines: true,
});
const rows = parsed.data;

const listing = readFileSync(FILE_LIST, "utf8").split("\n");
// The header records the commit, its release and its date as "# name value".
const listed = (name) =>
  listing
    .find((line) => line.startsWith(`# ${name} `))
    ?.slice(`# ${name} `.length);
const files = new Set(listing.filter((line) => line && !line.startsWith("#")));

const describeRow = (row) => `${row.type} ${row.path} (${row.file_path})`;

describe("PolicyEngine-US source links in the uprating viewer", () => {
  it("read the whole table", () => {
    expect(parsed.errors).toEqual([]);
    expect(rows.length).toBeGreaterThan(0);
  });

  it("pin the commit the file list records", () => {
    expect(POLICYENGINE_US_SNAPSHOT.commit).toMatch(/^[0-9a-f]{40}$/);
    expect(listed("commit")).toBe(POLICYENGINE_US_SNAPSHOT.commit);
    expect(files.size).toBeGreaterThan(1000);
  });

  it("name the release and date the file list records for that commit", () => {
    expect(listed("version")).toBe(POLICYENGINE_US_SNAPSHOT.version);
    expect(listed("date")).toBe(POLICYENGINE_US_SNAPSHOT.date);
  });

  it("open a file that exists at that commit, for every row", () => {
    const missing = rows
      .filter((row) => !files.has(policyengineUsSourcePath(row)))
      .map(describeRow);
    expect(missing).toEqual([]);
  });

  it("send parameters to YAML files and variables to Python files", () => {
    const misplaced = rows
      .filter((row) => {
        const path = policyengineUsSourcePath(row) ?? "";
        return row.type === "parameter"
          ? !/^policyengine_us\/parameters\/.+\.yaml$/.test(path)
          : !/^policyengine_us\/variables\/.+\.py$/.test(path);
      })
      .map(describeRow);
    expect(misplaced).toEqual([]);
  });

  it("build GitHub file URLs at the pinned commit", () => {
    const prefix = `https://github.com/PolicyEngine/policyengine-us/blob/${POLICYENGINE_US_SNAPSHOT.commit}/`;
    const wrong = rows
      .filter(
        (row) =>
          policyengineUsSourceUrl(row) !==
          prefix + policyengineUsSourcePath(row),
      )
      .map(describeRow);
    expect(wrong).toEqual([]);
  });

  it("give no link to a row with no file or an unknown type", () => {
    expect(
      policyengineUsSourceUrl({ type: "parameter", file_path: "" }),
    ).toBeNull();
    expect(
      policyengineUsSourceUrl({ type: "reform", file_path: "gov/irs.yaml" }),
    ).toBeNull();
    expect(policyengineUsSourceUrl(undefined)).toBeNull();
  });

  it("name the release month by its UTC date", () => {
    expect(POLICYENGINE_US_SNAPSHOT.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(formatReleaseMonth("2025-10-09")).toBe("October 2025");
    // vitest.config.mjs runs the suite west of UTC, where UTC midnight on the
    // 1st falls on the last day of the prior month.
    expect(new Date("2025-11-01T00:00:00Z").getDate()).toBe(31);
    expect(formatReleaseMonth("2025-11-01")).toBe("November 2025");
  });
});
