import { readFileSync } from "node:fs";

import { fireEvent, render, screen, within } from "@testing-library/react";
import Papa from "papaparse";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import {
  POLICYENGINE_US_SNAPSHOT,
  formatReleaseMonth,
  policyengineUsSourceUrl,
} from "../utils/policyengineUsSource";
import { FORMULA_MODULE, formulaSteps } from "../utils/upratingTable";
import UpratingViewer from "./UpratingViewer";

const csv = readFileSync("public/data/uprating_analysis.csv", "utf8");
const rows = Papa.parse(csv, { header: true, skipEmptyLines: true }).data;
const urlByPath = new Map(
  rows.map((row) => [row.path, policyengineUsSourceUrl(row)]),
);
const listedFiles = new Set(
  readFileSync("tests/fixtures/policyengine-us-files.txt", "utf8")
    .split("\n")
    .filter((line) => line && !line.startsWith("#")),
);
const blobPrefix = `https://github.com/PolicyEngine/policyengine-us/blob/${POLICYENGINE_US_SNAPSHOT.commit}/`;
// An open card lists this many of its items; search reaches the rest.
const SHOWN_PER_CARD = 50;

const sourceLinks = (container = document.body) =>
  within(container).queryAllByRole("link", { name: /view source/i });

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, status: 200, text: async () => csv })),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("names the release its links open", async () => {
  render(<UpratingViewer />);
  const intro = await screen.findByText(/grows over time/);
  const parameters = rows.filter((row) => row.type === "parameter").length;
  const variables = rows.filter((row) => row.type === "variable").length;
  expect(intro).toHaveTextContent(
    `Explore the ${parameters} parameters and ${variables} input variables that PolicyEngine-US ${POLICYENGINE_US_SNAPSHOT.version} (${formatReleaseMonth(POLICYENGINE_US_SNAPSHOT.date)}) grows over time`,
  );
});

test("counts what a search finds, in the singular for one", async () => {
  render(<UpratingViewer />);
  await screen.findByText(/grows over time/);
  const parameters = rows.filter((row) => row.type === "parameter").length;
  const variables = rows.filter((row) => row.type === "variable").length;
  expect(screen.getByText(/^Showing/)).toHaveTextContent(
    `Showing ${rows.length} items (${parameters} parameters, ${variables} variables)`,
  );

  const path = "gov.irs.payroll.social_security.cap";
  expect(rows.filter((row) => row.path === path)).toHaveLength(1);
  fireEvent.change(screen.getByPlaceholderText(/search/i), {
    target: { value: path },
  });
  expect(screen.getByText(/^Showing/)).toHaveTextContent(
    `Showing 1 item (1 parameter, 0 variables) matching "${path}"`,
  );
});

test("links every item it shows to its own file at the pinned commit", async () => {
  render(<UpratingViewer />);
  await screen.findByText(/grows over time/);
  expect(urlByPath.size).toBe(rows.length);

  const cards = () => document.querySelectorAll(".grid > .card");
  expect(cards().length).toBeGreaterThan(1);

  const problems = [];
  const seen = [];
  let itemsInCards = 0;
  for (let index = 0; index < cards().length; index += 1) {
    // A card's header counts its parameters and variables, as in "214p 0v".
    const heading = cards()[index].querySelector("h3").textContent;
    const [, parameters, variables] = heading.match(/(\d+)p (\d+)v/);
    const items = Number(parameters) + Number(variables);
    itemsInCards += items;

    fireEvent.click(cards()[index]);
    const links = sourceLinks(cards()[index]);
    if (links.length !== Math.min(SHOWN_PER_CARD, items)) {
      problems.push(`${heading}: ${links.length} links for ${items} items`);
    }
    for (const link of links) {
      // Each link sits in its item's block, beside the item's name.
      const path = link.parentElement.querySelector("strong").textContent;
      const href = link.getAttribute("href");
      if (href !== urlByPath.get(path)) problems.push(`${path}: ${href}`);
      seen.push(href);
    }
  }

  expect(problems).toEqual([]);
  expect(itemsInCards).toBe(rows.length);
  const outside = seen.filter(
    (href) =>
      !href.startsWith(blobPrefix) ||
      !listedFiles.has(href.slice(blobPrefix.length)),
  );
  expect(outside).toEqual([]);
});

test("links a variable to its Python file, not the parameters folder", async () => {
  render(<UpratingViewer />);
  await screen.findByText(/grows over time/);

  fireEvent.change(screen.getByPlaceholderText(/search/i), {
    target: { value: "household_weight" },
  });
  fireEvent.click(document.querySelector(".grid > .card"));

  expect(sourceLinks().map((link) => link.getAttribute("href"))).toEqual([
    `${blobPrefix}policyengine_us/variables/household/demographic/weights/household_weight.py`,
  ]);
});

test("links each formula-grown parameter to its formula too", async () => {
  const formulaRows = rows.filter((row) => formulaSteps(row).length);
  expect(formulaRows.length).toBeGreaterThan(0);

  render(<UpratingViewer />);
  await screen.findByText(/grows over time/);
  const [row] = formulaRows;
  fireEvent.change(screen.getByPlaceholderText(/search/i), {
    target: { value: row.path },
  });
  fireEvent.click(document.querySelector(".grid > .card"));

  const formulaLinks = screen.getAllByRole("link", { name: /view formula/i });
  expect(formulaLinks.length).toBeGreaterThan(0);
  for (const link of formulaLinks) {
    expect(link.getAttribute("href")).toBe(`${blobPrefix}${FORMULA_MODULE}`);
  }
  expect(listedFiles.has(FORMULA_MODULE)).toBe(true);
});
