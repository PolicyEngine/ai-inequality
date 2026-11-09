import { readFileSync } from "node:fs";

import { fireEvent, render, screen } from "@testing-library/react";
import Papa from "papaparse";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import {
  POLICYENGINE_US_SNAPSHOT,
  policyengineUsSourceUrl,
} from "../utils/policyengineUsSource";
import UpratingViewer from "./UpratingViewer";

const csv = readFileSync("public/data/uprating_analysis.csv", "utf8");
const rows = Papa.parse(csv, { header: true, skipEmptyLines: true }).data;
const listedFiles = new Set(
  readFileSync("tests/fixtures/policyengine-us-files.txt", "utf8")
    .split("\n")
    .filter((line) => line && !line.startsWith("#")),
);
const blobPrefix = `https://github.com/PolicyEngine/policyengine-us/blob/${POLICYENGINE_US_SNAPSHOT.commit}/`;

const sourceLinks = () =>
  screen
    .queryAllByRole("link", { name: /view source/i })
    .map((link) => link.getAttribute("href"));

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ text: async () => csv })),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("names the release its links open", async () => {
  render(<UpratingViewer />);
  const intro = await screen.findByText(/that grow over time/);
  const parameters = rows.filter((row) => row.type === "parameter").length;
  const variables = rows.filter((row) => row.type === "variable").length;
  expect(intro).toHaveTextContent(
    `Explore the ${parameters} parameters and ${variables} variables in PolicyEngine-US ${POLICYENGINE_US_SNAPSHOT.version} (October 2025)`,
  );
});

test("links every item it shows to a file listed at the pinned commit", async () => {
  render(<UpratingViewer />);
  await screen.findByText(/that grow over time/);

  const expected = new Set(rows.map(policyengineUsSourceUrl));
  const cardCount = document.querySelectorAll(".grid > .card").length;
  expect(cardCount).toBeGreaterThan(1);

  const seen = [];
  for (let index = 0; index < cardCount; index += 1) {
    fireEvent.click(document.querySelectorAll(".grid > .card")[index]);
    const links = sourceLinks();
    expect(links.length).toBeGreaterThan(0);
    seen.push(...links);
  }

  const outside = seen.filter(
    (href) =>
      !expected.has(href) ||
      !href.startsWith(blobPrefix) ||
      !listedFiles.has(href.slice(blobPrefix.length)),
  );
  expect(outside).toEqual([]);
});

test("links a variable to its Python file, not the parameters folder", async () => {
  render(<UpratingViewer />);
  await screen.findByText(/that grow over time/);

  fireEvent.change(screen.getByPlaceholderText(/search/i), {
    target: { value: "household_weight" },
  });
  fireEvent.click(document.querySelector(".grid > .card"));

  expect(sourceLinks()).toEqual([
    `${blobPrefix}policyengine_us/variables/household/demographic/weights/household_weight.py`,
  ]);
});
