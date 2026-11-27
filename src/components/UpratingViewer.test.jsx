import { readFileSync } from "node:fs";

import { fireEvent, render, screen, within } from "@testing-library/react";
import Papa from "papaparse";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import {
  POLICYENGINE_US_SNAPSHOT,
  formatReleaseMonth,
  policyengineUsSourceUrl,
} from "../utils/policyengineUsSource";
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
    vi.fn(async () => ({ text: async () => csv })),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("names the release its links open", async () => {
  render(<UpratingViewer />);
  const intro = await screen.findByText(/uprating rule we recorded/);
  const parameters = rows.filter((row) => row.type === "parameter").length;
  const variables = rows.filter((row) => row.type === "variable").length;
  expect(intro).toHaveTextContent(
    `Explore ${parameters} parameters and ${variables} variables from PolicyEngine-US ${POLICYENGINE_US_SNAPSHOT.version} (${formatReleaseMonth(POLICYENGINE_US_SNAPSHOT.date)}), each with the uprating rule we recorded for it.`,
  );
});

test("links every item it shows to its own file at the pinned commit", async () => {
  render(<UpratingViewer />);
  await screen.findByText(/uprating rule we recorded/);
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
    const card = cards()[index];
    const shown = [...card.querySelectorAll("[data-uprating-item]")];
    if (shown.length !== Math.min(SHOWN_PER_CARD, items)) {
      problems.push(`${heading}: shows ${shown.length} of ${items} items`);
    }
    // Every link in the card sits in an item's block, and each block holds
    // exactly one link, which opens that item's own file.
    const links = sourceLinks(card);
    if (links.length !== shown.length) {
      problems.push(
        `${heading}: ${links.length} links for ${shown.length} items`,
      );
    }
    for (const item of shown) {
      const path = item.dataset.upratingItem;
      const name = item.querySelector("strong")?.textContent;
      if (name !== path) problems.push(`${path}: block shows ${name}`);
      const itemLinks = sourceLinks(item);
      if (itemLinks.length !== 1) {
        problems.push(`${path}: ${itemLinks.length} links`);
        continue;
      }
      const href = itemLinks[0].getAttribute("href");
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
  await screen.findByText(/uprating rule we recorded/);

  fireEvent.change(screen.getByPlaceholderText(/search/i), {
    target: { value: "household_weight" },
  });
  fireEvent.click(document.querySelector(".grid > .card"));

  expect(sourceLinks().map((link) => link.getAttribute("href"))).toEqual([
    `${blobPrefix}policyengine_us/variables/household/demographic/weights/household_weight.py`,
  ]);
});
