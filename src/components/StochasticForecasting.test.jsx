import { readFileSync } from "node:fs";

import { fireEvent, render, screen, within } from "@testing-library/react";
import Papa from "papaparse";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { OTHER_CARD, UPRATING_CARDS } from "../utils/upratingTable";
import StochasticForecasting from "./StochasticForecasting";

const csv = readFileSync("public/data/uprating_analysis.csv", "utf8");
// Parsed here with Papa directly, apart from the code under test.
const rows = Papa.parse(csv, { header: true, skipEmptyLines: true }).data;
const parameters = rows.filter((row) => row.type === "parameter").length;
const variables = rows.filter((row) => row.type === "variable").length;

const cardOf = (category) =>
  (UPRATING_CARDS.find((card) => card.includes(category)) ?? OTHER_CARD).id;

let respond;

beforeEach(() => {
  respond = async () => ({ ok: true, status: 200, text: async () => csv });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (...args) => respond(...args)),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const cards = () => [
  ...screen.getByTestId("uprating-cards").querySelectorAll("[data-card]"),
];

test("counts the parameters and variables the table lists", async () => {
  render(<StochasticForecasting />);
  const intro = await screen.findByText(/over time with economic indexes/);
  await within(intro).findByText(`${parameters} parameter files`);
  expect(intro).toHaveTextContent(
    `PolicyEngine-US grows ${parameters} parameter files and ${variables} input variables over time`,
  );
});

test("shows each card's count and share of the table", async () => {
  render(<StochasticForecasting />);
  await screen.findByText(`${parameters} parameter files`);

  const expected = new Map();
  for (const row of rows) {
    const id = cardOf(row.uprating_category);
    expected.set(id, (expected.get(id) ?? 0) + 1);
  }

  const shown = new Map();
  for (const card of cards()) {
    const heading = card.querySelector("h3").textContent;
    const [, count, percent] = heading.match(/(\d+) \((<1|\d+)%\)$/);
    shown.set(card.dataset.card, Number(count));
    const share = Number(count) / rows.length;
    expect(percent).toBe(
      Math.round(share * 100) === 0 ? "<1" : String(Math.round(share * 100)),
    );
  }
  expect(Object.fromEntries(shown)).toEqual(Object.fromEntries(expected));
  expect([...shown.values()].reduce((a, b) => a + b, 0)).toBe(rows.length);
});

test("opens a card on its parameter and variable counts and examples", async () => {
  render(<StochasticForecasting />);
  await screen.findByText(`${parameters} parameter files`);

  const byPath = new Map(rows.map((row) => [row.path, row]));
  for (const card of cards()) {
    fireEvent.click(card);
    const id = card.dataset.card;
    const inCard = rows.filter((row) => cardOf(row.uprating_category) === id);
    const cardParameters = inCard.filter((row) => row.type === "parameter");
    const plural = (count, noun) => `${count} ${noun}${count === 1 ? "" : "s"}`;
    expect(card).toHaveTextContent(
      `${plural(cardParameters.length, "parameter file")} and ${plural(inCard.length - cardParameters.length, "variable")}`,
    );
    const source = UPRATING_CARDS.find((entry) => entry.id === id);
    const items = [...card.querySelectorAll("li")].map((li) => li.textContent);
    expect(items).toEqual(source.examples.map((example) => example.label));
    for (const example of source.examples) {
      expect(cardOf(byPath.get(example.path).uprating_category)).toBe(id);
    }
  }
});

test("loads the table once, with the explorer open too", async () => {
  render(<StochasticForecasting />);
  await screen.findByText(`${parameters} parameter files`);
  fireEvent.click(screen.getByRole("button", { name: /uprating explorer/i }));
  expect(await screen.findByText(/grows over time/)).toBeTruthy();
  expect(document.querySelectorAll("#uprating-viewer")).toHaveLength(1);
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("says so when the table fails to load", async () => {
  respond = async () => ({ ok: false, status: 404, text: async () => "" });
  render(<StochasticForecasting />);
  expect(await screen.findByText(/Error loading data: HTTP 404/)).toBeTruthy();
  expect(cards()).toEqual([]);
});
